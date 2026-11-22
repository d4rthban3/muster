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
pub static SAID: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
pub fn say(line: &str) { SAID.store(true, std::sync::atomic::Ordering::SeqCst); let _ = writeln!(std::io::stdout(), "{line}"); }

/// A note is not a refusal: it is kept beside the transcript (`<transcript>.muster-notes`) and told to the chat once, at its next prompt or tool call.
pub fn note_add(path: &str, rid: &str, text: &str) {
    if path.is_empty() || !rule_on(rid) { return; }
    let side = format!("{path}.muster-notes");
    let old = fs::read_to_string(&side).unwrap_or_default();
    if old.split('\n').any(|l| l == text) { return; }
    if let Ok(mut f) = fs::OpenOptions::new().create(true).append(true).open(&side) { let _ = writeln!(f, "{text}"); }
}
pub fn note_take(path: &str) -> Vec<String> {
    if path.is_empty() { return vec![]; }
    let side = format!("{path}.muster-notes");
    let Ok(t) = fs::read_to_string(&side) else { return vec![] };
    let _ = fs::remove_file(&side);
    t.split('\n').filter(|l| !l.trim().is_empty()).map(|l| l.to_string()).collect()
}
/// Tell the chat its pending notes (once) as added context; prints nothing when there are none.
pub fn notes_out(path: &str, event: &str) {
    let notes = note_take(path);
    if notes.is_empty() { return; }
    say(&format!("{{\"hookSpecificOutput\": {{\"hookEventName\": {}, \"additionalContext\": {}}}}}", py_str(event), py_str(&format!("Muster note (your reply was let through, nothing was refused; do it this way next time): {}", notes.join(" ")))));
}
pub const NOREPEAT: &str = " Your reply already reached the owner: do not write it again. Do what this asks, then end with at most one new line, or nothing.";
/// Two groups (docs/checks.md lists every check). A SAFETY STOP is on for every project, with no switch. A HOUSE RULE (everything about how a
/// chat talks, asks, reports and orders) has its own switch per project, "house_rules": {"<name>": false} in the project's profile; a house
/// rule switched off never reaches that project. A house rule made after the list starts off for every project but Muster (NEW_HOUSE).
pub const SAFETY: [&str; 5] = ["guard", "helper-ships", "note-secret", "usage-limit", "muster-not-saved"];
pub const NEW_HOUSE: [&str; 2] = ["ready-to-inspector", "verdict-from-inspector"];
pub fn rule_on(rid: &str) -> bool {
    if SAFETY.contains(&rid) { return true; }
    let p = load_profile();
    if let Some(v) = p.get("house_rules").and_then(Value::as_object).and_then(|m| m.get(rid)) { return truthy(Some(v)); }
    if NEW_HOUSE.contains(&rid) { return p.get("name").and_then(Value::as_str).filter(|n| !n.is_empty()).unwrap_or("Muster") == "Muster"; }
    true
}
/// Every refusal names its group and the project whose rule it is, so a meshing of two projects' rules is seen at once.
pub fn group_label(rid: &str) -> String {
    if SAFETY.contains(&rid) { format!(" [safety stop \"{rid}\": on for every project, no switch]") }
    else { format!(" [house rule \"{rid}\" of Muster; a project's profile can switch it off]") }
}
/// Refuse an end of turn; false (and nothing said) when the rule is a house rule this project has switched off.
pub fn block(rid: &str, reason: &str) -> bool {
    if !rule_on(rid) { return false; }
    say(&py_obj(&[("decision", "block".into()), ("reason", format!("Muster rule: {reason}{}{NOREPEAT}", group_label(rid)))]));
    true
}
/// Refuse a tool call; false (and nothing said) when the rule is a house rule this project has switched off.
pub fn deny(rid: &str, reason: &str) -> bool {
    if !rule_on(rid) { return false; }
    say(&format!("{{\"hookSpecificOutput\": {{\"hookEventName\": \"PreToolUse\", \"permissionDecision\": \"deny\", \"permissionDecisionReason\": {}}}}}", py_str(&format!("Muster rule: {reason}{}", group_label(rid)))));
    true
}
/// A house rule's refusal in the other checks (the reason may already end with NOREPEAT): the label goes before it.
pub fn say_block(rid: &str, reason: &str) {
    if !rule_on(rid) { return; }
    let r = match reason.strip_suffix(NOREPEAT) { Some(head) => format!("{head}{}{NOREPEAT}", group_label(rid)), None => format!("{reason}{}", group_label(rid)) };
    say(&py_obj(&[("decision", "block".into()), ("reason", r)]));
}

/// Python's idea of true for a JSON value (None, False, 0, "", [] and {} are false): a hook field the Python copies test with `if x`.
pub fn truthy(v: Option<&Value>) -> bool {
    match v {
        None | Some(Value::Null) => false,
        Some(Value::Bool(b)) => *b,
        Some(Value::Number(n)) => n.as_f64().map(|f| f != 0.0).unwrap_or(true),
        Some(Value::String(t)) => !t.is_empty(),
        Some(Value::Array(a)) => !a.is_empty(),
        Some(Value::Object(o)) => !o.is_empty(),
    }
}
/// The folders a plugin's own scripts may sit in, relative to the program: bin/<platform>/ (the plugin's copy) puts them two levels up,
/// a project's .muster-checks/ one level up; the Python copies find them from hooks/.. the same way.
pub fn script_roots() -> Vec<PathBuf> { vec![exe_dir().join("..").join(".."), exe_dir().join("..")] }
/// The folder a check counts as sitting in. A project's live stand-in (.muster-checks/<name>.sh) names the project it runs for in MUSTER_PROJECT, and the
/// program then acts exactly as the installed Python copy does there (here = <project>/.muster-checks); anywhere else it is the program's own folder.
pub fn here_dir() -> PathBuf {
    match std::env::var("MUSTER_PROJECT") { Ok(p) if !p.is_empty() => PathBuf::from(p).join(".muster-checks"), _ => exe_dir() }
}
/// True when the check runs as a project's installed copy: from a folder named .muster-checks, or for a project a stand-in named.
pub fn installed() -> bool { here_dir().file_name().map(|n| n == ".muster-checks").unwrap_or(false) }
pub fn exe_dir() -> PathBuf { std::env::current_exe().ok().and_then(|p| p.parent().map(Path::to_path_buf)).unwrap_or_default() }

pub fn load_profile() -> Value {
    let mut cands: Vec<PathBuf> = vec![];
    if let Ok(p) = std::env::var("MUSTER_PROFILE") { if !p.is_empty() { cands.push(p.into()); } }
    cands.push(here_dir().join("profile.json"));
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
    if installed() { return false; }
    let start = std::env::var("CLAUDE_PROJECT_DIR").ok().filter(|x| !x.is_empty()).unwrap_or_else(|| {
        let c = s(data, "cwd"); if c.is_empty() { std::env::current_dir().map(|p| p.to_string_lossy().to_string()).unwrap_or_default() } else { c.to_string() }
    });
    let mut d = PathBuf::from(start);
    loop {
        let mc = d.join(".muster-checks");
        if mc.join(py_name).is_file() || mc.join("muster-checks").is_file() || mc.join("muster-checks.exe").is_file() { return true; }
        if d.join(".git").is_file() { return false; } // a linked worktree's root: the installed copy of the main folder above is not this chat's
        match d.parent() { Some(p) if p != d => d = p.to_path_buf(), _ => return false }
    }
}

pub fn content_text(c: &Value) -> String {
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
pub fn msg_content(d: &Value) -> Value { d.get("message").and_then(|m| m.get("content")).cloned().unwrap_or(Value::String(String::new())) }

/// A crew chat's own first message is kept beside its transcript, so it still knows who it is after a compaction (D-039).
pub fn remember_first(path: &str, first: &str) {
    let side = format!("{path}.muster-first");
    if !path.is_empty() && !std::path::Path::new(&side).exists() { let _ = fs::write(&side, first.chars().take(6000).collect::<String>()); }
}

pub fn first_message(path: &str) -> String {
    if let Ok(kept) = fs::read_to_string(format!("{path}.muster-first")) { if !kept.trim().is_empty() { return kept.chars().take(6000).collect(); } }
    for d in lines_of(path) {
        if s(&d, "type") != "user" || d.get("isCompactSummary").and_then(Value::as_bool) == Some(true) { continue; }
        let t = content_text(&msg_content(&d));
        if t.trim().is_empty() { continue; } // a line holding only tool results is not the chat's first message
        return t.chars().take(6000).collect();
    }
    String::new()
}

/// The chat's own title: the last custom-title record in its transcript, "" when it cannot be read.
pub fn chat_title(path: &str) -> String {
    let mut t = String::new();
    for d in lines_of(path) {
        if s(&d, "type") == "custom-title" { if let Some(x) = d.get("customTitle").and_then(Value::as_str) { t = x.to_string(); } }
    }
    t.trim().to_string()
}
/// The chat's title when it starts with a crew name (so a chat whose first message is a compaction summary is still known), else None.
pub fn title_if_crew(path: &str, crew: &fancy_regex::Regex) -> Option<String> {
    let t = chat_title(path);
    if t.is_empty() { return None; }
    let anchored = re(&format!("^(?:{})", crew.as_str()));
    if is(&anchored, &t) { Some(t) } else { None }
}

/// The compaction summary's text: when no .muster-first file was kept, it is the one place left that names the chat.
pub fn compact_summary(path: &str) -> String {
    for d in lines_of(path) {
        if s(&d, "type") == "user" && d.get("isCompactSummary").and_then(Value::as_bool) == Some(true) {
            return content_text(&msg_content(&d)).chars().take(6000).collect();
        }
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

/// True when the choice card (an AskUserQuestion with this id) got no answer from him: its result is an error, says he does not want to
/// proceed, or never came back. Then there is nothing to record (item 53).
pub fn card_skipped(path: &str, use_id: &str) -> bool {
    if use_id.is_empty() || std::fs::metadata(path).is_err() { return false; } // an unreadable transcript is never "skipped"
    for d in lines_of(path) {
        if s(&d, "type") != "user" { continue; }
        if let Value::Array(a) = msg_content(&d) {
            for b in &a {
                if s(b, "type") == "tool_result" && s(b, "tool_use_id") == use_id {
                    let body = content_text(b.get("content").unwrap_or(&Value::Null));
                    return b.get("is_error").and_then(Value::as_bool).unwrap_or(false) || body.contains("doesn't want to proceed") || body.contains("has not answered");
                }
            }
        }
    }
    true
}

/// Messages really sent: a SendMessage whose result came back without an error.
pub fn all_sent_text(path: &str) -> Vec<String> { all_sent_pairs(path).into_iter().map(|(_, t)| t).collect() }

/// The same, with the recipient: (to, text).
pub fn all_sent_pairs(path: &str) -> Vec<(String, String)> {
    let mut calls: Vec<(String, (String, String))> = vec![];
    let (mut done, mut failed): (HashSet<String>, HashSet<String>) = (HashSet::new(), HashSet::new());
    for d in lines_of(path) {
        if let Value::Array(a) = msg_content(&d) {
            for b in &a {
                if !b.is_object() { continue; }
                if s(&d, "type") == "assistant" && s(b, "type") == "tool_use" && s(b, "name") == "SendMessage" {
                    calls.push((s(b, "id").to_string(), b.get("input").map(|i| (s(i, "to").to_string(), s(i, "message").to_string())).unwrap_or_default()));
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

/// True when a Stop hook already bounced a reply in this turn (the turn starts at the last message that is not hook feedback, so an app
/// event or a new typed message starts a fresh one). A check bounces at most once per turn (item 57).
pub fn bounced_this_turn(path: &str) -> bool {
    let mut bounced = false;
    for d in lines_of(path) {
        if s(&d, "type") != "user" { continue; }
        let c = msg_content(&d);
        if let Value::Array(a) = &c { if a.iter().any(|b| s(b, "type") == "tool_result") { continue; } }
        let t = content_text(&c);
        if t.trim().is_empty() { continue; }
        let t = t.trim_start();
        if t.starts_with("Stop hook feedback") || t.starts_with("Stop hook blocking error") { bounced = true; }
        else if !t.starts_with("<system-reminder") { bounced = false; }
    }
    bounced
}

/// True if this turn was started by the owner's typed message and it asks something: a question mark, or a question word or request
/// ("why", "how", "tell me", "look at", "check" ...) in his words (item 57).
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
    last.contains('?') || is(&rei(r"^\s*(what|why|how|when|where|who|which|can|could|would|will|did|does|do|is|are|was|were|should|tell|show|explain|look|check|find|list|give|say|read|open|run)\b|\b(tell me|show me|let me know|how come|what's|look at|or (is|are|do|does|should|can|would)|is (that|it|this)|do (i|we)|should (i|we)|can (i|we))\b"), &last)
}

/// True when this turn was started by a message from another chat or an app event, not the owner's typed words (item 75).
pub fn peer_started(path: &str) -> bool {
    let ends = rei(r"<cross-session-message|<task-notification|<side-sessions-event|<ci-monitor-event|\[SYSTEM NOTIFICATION");
    let neutral = rei(r"^\s*(<system-reminder|Stop hook feedback)");
    let mut last = false;
    for d in lines_of(path) {
        if s(&d, "type") != "user" { continue; }
        let c = msg_content(&d);
        if let Value::Array(a) = &c { if a.iter().any(|b| s(b, "type") == "tool_result") { continue; } }
        let t = content_text(&c);
        if t.trim().is_empty() { continue; }
        if is(&ends, &t) { last = true; } else if !is(&neutral, &t) { last = false; }
    }
    last
}

/// The letter he typed (A to D) when this turn was started by his bare typed letter and the manager's last text asked a lettered
/// question (***A.*** ...); else None. Messages from other chats, app events, hook feedback and system reminders are not his words (item 80, D-037).
pub fn typed_letter_answer(path: &str) -> Option<String> {
    let ends = rei(r"<cross-session-message|<task-notification|<side-sessions-event|<ci-monitor-event|\[SYSTEM NOTIFICATION");
    let neutral = rei(r"^\s*(<system-reminder|Stop hook feedback)");
    let letter = re(r"^\s*\(?([A-Da-d])\)?[.:!]*\s*$");
    let lettered = re(r"(?m)^\s*\*{2,3}[A-D]\.\*{2,3}");
    let (mut prev, mut last) = (String::new(), None::<String>);
    for d in lines_of(path) {
        let c = msg_content(&d);
        match s(&d, "type") {
            "assistant" => if let Value::Array(a) = &c {
                let t: Vec<&str> = a.iter().filter(|b| s(b, "type") == "text").map(|b| s(b, "text")).collect();
                let t = t.join(" ").trim().to_string();
                if !t.is_empty() { prev = t; }
            },
            "user" => {
                if let Value::Array(a) = &c { if a.iter().any(|b| s(b, "type") == "tool_result") { continue; } }
                let t = content_text(&c);
                if t.trim().is_empty() || is(&neutral, &t) { continue; }
                if is(&ends, &t) { last = None; continue; }
                last = letter.captures(&t).ok().flatten().and_then(|m| m.get(1)).filter(|_| is(&lettered, &prev)).map(|m| m.as_str().to_uppercase());
            }
            _ => {}
        }
    }
    last
}

/// True when the reply writes two or more lettered choice lines and any of them is not ***A.*** (bold and italic) (item 80).
pub fn letters_not_bold_italic(text: &str) -> bool {
    let any = re(r"^\s*(?:[-+*]\s+)?(?:\*{1,3}|_)?\(?[A-D][.)]\*{0,3}\s"); // a list marker before the letter counts, and is never good
    let good = re(r"^\s*\*\*\*[A-D]\.\*\*\*\s");
    let lines: Vec<&str> = text.lines().filter(|l| is(&any, l)).collect();
    lines.len() >= 2 && lines.iter().any(|l| !is(&good, l))
}

/// The choices of a lettered question, each reduced to its words (no letter, no "my pick"); empty unless there are two or more (item 114).
pub fn question_key(text: &str) -> HashSet<String> {
    let line = re(r"(?m)^\*\*\*[A-D]\.\*\*\*\s*(.*)$");
    let pick = rei(r"\(?\*?my pick\*?\)?");
    let junk = re(r"[^a-z0-9]+");
    let mut opts: HashSet<String> = HashSet::new();
    let mut n = 0;
    for c in line.captures_iter(text).flatten() {
        let b = sub(&pick, c.get(1).map(|m| m.as_str()).unwrap_or(""), " ").to_lowercase();
        let b = sub(&junk, &b, " ").trim().to_string();
        if !b.is_empty() { n += 1; opts.insert(b.chars().take(60).collect()); }
    }
    if n >= 2 { opts } else { HashSet::new() }
}

/// A plain question of any length (the owner said any form): a reply holding a "?" outside a web address (for example "Coverage order: A (...) or B (...)?").
pub fn one_line_question(text: &str) -> bool {
    sub(&re(r"https?://\S+"), text, " ").contains('?')
}

/// What a reply asks him, in any form (item 114): (the lettered choices' key or empty, its content words, whether it is a one-line question); None when it asks nothing.
pub type QInfo = (HashSet<String>, HashSet<String>, bool);
pub fn question_info(text: &str) -> Option<QInfo> {
    let key = question_key(text);
    if key.is_empty() && !one_line_question(text) { return None; }
    let pick = rei(r"\(?\*?my pick\*?\)?");
    let lower = sub(&pick, text, " ").to_lowercase();
    let toks: HashSet<String> = re(r"[a-z0-9]{3,}").find_iter(&lower).flatten().map(|m| m.as_str().to_string()).filter(|w| w != "pick").collect();
    let one = key.is_empty();
    Some((key, toks, one))
}

/// The same question put again, whatever its form: two lettered ones by their choices; otherwise the one-liner's words (three or more) found 70% or more in the other reply.
pub fn same_question(a: &QInfo, b: &QInfo) -> bool {
    if !a.0.is_empty() && !b.0.is_empty() {
        let i = a.0.intersection(&b.0).count() as f64; let u = a.0.union(&b.0).count() as f64;
        return i / u >= 0.7;
    }
    let (small, big) = if a.2 && (!b.2 || a.1.len() <= b.1.len()) { (a, b) } else { (b, a) };
    small.1.len() >= 3 && small.1.intersection(&big.1).count() as f64 / small.1.len() as f64 >= 0.7
}

/// Item 114: this question, in any form (lettered, one-line, a long card), matches one already put to him since his last typed words and not yet
/// answered. A reply the Stop hook bounced does not count; his typed message clears the list; a message from another chat does not.
pub fn question_repeated(path: &str, text: &str) -> bool {
    let mine = match question_info(text) { Some(m) => m, None => return false };
    let ends = rei(r"<cross-session-message|<task-notification|<side-sessions-event|<ci-monitor-event|\[SYSTEM NOTIFICATION");
    let neutral = rei(r"^\s*(<system-reminder|Stop hook feedback)");
    let bounce = re(r"^\s*Stop hook (feedback|blocking error)");
    let mut seen: Vec<(QInfo, String)> = vec![];
    let mut user_after = false;
    for d in lines_of(path) {
        let c = msg_content(&d);
        match s(&d, "type") {
            "assistant" => if let Value::Array(a) = &c {
                let t: Vec<&str> = a.iter().filter(|b| s(b, "type") == "text").map(|b| s(b, "text")).collect();
                let t = t.join("\n");
                if let Some(k) = question_info(&t) { seen.push((k, t)); user_after = false; }
            },
            "user" => {
                if let Value::Array(a) = &c { if a.iter().any(|b| s(b, "type") == "tool_result") { continue; } }
                let t = content_text(&c);
                if t.trim().is_empty() { continue; }
                user_after = true;
                if is(&bounce, &t) { seen.pop(); }
                else if is(&ends, &t) || is(&neutral, &t) {}
                else { seen.clear(); }
            }
            _ => {}
        }
    }
    if !user_after { if let Some((_, t)) = seen.last() { if t.trim() == text.trim() { seen.pop(); } } }
    seen.iter().any(|(k, _)| same_question(&mine, k))
}

/// Item 114: news words on a line that is neither a choice nor a question, in a reply that carries a lettered question.
pub fn news_with_question(text: &str) -> bool {
    let line = re(r"^\*\*\*[A-D]\.\*\*\*");
    if text.lines().filter(|l| is(&line, l.trim())).count() < 2 { return false; }
    let up = re(r"\b(PASS|LIVE|DONE)\b");
    let lo = rei(r"\b(shipped|passed|merged|released|progress|landed|finished)\b");
    text.lines().any(|l| !is(&line, l.trim()) && !l.contains('?') && (is(&up, l) || is(&lo, l)))
}

/// Item 115: True when this turn was started by his typed words and they are a question: a "?" or a question word first.
pub fn owner_questioned(path: &str) -> bool {
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
    last.contains('?') || is(&rei(r"^\s*(what|why|how|when|where|who|which|can|could|would|will|did|does|do|is|are|was|were|should)\b"), &last)
}

/// True when the owner's list (path relative to the project) holds a recorded "Choice (" line under that item (item 115).
pub fn choice_recorded(root: &str, rel: &str, item: i64) -> bool {
    let Ok(text) = fs::read_to_string(Path::new(if root.is_empty() { "." } else { root }).join(rel)) else { return false };
    let lines: Vec<&str> = text.split('\n').collect();
    let (mut fenced, mut start) = (false, None);
    let head = re(&format!(r"^{item}\.\s"));
    for (i, l) in lines.iter().enumerate() {
        if l.trim().starts_with("```") { fenced = !fenced; continue; }
        if !fenced && start.is_none() && is(&head, l) { start = Some(i); }
    }
    let Some(st) = start else { return false };
    let stop = re(r"^(\d+\.\s|#)");
    let mut end = st + 1;
    while end < lines.len() && !is(&stop, lines[end]) { end += 1; }
    lines[st..end].iter().any(|l| is(&re(r"^\s+Choice \("), l))
}

pub fn exists(p: &Path) -> bool { p.exists() }
pub fn read_all<R: Read>(mut r: R) -> String { let mut t = String::new(); let _ = r.read_to_string(&mut t); t }

/// The project's top-level folder and file names as codes, from git at `rev` (or HEAD) in `dir`; empty when git cannot say.
pub fn project_things(dir: &str, rev: &str) -> HashSet<String> {
    let run = |r: &str| {
        let mut c = std::process::Command::new("git");
        c.args(["ls-tree", "--name-only", "--full-tree", r]);
        if !dir.is_empty() { c.current_dir(dir); }
        c.output().ok().filter(|o| o.status.success()).map(|o| String::from_utf8_lossy(&o.stdout).to_string())
    };
    let out = (if rev.is_empty() { None } else { run(rev) }).or_else(|| run("HEAD")).unwrap_or_default();
    out.lines().map(|l| crate::record::thing_code(l.trim_matches('"'))).filter(|c| !c.is_empty()).collect()
}

#[cfg(test)]
mod rule_groups_tests {
    use super::*;
    #[test]
    fn house_rules_have_a_switch_and_safety_stops_have_none() {
        let dir = std::env::temp_dir().join(format!("muster-rules-{}", std::process::id()));
        let _ = fs::create_dir_all(&dir);
        let all: Vec<String> = ["pick-marked", "record-form", "note-card"].iter().map(|x| format!("\"{x}\": false")).chain(SAFETY.iter().map(|x| format!("\"{x}\": false"))).collect();
        let prof = dir.join("p.json");
        fs::write(&prof, format!("{{\"name\": \"Other\", \"house_rules\": {{{}}}}}", all.join(", "))).unwrap();
        std::env::set_var("MUSTER_PROFILE", &prof);
        assert!(!rule_on("pick-marked") && !rule_on("record-form") && !rule_on("note-card"), "a house rule switched off is off");
        assert!(rule_on("asked-twice"), "a house rule the profile does not name stays on");
        for r in SAFETY { assert!(rule_on(r), "{r} is a safety stop: no switch"); }
        assert!(group_label("guard").contains("safety stop") && group_label("pick-marked").contains("house rule \"pick-marked\" of Muster"));
        std::env::remove_var("MUSTER_PROFILE");
        let _ = fs::remove_dir_all(&dir);
    }
}
