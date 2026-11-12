//! Stop check for the manager: no turn ends while the board holds an open question for the owner that the reply does not name
//! (port of hooks/board-stop.py).
use crate::common::*;
use serde_json::Value;
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Clone)]
struct Entry { kind: String, from: String, job: String, status: String, paused: bool, resumed: bool }

fn entries(text: &str) -> Vec<Entry> {
    let (head, status_re, pause_yes, pause_no) = (re(r"^\s*###\s"), rei(r"^\s*status\s*:\s*([A-Za-z]+)"), rei(r"^\s*paused\s*:\s*yes"), rei(r"^\s*paused\s*:\s*no"));
    let arrow = re(r"\s*->.*");
    let (mut out, mut cur, mut fenced): (Vec<Entry>, Option<Entry>, bool) = (vec![], None, false);
    for line in text.lines() {
        if line.trim().starts_with("```") { fenced = !fenced; continue; }
        if fenced { continue; }
        if is(&head, line) {
            if let Some(c) = cur.take() { out.push(c); }
            let parts: Vec<String> = line.split('|').map(|p| p.trim_matches(|c| c == ' ' || c == '#' || c == '`').to_string()).collect();
            let frm = parts.get(2).map(|p| sub(&arrow, p, "")).unwrap_or_default();
            cur = Some(Entry { kind: parts.get(1).map(|p| p.to_uppercase()).unwrap_or_default(), from: frm, job: parts.get(3).cloned().unwrap_or_default(), status: "open".into(), paused: false, resumed: false });
        } else if let Some(c) = cur.as_mut() {
            if let Some(m) = caps(&status_re, line) { c.status = m[1].to_lowercase(); }
            if is(&pause_yes, line) { c.paused = true; }
            if is(&pause_no, line) { c.resumed = true; }
        }
    }
    if let Some(c) = cur { out.push(c); }
    out
}

/// A board whose entries are single lines: "DATE | KIND | from -> to | text" (PINR). File order, oldest first.
fn line_entries(text: &str) -> Vec<Entry> {
    let row = re(r"^\s*\d{4}-\d\d-\d\d\s*\|\s*([A-Za-z ]+?)\s*\|\s*([^|]*?)\s*\|\s*(.*)$");
    let (yes, no, arrow) = (rei(r"\bpaused\s*:\s*yes"), rei(r"\bpaused\s*:\s*no"), re(r"\s*->.*"));
    text.lines().filter_map(|l| caps(&row, l).map(|m| Entry { kind: m[1].to_uppercase(), from: sub(&arrow, &m[2], ""), job: String::new(), status: "open".into(), paused: is(&yes, l), resumed: is(&no, l) })).collect()
}

fn manager_re(profile: &Value) -> fancy_regex::Regex {
    let mut p = String::from(r"agents[/\\]manager\.md|\bManager_[^_\n]*_\d{3}\b");
    for x in pstrings(profile, "manager_names") { p.push_str(&format!("|(?:{x})")); }
    re(&p)
}

fn card_answered_this_turn(path: &str) -> bool {
    let data = match fs::read(path) { Ok(d) => d, Err(_) => return true };
    let start = data.len().saturating_sub(3_000_000);
    let raw = String::from_utf8_lossy(&data[start..]).to_string();
    let (mut last_human, mut card_after) = (None::<bool>, false);
    for l in raw.split('\n') {
        let Ok(d) = serde_json::from_str::<Value>(l) else { continue };
        let c = d.get("message").and_then(|m| m.get("content")).cloned().unwrap_or(Value::Null);
        match s(&d, "type") {
            "user" => {
                let human = matches!(&c, Value::String(_)) || c.as_array().map(|a| a.iter().any(|b| s(b, "type") == "text")).unwrap_or(false);
                if human { last_human = Some(true); card_after = false; }
            }
            "assistant" => if let Some(a) = c.as_array() { if a.iter().any(|b| s(b, "type") == "tool_use" && s(b, "name") == "AskUserQuestion") { card_after = true; } },
            _ => {}
        }
    }
    if last_human.is_none() { true } else { card_after }
}

pub fn run() -> i32 {
    let Some(data) = read_stdin() else { return 0 };
    if stood_down(&data, "board-stop.py") { return 0; }
    let profile = load_profile();
    if data.get("stop_hook_active").and_then(Value::as_bool).unwrap_or(false) { return 0; }
    if bounced_this_turn(s(&data, "transcript_path")) { return 0; }
    let tpath = s(&data, "transcript_path");
    let mgr_re = manager_re(&profile);
    if std::env::var("MUSTER_ASSUME_MANAGER").ok().as_deref() != Some("1") {
        let first: String = first_message(tpath);
        if !is(&mgr_re, &first) { return 0; }
    }
    let cwd = { let c = s(&data, "cwd"); if c.is_empty() { std::env::current_dir().unwrap_or_default() } else { c.into() } };
    let cwd = std::path::absolute(&cwd).unwrap_or(cwd);
    if cwd.components().any(|c| c.as_os_str() == "worktrees") { return 0; }
    let mut path = cwd.join("muster").join("BOARD.md");
    if let Some(b) = profile.get("board").and_then(Value::as_str).filter(|b| !b.is_empty()) {
        path = exe_dir().parent().map(Path::to_path_buf).unwrap_or_default().join(b);
    }
    if !path.is_file() { return 0; }
    let Ok(text) = fs::read_to_string(&path) else { return 0 };
    let lines_style = profile.get("board_style").and_then(Value::as_str) == Some("lines");
    let mut items = if lines_style { line_entries(&text) } else { entries(&text) };
    let said = s(&data, "last_assistant_message").to_lowercase();
    if let Ok(rd) = fs::read_dir(cwd.join(".claude").join("worktrees")) {
        let mut dirs: Vec<_> = rd.filter_map(Result::ok).collect();
        dirs.sort_by_key(|e| e.file_name());
        for e in dirs {
            let p = e.path().join(".muster-paused");
            if p.is_file() {
                let who = fs::read_to_string(&p).ok().and_then(|t| t.lines().next().map(|l| l.trim().to_string())).filter(|l| !l.is_empty()).unwrap_or_else(|| e.file_name().to_string_lossy().to_string());
                items.push(Entry { kind: String::new(), from: who, job: String::new(), status: "open".into(), paused: true, resumed: false });
            }
        }
    }
    let kinds_open = profile.get("board_kinds_open") != Some(&Value::Bool(false));
    let mut last: HashMap<String, usize> = HashMap::new();
    for (i, e) in items.iter().enumerate() { last.insert(e.from.clone(), i); }
    let mut missed: Vec<Entry> = vec![];
    for i in 0..items.len() {
        let mut e = items[i].clone();
        let attn = |k: &str| matches!(k, "NEED" | "STUCK" | "OWNER CALL");
        if e.paused && (e.resumed || last[&e.from] != i) {
            e.paused = false;
            if !attn(&e.kind) { continue; }
        }
        if e.status == "done" || e.status == "closed" { continue; }
        if !(e.paused || (kinds_open && attn(&e.kind))) { continue; }
        if (!e.from.is_empty() && said.contains(&e.from.to_lowercase())) || (!e.job.is_empty() && said.contains(&e.job.to_lowercase())) { continue; }
        missed.push(e);
    }
    let picks_re = rei(r"fits what you want|fits what you said|i'?m recording|i am recording|i'?ll record|i will record|i went with|i'?ll go with|i will go with|i'?m going with|i am going with|i picked|i chose|i'?ve chosen|i have chosen|so [a-d] (fits|it is)|recording (it|that|this) as");
    let told_re = rei(r"you (picked|chose|clicked|selected)");
    let picks = is(&picks_re, &said) && !is(&told_re, &said) && !card_answered_this_turn(tpath);
    if missed.is_empty() && !picks { return 0; }
    let favour = "ask him with a choice card, the option you favour marked \"my pick\", and record nothing until he clicks.";
    if picks && missed.is_empty() {
        say(&py_obj(&[("decision", "block".into()), ("reason", format!("You wrote that you are choosing or recording for the owner, but he has not picked this turn. Do not decide for him: ask him now with a choice card, the option you favour marked \"my pick\", and record nothing until he clicks."))]));
        return 0;
    }
    let names: Vec<String> = missed.iter().map(|e| format!("{} ({})", if e.from.is_empty() { "a worker" } else { &e.from }, if e.paused { "paused".to_string() } else { e.kind.clone() })).collect();
    let mut reason = format!("The board holds open items for the owner that you have not told him about: {}. Before you stop, ask him the top one as a choice card, or say \"<worker> is waiting for you: type in <chat link>\" for a paused chat; then stop.", names.join("; "));
    if picks { reason.push_str(&format!(" Also: you wrote that you are choosing or recording for the owner, but he has not picked this turn; {favour}")); }
    say(&py_obj(&[("decision", "block".into()), ("reason", reason)]));
    0
}
