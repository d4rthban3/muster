//! The worker queue check (port of scripts/worker-queue-check.py): before a worker's turn ends, read the board and the owner's list for open
//! work addressed to this worker; if the last message does not name it, the stop is refused once. Stop hook; silent on any error, as the Python copy is.
use crate::common::*;
use fancy_regex::Regex;
use serde_json::Value;
use std::collections::BTreeSet;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::Command;

fn read(p: &Path) -> String { fs::read(p).map(|b| String::from_utf8_lossy(&b).to_string()).unwrap_or_default() }

/// Python's str.splitlines for the separators that can show up in a text file.
fn py_lines(t: &str) -> Vec<&str> {
    let mut out = vec![];
    let (mut start, mut it) = (0usize, t.char_indices().peekable());
    while let Some((i, c)) = it.next() {
        let brk = matches!(c, '\n' | '\r' | '\x0b' | '\x0c' | '\x1c' | '\x1d' | '\x1e' | '\u{85}' | '\u{2028}' | '\u{2029}');
        if !brk { continue; }
        out.push(&t[start..i]);
        let mut end = i + c.len_utf8();
        if c == '\r' { if let Some(&(j, '\n')) = it.peek() { it.next(); end = j + 1; } }
        start = end;
    }
    if start < t.len() { out.push(&t[start..]); }
    out
}

/// re.split(r"\n(?=<ahead>)", text): the text cut at each newline that is followed by the pattern.
fn split_before(text: &str, ahead: &str) -> Vec<String> {
    let r = re(&format!(r"\n(?={ahead})"));
    let mut parts = vec![];
    let mut last = 0;
    for m in r.find_iter(text).flatten() { parts.push(text[last..m.start()].to_string()); last = m.end(); }
    parts.push(text[last..].to_string());
    parts
}

fn norm(t: &str) -> String { re(r"[^a-z0-9]+").replace_all(&t.to_lowercase(), "-").trim_matches('-').to_string() }

fn main_folder(cwd: &Path) -> Option<PathBuf> {
    let out = Command::new("git").args(["rev-parse", "--git-common-dir"]).current_dir(cwd).output().ok()?;
    let out = String::from_utf8_lossy(&out.stdout).trim().to_string();
    if out.is_empty() { return None; }
    let p = cwd.join(out);
    fs::canonicalize(&p).unwrap_or(p).parent().map(Path::to_path_buf)
}

/// The crew name whose "Folder copy" cell names this folder (its last path part).
fn my_name(main: &Path, cwd: &Path) -> String {
    let text = read(&main.join("muster").join("CREW.md"));
    let block = caps(&re(r"(?s)## Running now(.*?)(?:\n## |\z)"), &text).and_then(|c| c.get(1).map(|m| m.as_str().to_string())).unwrap_or_default();
    let real = fs::canonicalize(cwd).unwrap_or_else(|_| cwd.to_path_buf());
    let here = real.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default();
    let cell = re(&format!(r"(?:^|[/\\ ]){}(?:\s|$|\))", fancy_regex::escape(&here)));
    for line in py_lines(&block) {
        let cells: Vec<&str> = line.trim().trim_matches('|').split('|').map(str::trim).collect();
        if cells.len() >= 4 && cells[0] != "Name" && !cells[0].is_empty() && is(&cell, cells[3]) { return cells[0].to_string(); }
    }
    String::new()
}

fn finished(blk: &str, job: &str) -> bool {
    let Some(h) = caps(&re(r"^### \S+ \| (PASS|DONE) \| [^|]*\| (.*)"), blk) else { return false };
    let mut first: Vec<&str> = py_lines(blk);
    first.push(""); first.push("");
    let mid = first[1..first.len().min(4)].join(" ");
    let head = mid.split("What:").next().unwrap_or("");
    let nj = norm(job);
    norm(&h[2]).contains(&nj) || norm(head).contains(&nj)
}

/// [(label, key)]: key is the text the worker's last message must contain.
fn open_work(main: &Path, name: &str) -> Vec<(String, String)> {
    let mut out = vec![];
    let board = read(&main.join("muster").join("BOARD.md"));
    let blocks = split_before(&board, "### ");
    let order = re(r"^### \S+ \| ORDER \| .*? -> ([^|]+?) \| (.*)");
    let open = rei(r"(?m)^Status:\s*open");
    let low = name.to_lowercase();
    for (i, blk) in blocks.iter().enumerate() {
        let Some(h) = caps(&order, blk) else { continue };
        let to = h[1].trim().to_lowercase();
        if (to == low || to == "all") && is(&open, blk) {
            if to == "all" && !blk.to_lowercase().contains(&low) { continue; } // an ALL order counts only if it names this worker
            let job = h[2].trim().to_string();
            if blocks[i + 1..].iter().any(|b| finished(b, &job)) { continue; } // a later PASS or DONE names the same job
            out.push((format!("board order \"{job}\""), job));
        }
    }
    let ol = read(&main.join("muster").join("OWNERS-LIST.md"));
    let open_part = caps(&re(r"(?s)(?:^|\n)## Open\n(.*?)(?:\n## |\z)"), &ol).and_then(|c| c.get(1).map(|m| m.as_str().to_string())).unwrap_or_default();
    let (numr, stands) = (re(r"^(\d+)\. "), re(r"(?m)^\s*Stands:\s*(.*)$"));
    let with = rei(&format!(r"^with\b[^;]*{}", fancy_regex::escape(name)));
    for blk in split_before(&open_part, r"\d+\. ") {
        let (Some(n), Some(st)) = (caps(&numr, blk.trim()), caps(&stands, &blk)) else { continue };
        if is(&with, &st[1]) { out.push((format!("owner's list item {}", &n[1]), format!("item {}", &n[1]))); }
    }
    out
}

fn pick_name(first: &str, names: &BTreeSet<String>) -> String {
    let low = first.to_lowercase();
    let mut by_len: Vec<&String> = names.iter().collect();
    by_len.sort_by_key(|n| std::cmp::Reverse(n.chars().count()));
    for n in by_len {
        if is(&re(&format!(r"you are\s+(?:the\s+)?{}", fancy_regex::escape(&n.to_lowercase()))), &low) { return n.clone(); }
    }
    names.iter().filter_map(|n| low.find(&n.to_lowercase()).map(|p| (low[..p].chars().count(), std::cmp::Reverse(n.chars().count()), n.clone()))).min().map(|t| t.2).unwrap_or_default()
}

struct Row { kind: String, from: String, to: Vec<String>, text: String }

fn rows(board: &str) -> Vec<Row> {
    let line = re(r"^(\S+)\s*\|\s*([A-Za-z]+)\s*\|\s*(.*?)\s*->\s*(.*?)\s*\|\s*(.*)$");
    py_lines(board).into_iter().filter_map(|l| {
        let m = caps(&line, l.trim())?;
        Some(Row { kind: m[2].to_uppercase(), from: m[3].trim().to_string(), to: m[4].split(',').map(|x| x.trim().to_string()).collect(), text: m[5].to_string() })
    }).collect()
}

fn line_open_work(board: &str, name: &str) -> Vec<(String, Vec<String>)> {
    let rows = rows(board);
    let low = name.to_lowercase();
    let start = rows.iter().rposition(|r| r.from.to_lowercase() == low && ["DONE", "PASS", "FAIL", "READY", "STUCK"].contains(&r.kind.as_str())).map(|i| i + 1).unwrap_or(0);
    let (action, word) = (rei(r"Action:\s*(start|ship)\b"), re(r"[A-Za-z]{5,}"));
    let mut out = vec![];
    for r in &rows[start..] {
        if ["RULE", "NEED", "READY", "ORDER", "FAIL"].contains(&r.kind.as_str()) && r.to.iter().any(|x| x.to_lowercase() == low) && is(&action, &r.text) {
            let mut keys = vec![r.from.clone()];
            keys.extend(word.find_iter(&r.text).flatten().take(3).map(|m| m.as_str().to_lowercase()));
            out.push((format!("{} from {}: {}", r.kind, r.from, r.text.chars().take(60).collect::<String>()), keys));
        }
    }
    out
}

fn line_names(board: &str) -> BTreeSet<String> {
    let mut names = BTreeSet::new();
    for r in rows(board) { names.insert(r.from); names.extend(r.to); }
    names.into_iter().filter(|n| n.contains('_')).collect()
}

fn tail(path: &str, n: u64) -> Option<String> {
    let mut f = fs::File::open(path).ok()?;
    let len = f.metadata().ok()?.len();
    std::io::Seek::seek(&mut f, std::io::SeekFrom::Start(len.saturating_sub(n))).ok()?;
    let mut b = vec![];
    f.read_to_end(&mut b).ok()?;
    Some(String::from_utf8_lossy(&b).to_string())
}

fn last_message(data: &Value) -> String {
    if let Some(m) = data.get("last_assistant_message").and_then(Value::as_str) { return m.to_string(); }
    let Some(text) = tail(s(data, "transcript_path"), 200000) else { return String::new() };
    for line in py_lines(&text).into_iter().rev() {
        let Ok(e) = serde_json::from_str::<Value>(line) else { continue };
        if s(&e, "type") == "assistant" {
            return match e.get("message").and_then(|m| m.get("content")) {
                Some(Value::Array(a)) => a.iter().filter(|b| b.is_object()).map(|b| s(b, "text")).collect::<Vec<_>>().join(" "),
                Some(Value::String(t)) => t.clone(),
                Some(v) if !v.is_null() => v.to_string(),
                _ => "None".into(),
            };
        }
    }
    String::new()
}

fn wait_re() -> Regex {
    let answer = r"(?:choice|decision|answer|go-ahead|go ahead|reply|call|approval|go)\b";
    re(&format!(r"(?im)\b(?:waiting|wait|waits|blocked|stuck)\s+(?:on|for)\s+(?:the\s+)?manager\b(?!\W?s?\s+(?:page|rules|check|file|definition))|\bmanager\W?s\s+{answer}|\bneeds?\s+(?:the\s+manager(?:\W?s)?|his)\s+{answer}|\bneeds?\s+the\s+manager\s+to\b|^\s*WAIT\b[^\n]*\bmanager\b"))
}

/// Tool calls (name, input text) made since the last real user message, read from the end of the transcript; None when it cannot be read.
fn turn_calls(path: &str) -> Option<Vec<(String, String)>> {
    let text = tail(path, 400000)?;
    let mut calls = vec![];
    for line in py_lines(&text).into_iter().rev() {
        let Ok(e) = serde_json::from_str::<Value>(line) else { continue };
        let c = e.get("message").and_then(|m| m.get("content"));
        match s(&e, "type") {
            "user" => {
                if let Some(Value::Array(a)) = c { if a.iter().all(|b| b.is_object() && s(b, "type") == "tool_result") { continue; } }
                return Some(calls);
            }
            "assistant" => if let Some(Value::Array(a)) = c {
                for b in a { if b.is_object() && s(b, "type") == "tool_use" { calls.push((s(b, "name").to_string(), b.get("input").cloned().unwrap_or(Value::Object(Default::default())).to_string())); } }
            },
            _ => {}
        }
    }
    Some(calls)
}

fn waiting_unreported(data: &Value) -> Option<&'static str> {
    if !is(&wait_re(), &last_message(data)) { return None; }
    let calls = turn_calls(s(data, "transcript_path"))?;
    for (name, inp) in calls {
        let low = inp.to_lowercase();
        if name.to_lowercase().contains("send") && low.contains("manager") { return None; }
        if ["Write", "Edit", "Bash"].contains(&name.as_str()) && low.contains("board") { return None; }
    }
    Some("Your reply says you are waiting on, or need, the manager, but this turn sent the manager nothing: a chat reply alone is not seen. Send the manager one message (NEED, STUCK or READY) now, or write the line on the board.")
}

fn refuse(reason: &str) { say(&py_obj(&[("decision", "block".into()), ("reason", format!("{reason}{NOREPEAT}"))])); }

/// The hook's JSON on standard input: nothing at all is an empty object; anything that is not an object ends the check in silence.
fn stdin_object() -> Option<Value> {
    let mut b = vec![];
    std::io::stdin().read_to_end(&mut b).ok()?;
    let t = String::from_utf8(b).ok()?;
    let v: Value = serde_json::from_str(if t.is_empty() { "{}" } else { &t }).ok()?;
    v.is_object().then_some(v)
}

/// A line-style board (PINR): the worker is named in the chat's first message.
fn main_lines(args: &[String], cwd: &Path, profile: &Value) -> i32 {
    let list = args.iter().any(|a| a == "--list");
    let Some(rel) = profile.get("board").and_then(Value::as_str) else { return 0 };
    let root = { let d = exe_dir(); if d.file_name().map(|n| n == ".muster-checks").unwrap_or(false) { d.parent().map(Path::to_path_buf).unwrap_or_default() } else { cwd.to_path_buf() } };
    let board = read(&root.join(rel));
    if board.is_empty() {
        if list { say(&format!("no board found at {}", root.join(rel).display())); }
        return 0;
    }
    if list && !args.iter().any(|a| a == "--worker") {
        say("give the worker: --list --worker \"<name>\" (for example the name in a board line's '-> name')");
        return 0;
    }
    let data = if list { Value::Object(Default::default()) } else { match stdin_object() { Some(d) => d, None => return 0 } };
    if !data.get("transcript_path").map(|v| v.is_string() || !truthy(Some(v))).unwrap_or(true) { return 0; }
    let name = if list {
        match args.iter().position(|a| a == "--worker").and_then(|i| args.get(i + 1)) { Some(n) => n.clone(), None => return 0 }
    } else {
        let tp = s(&data, "transcript_path");
        let names = line_names(&board);
        let n = pick_name(&first_message(tp), &names);
        if n.is_empty() { pick_name(&format!("You are {}", chat_title(tp)), &names) } else { n }
    };
    if name.is_empty() || is(&re(r"\bManager_"), &name) { return 0; }
    let work = line_open_work(&board, &name);
    if list {
        say(&format!("{name}: {}", if work.is_empty() { "nothing open".to_string() } else { work.iter().map(|w| w.0.as_str()).collect::<Vec<_>>().join("; ") }));
        return 0;
    }
    if truthy(data.get("stop_hook_active")) { return 0; }
    if let Some(why) = waiting_unreported(&data) { refuse(why); return 0; }
    if work.is_empty() { return 0; }
    let msg = last_message(&data).to_lowercase();
    let missing: Vec<&str> = work.iter().filter(|(_, keys)| !keys.iter().any(|k| msg.contains(&k.to_lowercase()))).map(|w| w.0.as_str()).collect();
    if missing.is_empty() { return 0; }
    refuse(&format!("Do not go idle: open work is addressed to you ({}). Do it now, or if you are waiting, say in your reply what you are waiting for and name who gave it. If it is not yours, tell the manager.", missing.join("; ")));
    0
}

pub fn run(args: &[String]) -> i32 {
    let profile = load_profile();
    let mut cwd = std::env::current_dir().unwrap_or_default();
    if profile.get("board_style").and_then(Value::as_str) == Some("lines") && truthy(profile.get("board")) { return main_lines(args, &cwd, &profile); }
    if let Some(i) = args.iter().position(|a| a == "--project") { match args.get(i + 1) { Some(p) => cwd = PathBuf::from(p), None => return 0 } }
    let Some(main) = main_folder(&cwd) else { return 0 };
    if !main.join("muster").join("BOARD.md").is_file() { return 0; }
    let real = |p: &Path| fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf());
    if real(&main) == real(&cwd) { return 0; } // the manager's own folder: idle-check handles it
    let name = my_name(&main, &cwd);
    if name.is_empty() { return 0; }
    let work = open_work(&main, &name);
    if args.iter().any(|a| a == "--list") {
        say(&format!("{name}: {}", if work.is_empty() { "nothing open".to_string() } else { work.iter().map(|w| w.0.as_str()).collect::<Vec<_>>().join("; ") }));
        return 0;
    }
    let Some(data) = stdin_object() else { return 0 };
    if truthy(data.get("stop_hook_active")) { return 0; }
    if let Some(why) = waiting_unreported(&data) { refuse(why); return 0; }
    if work.is_empty() { return 0; }
    let msg = last_message(&data).to_lowercase();
    let missing: Vec<&str> = work.iter().filter(|(_, k)| !msg.contains(&k.to_lowercase())).map(|w| w.0.as_str()).collect();
    if missing.is_empty() { return 0; }
    refuse(&format!("Do not go idle: open work is addressed to you ({}). Do it now (the next piece), or if you are waiting, say in your reply what you are waiting for and name the job. If it is not yours, send the manager one NEED.", missing.join("; ")));
    0
}
