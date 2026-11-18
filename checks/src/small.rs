//! The three small hooks and the usage line (ports of hooks/renew-after-summary.py, hooks/precompact-board.py and scripts/usage.py).
use crate::common::*;
use crate::talk::ROLE;
use chrono::{Local, TimeZone};
use fancy_regex::Regex;
use serde_json::Value;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;

/// The three crew-name patterns of renew-after-summary.py: the role file, the chat name, and the profile's own names (crew + manager).
struct Crew { role: Regex, name: Regex, profile: Vec<Regex> }

fn crew(profile: &Value) -> Option<Crew> {
    let mut profile_re = vec![];
    for x in pstrings(profile, "crew_names").into_iter().chain(pstrings(profile, "manager_names")) {
        profile_re.push(Regex::new(&x).ok()?); // a pattern the Python copy cannot compile ends it in silence; so does this
    }
    Some(Crew {
        role: re(r"agents[/\\](manager|builder|designer|inspector|design-inspector|sketchpad|ai-socket|agent-teacher)\.md"),
        name: re(&format!(r"\b{ROLE}_[^\s_][^_\n]*?(?:_\d{{3}})?\b")),
        profile: profile_re,
    })
}

fn starts(r: &Regex, t: &str) -> bool { find(r, t).map(|m| m.start() == 0).unwrap_or(false) }

/// The chat's first message, or "You are <title>" when the file opens with a summary and the title names a crew chat.
fn crew_first(c: &Crew, path: &str) -> String {
    let mut first = first_message(path);
    let known = is(&c.role, &first) || is(&c.name, &first) || c.profile.iter().any(|p| is(p, &first));
    if !known {
        let t = chat_title(path);
        if !t.is_empty() && (starts(&c.name, &t) || c.profile.iter().any(|p| starts(p, &t))) { first = format!("You are {t}"); }
    }
    first
}

pub fn renew() -> i32 {
    let Some(data) = read_stdin() else { return 0 };
    let Some(c) = crew(&load_profile()) else { return 0 };
    let first = crew_first(&c, s(&data, "transcript_path"));
    if !(is(&c.role, &first) || is(&c.name, &first) || c.profile.iter().any(|p| is(p, &first))) { return 0; } // not a crew chat
    say("Muster: your conversation was just compacted in place (D-039); carry on, no renewal. Your open job, branch and saved version were written to the board just before it. Re-read your rules page (muster/rules/<your role>.md) and the board entries addressed to you.");
    let mut cands: Vec<PathBuf> = script_roots().into_iter().map(|r| r.join("hooks").join("talk-block.txt")).collect();
    cands.insert(0, exe_dir().join("talk-block.txt"));
    for cand in cands {
        if let Ok(t) = fs::read_to_string(&cand) { say(t.trim_end()); break; }
    }
    0
}

fn git(cwd: &str, args: &[&str]) -> String {
    match Command::new("git").arg("-C").arg(cwd).args(args).output() {
        Ok(o) if o.status.success() => String::from_utf8_lossy(&o.stdout).trim().to_string(),
        _ => String::new(),
    }
}

fn main_folder(cwd: &str) -> String {
    let common = git(cwd, &["rev-parse", "--path-format=absolute", "--git-common-dir"]);
    if common.ends_with(".git") { return Path::new(&common).parent().map(|p| p.to_string_lossy().to_string()).unwrap_or_else(|| cwd.to_string()); }
    cwd.to_string()
}

/// The last job name and the last note this chat sent or received, read from its own transcript (best effort, as the Python copy does).
fn last_facts(path: &str) -> (String, String) {
    let (mut job, mut note) = (String::new(), String::new());
    let Ok(text) = fs::read_to_string(path) else { return (job, note) };
    let job_re = re(r#"\\?"job\\?":\s*\\?"([^"\\]{1,60})"#);
    let note_re = re(r#"\\?"note\\?":\s*\\?"([^"\\]{1,240})"#);
    for line in text.lines() {
        if !line.contains("job") && !line.contains("note") { continue; }
        for m in job_re.captures_iter(line).flatten() { job = m[1].to_string(); }
        for m in note_re.captures_iter(line).flatten() { note = m[1].to_string(); }
    }
    (job, note)
}

pub fn precompact() -> i32 {
    let Some(data) = read_stdin() else { return 0 };
    let Some(c) = crew(&load_profile()) else { return 0 };
    let path = s(&data, "transcript_path");
    let first = crew_first(&c, path);
    let name = find(&c.name, &first).map(|m| m.as_str().to_string());
    let role = caps(&c.role, &first).map(|m| m[1].to_string());
    let profile_hit = c.profile.iter().find_map(|p| find(p, &first).map(|m| m.as_str().to_string()));
    if name.is_none() && role.is_none() && profile_hit.is_none() { return 0; }
    remember_first(path, &first);
    let who = name.or(profile_hit).or(role).unwrap_or_else(|| "a crew chat".into());
    let cwd = { let c = s(&data, "cwd"); if c.is_empty() { std::env::current_dir().map(|p| p.to_string_lossy().to_string()).unwrap_or_default() } else { c.to_string() } };
    let board = Path::new(&main_folder(&cwd)).join("muster").join("BOARD.md");
    if !board.is_file() { return 0; }
    let or = |v: String, d: &str| if v.is_empty() { d.to_string() } else { v };
    let branch = or(git(&cwd, &["rev-parse", "--abbrev-ref", "HEAD"]), "unknown");
    let sha = or(git(&cwd, &["rev-parse", "--short", "HEAD"]), "unknown");
    let (job, note) = last_facts(path);
    let now = Local::now();
    let slug = re(r"[^a-z0-9]+").replace_all(&who.to_lowercase(), "-").trim_matches('-').to_string();
    let entry = format!(
        "\n### {} | DONE | {} -> Manager | compaction\nStatus: done\nDONE: compacted in place [ID compact-{}-{}]\n\
         What:  this chat is compacting in place (D-039); it carries on, no renewal.\n\
         Where: open job {}; branch {} at {}.\n\
         Why:   the chat reached its size line, 250k tokens (compact window, items 105 and 118).\n\
         How:   next step, from its last message: {}\n\
         Need:  none\n",
        now.format("%Y-%m-%d"), who, slug, now.format("%H%M%S"),
        or(job, "none named in its last messages"), branch, sha, or(note, "read its summary and the board entries addressed to it"));
    if let Ok(mut f) = fs::OpenOptions::new().append(true).open(&board) { let _ = f.write_all(entry.as_bytes()); }
    0
}

/// Python's `%d` of `round(x)`: halves go to the even number.
fn py_round(x: f64) -> i64 { x.round_ties_even() as i64 }

fn local_time(ts: f64, fmt: &str) -> String {
    match Local.timestamp_opt(ts.floor() as i64, 0).single() { Some(t) => t.format(fmt).to_string(), None => "?".into() }
}

/// scripts/usage.py: prints the Usage line from the saved usage file; exit 3 when the week is at or over the limit.
pub fn usage(args: &[String]) -> i32 {
    let (line, code) = usage_line(args);
    if let Some(l) = line { say(&l); }
    code
}

/// The same, without printing: the Usage line (None when the arguments were refused) and the exit code. The rules check asks only for the code.
pub fn usage_line(args: &[String]) -> (Option<String>, i32) {
    let (mut session, mut limit) = (None::<String>, 90.0f64);
    let mut i = 0;
    while i < args.len() {
        let a = args[i].as_str();
        let (key, inline) = match a.split_once('=') { Some((k, v)) => (k, Some(v.to_string())), None => (a, None) };
        let take = |i: &mut usize| -> Option<String> { if inline.is_some() { inline.clone() } else { *i += 1; args.get(*i).cloned() } };
        match key {
            "--session" => session = take(&mut i),
            "--limit-percent" => match take(&mut i).and_then(|v| v.trim().parse::<f64>().ok()) { Some(v) => limit = v, None => { eprintln!("usage.py: error: argument --limit-percent: invalid float value"); return (None, 2); } },
            _ => { eprintln!("usage.py: error: unrecognized arguments: {a}"); return (None, 2); }
        }
        i += 1;
    }
    if session.is_none() && args.iter().any(|a| a == "--session") { eprintln!("usage.py: error: argument --session: expected one argument"); return (None, 2); }
    let base = std::env::var("CLAUDE_CONFIG_DIR").ok().filter(|x| !x.is_empty()).map(PathBuf::from).unwrap_or_else(|| {
        let home = std::env::var("HOME").ok().filter(|x| !x.is_empty()).or_else(|| std::env::var("USERPROFILE").ok()).unwrap_or_default();
        Path::new(&home).join(".claude")
    });
    let dir = base.join("muster-usage");
    let mut files: Vec<PathBuf> = vec![];
    match &session {
        Some(sid) => { let f = dir.join(format!("{sid}.json")); if f.is_file() { files.push(f); } }
        None => if let Ok(rd) = fs::read_dir(&dir) {
            for e in rd.flatten() {
                let n = e.file_name().to_string_lossy().to_string();
                if n.ends_with(".json") && !n.starts_with('.') && e.path().is_file() { files.push(e.path()); }
            }
        },
    }
    if files.is_empty() {
        return (Some("Usage: not readable (Muster's status line is not saving usage here; run /muster:setup or ask the manager to turn it on)".into()), 0);
    }
    let mtime = |p: &PathBuf| fs::metadata(p).and_then(|m| m.modified()).ok();
    let f = files.iter().max_by_key(|p| mtime(p)).unwrap().clone();
    let d: Value = match fs::read_to_string(&f).ok().and_then(|t| serde_json::from_str(&t).ok()) {
        Some(v) => v,
        None => return (Some("Usage: not readable (the saved usage file is damaged)".into()), 0),
    };
    let mut bits: Vec<String> = vec![];
    match d.get("cost_usd").and_then(Value::as_f64) {
        Some(c) => bits.push(format!("session ${c:.2} at list price")),
        None => bits.push("session cost not readable".into()),
    }
    let wk = d.get("week_used_percent").and_then(Value::as_f64);
    match wk {
        None => bits.push("week limit not readable (only claude.ai Pro/Max/Ultra with Muster's status line)".into()),
        Some(w) => {
            let when = match d.get("week_resets_at").and_then(Value::as_f64) { Some(t) if t != 0.0 => local_time(t, "%a %d %b"), _ => "?".into() };
            bits.push(format!("week {}% used (resets {when})", py_round(w)));
        }
    }
    let saved = match d.get("saved_at") { Some(Value::Null) => Local::now().timestamp() as f64, Some(v) => v.as_f64().unwrap_or(0.0), None => 0.0 };
    bits.push(format!("read at {}", local_time(saved, "%H:%M")));
    (Some(format!("Usage: {}", bits.join("; "))), if wk.map(|w| w >= limit).unwrap_or(false) { 3 } else { 0 })
}
