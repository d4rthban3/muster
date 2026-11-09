//! Shared helpers: the hook's input, the profile, regex shortcuts, transcript readers, and the exact output shape Muster's
//! Python checks printed (so every existing test reads the Rust copies the same way).
use fancy_regex::Regex;
use serde_json::Value;
use std::collections::HashSet;
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

pub fn re(p: &str) -> Regex { Regex::new(p).unwrap_or_else(|e| panic!("bad pattern {p}: {e}")) }
pub fn rei(p: &str) -> Regex { re(&format!("(?i){p}")) }
pub fn is(r: &Regex, s: &str) -> bool { r.is_match(s).unwrap_or(false) }
pub fn find<'a>(r: &Regex, s: &'a str) -> Option<fancy_regex::Match<'a>> { r.find(s).ok().flatten() }
pub fn caps<'a>(r: &Regex, s: &'a str) -> Option<fancy_regex::Captures<'a>> { r.captures(s).ok().flatten() }
pub fn sub(r: &Regex, s: &str, with: &str) -> String { r.replace_all(s, with).to_string() }

pub fn read_stdin() -> Option<Value> {
    let mut buf = Vec::new();
    std::io::stdin().read_to_end(&mut buf).ok()?;
    serde_json::from_str(&String::from_utf8_lossy(&buf)).ok()
}

pub fn s<'a>(v: &'a Value, k: &str) -> &'a str { v.get(k).and_then(Value::as_str).unwrap_or("") }

/// Python's json.dumps for a flat object of strings: `{"a": "b", "c": "d"}` with non-ASCII escaped.
pub fn py_obj(pairs: &[(&str, String)]) -> String {
    let body: Vec<String> = pairs.iter().map(|(k, v)| format!("{}: {}", py_str(k), py_str(v))).collect();
    format!("{{{}}}", body.join(", "))
}
pub fn py_str(t: &str) -> String {
    let mut o = String::from("\"");
    for c in t.chars() {
        match c {
            '"' => o.push_str("\\\""), '\\' => o.push_str("\\\\"), '\n' => o.push_str("\\n"), '\r' => o.push_str("\\r"), '\t' => o.push_str("\\t"),
            c if (c as u32) < 0x20 => o.push_str(&format!("\\u{:04x}", c as u32)),
            c if (c as u32) < 0x7f => o.push(c),
            c => { let mut b = [0u16; 2]; for u in c.encode_utf16(&mut b) { o.push_str(&format!("\\u{:04x}", u)); } }
        }
    }
    o.push('"');
    o
}
pub fn say(line: &str) { let _ = writeln!(std::io::stdout(), "{line}"); }
pub fn block(reason: &str) { say(&py_obj(&[("decision", "block".into()), ("reason", format!("Muster rule: {reason}"))])); }
pub fn deny(reason: &str) {
    say(&format!("{{\"hookSpecificOutput\": {{\"hookEventName\": \"PreToolUse\", \"permissionDecision\": \"deny\", \"permissionDecisionReason\": {}}}}}", py_str(&format!("Muster rule: {reason}"))));
}

pub fn exe_dir() -> PathBuf { std::env::current_exe().ok().and_then(|p| p.parent().map(Path::to_path_buf)).unwrap_or_default() }

pub fn load_profile() -> Value {
    let mut cands: Vec<PathBuf> = vec![];
    if let Ok(p) = std::env::var("MUSTER_PROFILE") { if !p.is_empty() { cands.push(p.into()); } }
    cands.push(exe_dir().join("profile.json"));
    for c in cands {
        if c.is_file() {
            return fs::read_to_string(&c).ok().and_then(|t| serde_json::from_str::<Value>(&t).ok()).filter(Value::is_object).unwrap_or(Value::Object(Default::default()));
        }
    }
    Value::Object(Default::default())
}
pub fn pstrings(p: &Value, k: &str) -> Vec<String> {
    p.get(k).and_then(Value::as_array).map(|a| a.iter().filter_map(|x| x.as_str().map(String::from)).collect()).unwrap_or_default()
}

/// The plugin's copy stands down where the project has its own installed copy (.muster-checks/), so a check never runs twice.
pub fn stood_down(data: &Value, py_name: &str) -> bool {
    let dir = exe_dir();
    if dir.file_name().map(|n| n == ".muster-checks").unwrap_or(false) { return false; }
    let start = std::env::var("CLAUDE_PROJECT_DIR").ok().filter(|x| !x.is_empty()).unwrap_or_else(|| {
        let c = s(data, "cwd"); if c.is_empty() { std::env::current_dir().map(|p| p.to_string_lossy().to_string()).unwrap_or_default() } else { c.to_string() }
    });
    let mut d = PathBuf::from(start);
    loop {
        let mc = d.join(".muster-checks");
        if mc.join(py_name).is_file() || mc.join("muster-checks").is_file() || mc.join("muster-checks.exe").is_file() { return true; }
        match d.parent() { Some(p) if p != d => d = p.to_path_buf(), _ => return false }
    }
}

fn content_text(c: &Value) -> String {
    match c {
        Value::String(t) => t.clone(),
        Value::Array(a) => a.iter().filter_map(|b| b.as_object().map(|o| o.get("text").and_then(Value::as_str).unwrap_or("").to_string())).collect::<Vec<_>>().join(" "),
        Value::Null => String::new(),
        o => o.to_string(),
    }
}
pub fn lines_of(path: &str) -> Vec<Value> {
    fs::read_to_string(path).map(|t| t.lines().filter_map(|l| serde_json::from_str::<Value>(l).ok()).collect()).unwrap_or_default()
}
fn msg_content(d: &Value) -> Value { d.get("message").and_then(|m| m.get("content")).cloned().unwrap_or(Value::String(String::new())) }

pub fn first_message(path: &str) -> String {
    for d in lines_of(path) {
        if s(&d, "type") != "user" { continue; }
        let t = content_text(&msg_content(&d));
        return t.chars().take(6000).collect();
    }
    String::new()
}

/// tool_use blocks of the current turn: everything after the last user message that holds text.
pub fn turn_blocks(path: &str) -> Vec<Value> {
    let mut uses: Vec<Value> = vec![];
    for d in lines_of(path) {
        let c = msg_content(&d);
        match s(&d, "type") {
            "user" => {
                let texty = match &c { Value::String(_) => true, Value::Array(a) => a.iter().any(|b| s(b, "type") == "text"), _ => false };
                if texty { uses.clear(); }
            }
            "assistant" => if let Value::Array(a) = &c { for b in a { if s(b, "type") == "tool_use" { uses.push(b.clone()); } } },
            _ => {}
        }
    }
    uses
}

/// Messages really sent: a SendMessage whose result came back without an error.
pub fn all_sent_text(path: &str) -> Vec<String> {
    let mut calls: Vec<(String, String)> = vec![];
    let (mut done, mut failed): (HashSet<String>, HashSet<String>) = (HashSet::new(), HashSet::new());
    for d in lines_of(path) {
        if let Value::Array(a) = msg_content(&d) {
            for b in &a {
                if !b.is_object() { continue; }
                if s(&d, "type") == "assistant" && s(b, "type") == "tool_use" && s(b, "name") == "SendMessage" {
                    calls.push((s(b, "id").to_string(), b.get("input").map(|i| s(i, "message").to_string()).unwrap_or_default()));
                } else if s(&d, "type") == "user" && s(b, "type") == "tool_result" {
                    let id = s(b, "tool_use_id").to_string();
                    done.insert(id.clone());
                    let rc = content_text(b.get("content").unwrap_or(&Value::Null));
                    let head: String = rc.chars().take(200).collect();
                    if b.get("is_error").and_then(Value::as_bool).unwrap_or(false) || rc.trim_start().starts_with("Muster rule:") || head.contains("Muster rule:") { failed.insert(id); }
                }
            }
        }
    }
    calls.into_iter().filter(|(i, _)| done.contains(i) && !failed.contains(i)).map(|(_, t)| t).collect()
}

/// True if this turn was started by the owner's typed message and it holds a question mark.
pub fn owner_asked(path: &str) -> bool {
    let ends = rei(r"<cross-session-message|<task-notification|<side-sessions-event|<ci-monitor-event|\[SYSTEM NOTIFICATION");
    let neutral = rei(r"^\s*(<system-reminder|Stop hook feedback)");
    let mut last = String::new();
    for d in lines_of(path) {
        if s(&d, "type") != "user" { continue; }
        let c = msg_content(&d);
        if let Value::Array(a) = &c { if a.iter().any(|b| s(b, "type") == "tool_result") { continue; } }
        let t = content_text(&c);
        if t.trim().is_empty() { continue; }
        if is(&ends, &t) { last.clear(); } else if !is(&neutral, &t) { last = t; }
    }
    last.contains('?')
}

pub fn exists(p: &Path) -> bool { p.exists() }
pub fn read_all<R: Read>(mut r: R) -> String { let mut t = String::new(); let _ = r.read_to_string(&mut t); t }
