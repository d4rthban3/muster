//! The idle-crew check (port of scripts/idle-check.py): before the manager ends a turn, list the crew's chats that are not running and match them
//! against open items on the owner's list and open orders on the board; the idle card (item 95), the crew sweep (item 96), held workers (item 74).
//! Stop hook, or by hand: `muster-checks idle-check [--project DIR] [--list]`. Reads only; silent (exit 0) outside a manager folder, on any error,
//! or when Claude Code is already continuing because of a stop hook. Same answers as the Python copy, nothing added.
use crate::boardstop::fnv;
use crate::common::*;
use crate::wq::{last_message, py_lines, read, split_before};
use chrono::{Duration, Local};
use fancy_regex::Regex;
use serde_json::Value;
use std::collections::BTreeSet;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};

struct Ctx { idle_seconds: f64, installed: bool, exe: PathBuf, profile: Value }

fn rd(p: &Path) -> String { read(p) }

fn sessions_dir() -> Option<PathBuf> {
    if let Some(d) = std::env::var("MUSTER_SESSIONS_DIR").ok().filter(|d| !d.is_empty()) { return Some(PathBuf::from(d)); }
    let home = std::env::var("HOME").ok().filter(|x| !x.is_empty()).or_else(|| std::env::var("USERPROFILE").ok()).unwrap_or_default();
    let appdata = std::env::var("APPDATA").unwrap_or_default();
    for c in [Path::new(&home).join("Library").join("Application Support").join("Claude").join("claude-code-sessions"),
              Path::new(&appdata).join("Claude").join("claude-code-sessions"),
              Path::new(&home).join(".config").join("Claude").join("claude-code-sessions")] {
        if c.is_dir() { return Some(c); }
    }
    None
}

/// glob.glob(base/*/*/<name or pattern>): files two folders down, hidden names skipped, in name order. `prefix`/`suffix` stand for "local_*.json".
fn glob2(base: &Option<PathBuf>, prefix: &str, suffix: &str) -> Vec<PathBuf> {
    let Some(base) = base else { return vec![] };
    let visible = |e: &fs::DirEntry| !e.file_name().to_string_lossy().starts_with('.');
    let mut out = vec![];
    let mut l1: Vec<_> = fs::read_dir(base).map(|r| r.flatten().filter(|e| visible(e) && e.path().is_dir()).map(|e| e.path()).collect()).unwrap_or_default();
    l1.sort();
    for a in l1 {
        let mut l2: Vec<_> = fs::read_dir(&a).map(|r| r.flatten().filter(|e| visible(e) && e.path().is_dir()).map(|e| e.path()).collect()).unwrap_or_default();
        l2.sort();
        for b in l2 {
            let mut fs_: Vec<_> = fs::read_dir(&b).map(|r| r.flatten().filter(visible).map(|e| e.path()).collect()).unwrap_or_default();
            fs_.sort();
            for f in fs_ {
                let n = f.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default();
                if n.len() >= prefix.len() + suffix.len() && n.starts_with(prefix) && n.ends_with(suffix) { out.push(f); }
            }
        }
    }
    out
}

fn record(base: &Option<PathBuf>, cid: &str) -> Vec<PathBuf> { glob2(base, cid, ".json").into_iter().filter(|p| p.file_name().map(|n| n.to_string_lossy() == format!("{cid}.json")).unwrap_or(false)).collect() }

fn load_json(p: &Path) -> Option<Value> { fs::read_to_string(p).ok().and_then(|t| serde_json::from_str(&t).ok()) }

/// Python's str() of a JSON value, as the app's summary fields are joined.
fn pystr(v: Option<&Value>) -> String {
    match v {
        None => String::new(),
        Some(Value::Null) => "None".into(),
        Some(Value::Bool(b)) => if *b { "True".into() } else { "False".into() },
        Some(Value::String(t)) => t.clone(),
        Some(o) => o.to_string(),
    }
}

fn chars(t: &str, n: usize) -> String { t.chars().take(n).collect() }

impl Ctx {
    fn crew(&self, project: &Path) -> Vec<(String, String)> {
        let text = rd(&project.join("muster").join("CREW.md"));
        let m = caps(&re(r"(?s)## Running now(.*?)(?:\n## |\z)"), &text).and_then(|c| c.get(1).map(|x| x.as_str().to_string()));
        if m.is_none() && truthy(self.profile.get("crew_names")) { return self.profile_crew(); }
        let id = re(r"local_[0-9a-f-]{36}");
        let mut rows = vec![];
        for line in py_lines(&m.unwrap_or_default()) {
            let cells: Vec<&str> = line.trim().trim_matches('|').split('|').map(str::trim).collect();
            if cells.len() >= 2 && cells[0] != "Name" && !cells[0].is_empty() {
                if let Some(i) = find(&id, line) { rows.push((cells[0].to_string(), i.as_str().to_string())); }
            }
        }
        rows
    }

    fn profile_crew(&self) -> Vec<(String, String)> {
        let base = sessions_dir();
        let pats: Vec<Regex> = pstrings(&self.profile, "crew_names").iter().map(|x| re(&format!("^(?:{x})$"))).collect();
        let mgr: Vec<Regex> = pstrings(&self.profile, "manager_names").iter().map(|x| re(x)).collect();
        let mut rows = vec![];
        for f in glob2(&base, "local_", ".json") {
            let Some(d) = load_json(&f) else { continue };
            let t = pystr(d.get("title").filter(|v| truthy(Some(v))));
            let t = if t == "None" { String::new() } else { t };
            if !truthy(d.get("isArchived")) && pats.iter().any(|p| is(p, &t)) && !mgr.iter().any(|m| is(m, &t)) {
                let sid = d.get("sessionId").filter(|v| truthy(Some(v))).map(|v| pystr(Some(v))).unwrap_or_else(|| {
                    let n = f.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default(); n[..n.len().saturating_sub(5)].to_string()
                });
                rows.push((t, sid));
            }
        }
        rows
    }

    fn waiting_chats(&self, rows: &[(String, String)]) -> Vec<(String, String)> {
        let base = sessions_dir();
        let mut out = vec![];
        let mgr = rei("manager");
        for (name, cid) in rows {
            let hits = record(&base, cid);
            let d = match hits.first() { Some(h) => match load_json(h) { Some(d) => d, None => continue }, None => Value::Object(Default::default()) };
            if truthy(d.get("isArchived")) { continue; }
            let ps = d.get("postTurnSummary").filter(|v| truthy(Some(v))).cloned().unwrap_or(Value::Object(Default::default()));
            let txt = ["status_detail", "needs_action"].iter().map(|k| pystr(ps.get(k))).collect::<Vec<_>>().join(" ");
            if (s(&ps, "status_category") == "blocked" || truthy(ps.get("needs_action"))) && is(&mgr, &txt) { out.push((name.clone(), chars(txt.trim(), 100))); }
        }
        out
    }

    fn last_activity(d: &Value) -> f64 { d.get("lastActivityAt").and_then(Value::as_f64).unwrap_or(0.0) / 1000.0 }

    fn idle_chats(&self, rows: &[(String, String)], now: f64) -> Vec<(String, i64)> {
        let base = sessions_dir();
        let mut out = vec![];
        for (name, cid) in rows {
            let hits = record(&base, cid);
            let Some(h) = hits.first() else { continue };
            let Some(d) = load_json(h) else { continue };
            if truthy(d.get("isArchived")) { continue; }
            let last = Self::last_activity(&d);
            if last != 0.0 && now - last >= self.idle_seconds { out.push((name.clone(), (now - last) as i64)); }
        }
        out
    }

    fn running_workers(&self, rows: &[(String, String)], now: f64) -> Vec<String> {
        let base = sessions_dir();
        let mut out = vec![];
        for (name, cid) in rows {
            if name.starts_with("Manager") { continue; }
            let hits = record(&base, cid);
            let d = match hits.first() { Some(h) => match load_json(h) { Some(d) => d, None => continue }, None => Value::Object(Default::default()) };
            let last = Self::last_activity(&d);
            if !hits.is_empty() && !truthy(d.get("isArchived")) && last != 0.0 && now - last < self.idle_seconds { out.push(name.clone()); }
        }
        out
    }

    fn goal_set(&self, project: &Path) -> bool { is(&re(r#"(?m)^Goal \(his words\):\s*"[^"]+""#), &rd(&project.join("muster").join("GOAL.md"))) }

    fn open_items(&self, project: &Path) -> Vec<(String, String)> {
        let mut items = vec![];
        let ol = rd(&project.join("muster").join("OWNERS-LIST.md"));
        let open = caps(&re(r"(?s)(?:^|\n)## Open\n(.*?)(?:\n## |\z)"), &ol).and_then(|c| c.get(1).map(|x| x.as_str().to_string())).unwrap_or_default();
        let (numre, stands, skip) = (re(r"^(\d+)\. "), re(r"(?m)^\s*Stands:\s*(.*)$"), rei(r"^(done|waiting)"));
        for blk in split_before(&open, r"\d+\. ") {
            let num = caps(&numre, blk.trim());
            let st = caps(&stands, &blk);
            if let (Some(n), Some(st)) = (num, st) {
                let g = st.get(1).map(|m| m.as_str()).unwrap_or("");
                if !is(&skip, g) { items.push((format!("item {}", &n[1]), g.to_string())); }
            }
        }
        let board = rd(&project.join("muster").join("BOARD.md"));
        let (order, status) = (re(r"^### \S+ \| ORDER \| .*? -> ([^|]+?) \| (.*)"), rei(r"(?m)^Status:\s*open"));
        for blk in split_before(&board, "### ") {
            if let Some(h) = caps(&order, &blk) { if is(&status, &blk) { items.push((format!("order {}", h[2].trim()), format!("to {}", h[1].trim()))); } }
        }
        items
    }

    fn findings(&self, project: &Path, now: f64) -> Vec<(String, i64, Vec<(String, String)>)> {
        let items = self.open_items(project);
        self.idle_chats(&self.crew(project), now).into_iter().map(|(n, secs)| {
            let f = items.iter().filter(|(_, t)| t.to_lowercase().contains(&n.to_lowercase())).cloned().collect();
            (n, secs, f)
        }).collect()
    }

    fn board_entries(&self, project: &Path) -> Vec<(String, String, String)> {
        let mut paths = vec![project.join("muster").join("BOARD.md")];
        if let Some(b) = self.profile.get("board").filter(|v| truthy(Some(v))).and_then(Value::as_str) { paths.push(project.join(b)); }
        let line = re(r"^(?:###\s+)?(\d{4}-\d{2}-\d{2})\S*\s*\|\s*[^|]+\|\s*(.*?)\s*->\s*(.*?)\s*\|");
        let mut out = vec![];
        for p in paths {
            for ln in py_lines(&rd(&p)) {
                if let Some(m) = caps(&line, ln.trim()) { out.push((m[1].to_string(), m[2].to_string(), m[3].to_string())); }
            }
        }
        out
    }

    fn quiet_members(&self, project: &Path) -> Vec<String> {
        let cutoff = (Local::now().date_naive() - Duration::days(1)).format("%Y-%m-%d").to_string();
        let recent: Vec<String> = self.board_entries(project).into_iter().filter(|(d, _, _)| *d >= cutoff).map(|(_, f, t)| format!("{f} {t}").to_lowercase()).collect();
        let base = sessions_dir();
        let mut arch = BTreeSet::new();
        for f in glob2(&base, "local_", ".json") {
            if let Some(d) = load_json(&f) { if truthy(d.get("isArchived")) { arch.insert(pystr(d.get("title").filter(|v| truthy(Some(v))))); } }
        }
        let mut mpats = pstrings(&self.profile, "manager_names");
        if !truthy(self.profile.get("manager_names")) || mpats.is_empty() { mpats = vec![DEFAULT_MANAGER.to_string()]; }
        let mgr: Vec<Regex> = mpats.iter().map(|x| re(x)).collect();
        let mut out = vec![];
        for (name, _) in self.crew(project) {
            if arch.contains(&name) || mgr.iter().any(|m| is(m, &name)) { continue; }
            if !recent.iter().any(|r| r.contains(&name.to_lowercase())) { out.push(name); }
        }
        out
    }

    fn board_holds(&self, project: &Path) -> Vec<(String, String)> {
        let hold = rei(r"\baction:?\s*hold\b");
        let basis = rei(r"\b(item\s*\d+|D-\d+|decision\s*\d+|owner|founder|his\s+(?:word|words|choice|yes|go|pick|call|decision|click)|he\s+(?:said|asked|chose|picked|told))");
        let mut out = vec![];
        let board = self.profile.get("board").filter(|v| truthy(Some(v))).and_then(Value::as_str);
        if s(&self.profile, "board_style") == "lines" && board.is_some() {
            let text = rd(&project.join(board.unwrap()));
            let all = py_lines(&text);
            let line = re(r"^\S+\s*\|\s*[A-Za-z]+\s*\|\s*(.*?)\s*->\s*(.*?)\s*\|\s*(.*)$");
            let mgr = re(r"\bManager_");
            for ln in &all[all.len().saturating_sub(15)..] {
                if let Some(m) = caps(&line, ln.trim()) {
                    if is(&mgr, &m[1]) && is(&hold, &m[3]) && !is(&basis, &m[3]) { out.push((m[2].to_string(), chars(&m[3], 80))); }
                }
            }
            return out;
        }
        let (head, status) = (re(r"^### \S+ \| \w+ \| (Manager_[^|]*?) -> ([^|]+?) \|"), rei(r"(?m)^Status:\s*open"));
        for blk in split_before(&rd(&project.join("muster").join("BOARD.md")), "### ") {
            if let Some(h) = caps(&head, &blk) {
                if is(&status, &blk) && is(&hold, &blk) && !is(&basis, &blk) { out.push((h[2].to_string(), chars(py_lines(&blk).first().copied().unwrap_or(""), 80))); }
            }
        }
        out
    }

    fn is_manager_chat(&self, data: &Value) -> bool {
        let mut pats = pstrings(&self.profile, "manager_names");
        if pats.is_empty() { pats = vec![DEFAULT_MANAGER.to_string()]; }
        let title = chat_title(s(data, "transcript_path"));
        !title.is_empty() && pats.iter().any(|p| is(&re(p), &title))
    }
}

const DEFAULT_MANAGER: &str = r"\bManager_[^_\s]*?(?:_\d{3})?\b";

/// What a reply to the owner lacks when two or more workers are idle and still idle; "" when it is the card (item 95).
fn card_problem(raw: &str, names: &[String]) -> String {
    let lines = py_lines(raw);
    let (since, why, unblock) = (rei(r"\bsince\b"), rei(r"\bwhy\b"), rei(r"\bunblock"));
    let lacking: Vec<&String> = names.iter().filter(|n| !lines.iter().any(|l| l.to_lowercase().contains(&n.to_lowercase()) && is(&since, l) && is(&why, l) && is(&unblock, l))).collect();
    let letters = re(r"(?m)^\s*\*{2,3}[A-D]\.\*{2,3}").find_iter(raw).flatten().count();
    let q_ok = letters >= 2 || (raw.contains('?') && letters >= 1);
    let mut out = vec![];
    if !lacking.is_empty() { out.push(format!("no line with 'since', 'why' and 'unblocked by' for: {}", lacking.iter().map(|s| s.as_str()).collect::<Vec<_>>().join(", "))); }
    if !q_ok { out.push("no lettered question (two or more ***A.*** lines, or one with a '?') for the choice that unblocks the most".to_string()); }
    out.join("; ")
}

fn told_file(tpath: &str, project: &str) -> PathBuf {
    let d = std::env::var("MUSTER_STATE_DIR").ok().filter(|d| !d.is_empty()).map(PathBuf::from).unwrap_or_else(std::env::temp_dir);
    d.join(format!("muster-told-{:016x}.txt", fnv(if tpath.is_empty() { project } else { tpath })))
}

fn now_secs() -> f64 { std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0) }

fn minutes(secs: i64) -> i64 { std::cmp::max(1, secs.div_euclid(60)) }

fn finding_text(f: &[(String, String)]) -> String { f.iter().map(|(k, t)| format!("{k} ({t})")).collect::<Vec<_>>().join("; ") }

pub fn run(args: &[String]) -> i32 {
    let idle_seconds = match std::env::var("MUSTER_IDLE_SECONDS").ok().filter(|v| !v.is_empty()) {
        Some(v) => match v.trim().parse::<i64>() { Ok(n) => n as f64, Err(_) => return 1 }, // Python's int() of text that is not a number ends the script
        None => 120.0,
    };
    let here = here_dir();
    let cx = Ctx { idle_seconds, installed: installed(), exe: here.clone(), profile: load_profile() };
    let mut project = std::env::current_dir().unwrap_or_default();
    if let Some(i) = args.iter().position(|a| a == "--project") {
        match args.get(i + 1) { Some(p) => project = PathBuf::from(p), None => return 1 }
    } else if cx.installed {
        project = cx.exe.parent().map(Path::to_path_buf).unwrap_or_default();
    }
    if !cx.installed && !project.join("muster").join("BOARD.md").is_file() { return 0; }
    if args.iter().any(|a| a == "--list") {
        for (n, secs, f) in cx.findings(&project, now_secs()) {
            say(&format!("{n} idle {secs}s: {}", if f.is_empty() { "no open item".to_string() } else { finding_text(&f) }));
        }
        for (n, why) in cx.waiting_chats(&cx.crew(&project)) { say(&format!("{n} waits on the manager: {why}")); }
        for (to, t) in cx.board_holds(&project) { say(&format!("hold with no owner basis, to {to}: {t}")); }
        return 0;
    }
    let mut raw = vec![];
    let _ = std::io::stdin().read_to_end(&mut raw);
    let text = String::from_utf8_lossy(&raw).to_string();
    let data: Value = match serde_json::from_str(if text.is_empty() { "{}" } else { &text }) { Ok(v) => v, Err(_) => return 0 };
    if !data.is_object() { return 1; } // Python's .get on a list or a number ends the script with an error
    if truthy(data.get("stop_hook_active")) { return 0; }
    if cx.installed && !cx.is_manager_chat(&data) { return 0; }
    let msg = last_message(&data).to_lowercase();
    if msg.trim().is_empty() && peer_started(s(&data, "transcript_path")) { return 0; } // item 97
    let project_s = project.to_string_lossy().to_string();
    let tfile = told_file(s(&data, "transcript_path"), &project_s);
    let mut told: BTreeSet<String> = fs::read_to_string(&tfile).map(|t| t.split_whitespace().map(String::from).collect()).unwrap_or_default();
    let told0 = told.clone();
    let fresh = |told: &mut BTreeSet<String>, kind: &str, who: &str, what: &str, key: &str| -> bool {
        let fp = format!("{:016x}", fnv(&format!("idle|{kind}|{who}|{what}")));
        if msg.contains(&key.to_lowercase()) { told.insert(fp); return false; }
        if told.contains(&fp) { return false; }
        told.insert(fp);
        true
    };
    let missing: Vec<_> = cx.findings(&project, now_secs()).into_iter().filter(|f| !f.2.is_empty() && fresh(&mut told, "item", &f.0, &finding_text(&f.2), &f.0)).collect();
    let waiting: Vec<_> = cx.waiting_chats(&cx.crew(&project)).into_iter().filter(|w| fresh(&mut told, "wait", &w.0, &w.1, &w.0)).collect();
    let holds: Vec<_> = cx.board_holds(&project).into_iter().filter(|h| fresh(&mut told, "hold", &h.0, &h.1, &h.0)).collect();
    let still: Vec<(String, i64)> = cx.findings(&project, now_secs()).into_iter().filter(|f| f.2.is_empty()).map(|f| (f.0, f.1)).collect();
    let mut card = String::new();
    let stretch = format!("{:016x}", fnv("idle|card|stretch"));
    if still.len() < 2 {
        told.remove(&stretch);
    } else if missing.is_empty() && !(cx.goal_set(&project) && !cx.running_workers(&cx.crew(&project), now_secs()).is_empty()) && !told.contains(&stretch) {
        told.insert(stretch);
        card = card_problem(&last_message(&data), &still.iter().map(|(n, _)| n.clone()).collect::<Vec<_>>());
    }
    let day = Local::now().date_naive().format("%Y-%m-%d").to_string();
    let mut sweep: Vec<String> = vec![];
    if missing.is_empty() && std::env::var("MUSTER_NO_SWEEP").map(|v| v.is_empty()).unwrap_or(true) {
        for n in cx.quiet_members(&project) {
            if fresh(&mut told, "quiet", &n, &day, &n) { sweep.push(format!("{n} has had no order and no report on the board for a day")); }
        }
    }
    if told != told0 {
        let body = told.iter().cloned().collect::<Vec<_>>().join("\n") + "\n";
        let _ = fs::write(&tfile, body);
    }
    let reply = |r: String| say(&py_obj(&[("decision", "block".into()), ("reason", r)]));
    if !sweep.is_empty() && missing.is_empty() && waiting.is_empty() && holds.is_empty() && card.is_empty() {
        reply(format!("Crew sweep (item 96): {}. Give each quiet member its next order or find out why it has none; name each in your reply.{NOREPEAT}", sweep.join(" | ")));
        return 0;
    }
    if missing.is_empty() && waiting.is_empty() && holds.is_empty() {
        if !card.is_empty() {
            let who = still.iter().map(|(n, sec)| format!("{n} idle {} min", minutes(*sec))).collect::<Vec<_>>().join("; ");
            reply(format!("Two or more workers are idle with nothing to order and the owner has no clear report (item 95). Send him ONE card: a bold title, one bullet \
line per worker ({who}), each saying 'since <when>', 'why: <reason>' and 'unblocked by: <what>', then the one lettered question \
(***A.*** ...) that unblocks the most. Missing: {card}.{NOREPEAT}"));
        }
        return 0;
    }
    let mut lines: Vec<String> = missing.iter().map(|(n, secs, f)| format!("{n} has been idle {} minutes and holds an open item: {}", minutes(*secs), finding_text(f))).collect();
    lines.extend(waiting.iter().map(|(n, d)| format!("{n} says it waits on the manager ({d})")));
    lines.extend(holds.iter().map(|(to, t)| format!("your board line holds {to} ({t}) but names no decision or item of his: a manager never holds a worker for a \
measurement or convenience, and no order of yours outranks his word; release it or cite his words")));
    reply(format!("Do not end this turn silently: {}. Message each one (give it the next order quoting his words, answer what it waits on, or ask why it is idle), \
name it in your reply, or if nothing fits say \"The crew is idle\" with the choices as buttons.{NOREPEAT}", lines.join(" | ")));
    0
}
