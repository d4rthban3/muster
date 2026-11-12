//! Muster's rules as code (port of hooks/rules-check.py). PreToolUse: a message between chats must be a data record (or, where a
//! project's profile says "message_form": "text", the older six-line report), no social replies, no ID sent twice, only the manager
//! writes the owner's files, nothing under muster/ is saved. Stop: the manager's reply and every worker's card.
use crate::common::*;
use crate::talk::{crew_re, ROLE};
use serde_json::Value;
use std::path::{Component, Path, PathBuf};
use std::process::Command;

const FIRST: &str = r"(DONE|READY|PASS|FAIL|OWNER CALL|STUCK|NEED)";

struct Ctx { profile: Value, crew: fancy_regex::Regex, text_form: bool, report_id: bool, report_usage: bool, orders_free: bool, recorder: String, protected: fancy_regex::Regex, profile_protected: Option<fancy_regex::Regex> }

fn ctx() -> Ctx {
    let profile = load_profile();
    let form = std::env::var("MUSTER_MESSAGE_FORM").ok().filter(|x| !x.is_empty()).or_else(|| profile.get("message_form").and_then(Value::as_str).map(String::from)).unwrap_or_else(|| "records".into());
    let rb = |k: &str| profile.get("report").and_then(|r| r.get(k)).and_then(Value::as_bool).unwrap_or(true);
    let mut prot = String::from(r"/muster/(OWNERS-LIST\.md|DECISIONS-LOG\.md|CREW\.md|CLAUDE\.md|rules/|RULES-PAGE\.md|REPORT\.md)");
    let pp = pstrings(&profile, "protected");
    let profile_protected = if pp.is_empty() { None } else { Some(re(&pp.iter().map(|x| format!("(?:{x})")).collect::<Vec<_>>().join("|"))) };
    for x in &pp { prot.push_str(&format!("|(?:{x})")); }
    Ctx {
        crew: crew_re(&profile), text_form: form == "text", report_id: rb("require_id"), report_usage: rb("require_usage"),
        orders_free: profile.get("orders").and_then(Value::as_str) == Some("free"),
        recorder: profile.get("record_choice").and_then(Value::as_str).unwrap_or("record-choice.py").to_string(),
        protected: re(&prot), profile_protected, profile,
    }
}

fn manager_names(c: &Ctx) -> Vec<fancy_regex::Regex> { pstrings(&c.profile, "manager_names").iter().map(|x| re(&format!("^(?:{x})$"))).collect() }

fn token_is_manager(c: &Ctx, tok: &str) -> bool {
    if is(&re(r"^agents[/\\]"), tok) { return is(&re(r"agents[/\\]manager\.md$"), tok); }
    is(&re(r"^Manager_[^_\n]*_\d{3}$"), tok) || manager_names(c).iter().any(|r| is(r, tok))
}

fn is_manager(c: &Ctx, first: &str) -> bool {
    let mut best: Option<(usize, String)> = None;
    for lead in [r"\bJob:\s*[*`]{0,2}", r"\b(?:you are|i am|i'm)\s+(?:the\s+)?[*`]{0,2}"] {
        let l = rei(lead);
        let mut at = 0;
        while let Some(m) = l.find_from_pos(first, at).ok().flatten() {
            let tail = &first[m.end()..];
            let anchored = re(&format!("^(?:{})", c.crew.as_str()));
            if let Some(cm) = find(&anchored, tail) {
                if best.as_ref().map(|b| m.start() < b.0).unwrap_or(true) { best = Some((m.start(), cm.as_str().to_string())); }
                break;
            }
            at = m.end().max(m.start() + 1);
            if at >= first.len() { break; }
        }
    }
    if let Some((_, tok)) = best { return token_is_manager(c, &tok); }
    if let Some(m) = find(&re(r"agents[/\\](?:manager|builder|designer|inspector|design-inspector|sketchpad|ai-socket|agent-teacher)\.md"), first) { return token_is_manager(c, m.as_str()); }
    is(&rei(r"\bJob:[^\n]*(go-between|record keeper)"), first)
}

// ---- the older text shapes (kept for projects whose profile says "message_form": "text", and for the carried-over tests) ----
fn report_problem(c: &Ctx, text: &str) -> Option<String> {
    let mut lines: Vec<&str> = text.trim().lines().filter(|l| !l.trim().is_empty()).collect();
    let mut usage = None;
    if lines.len() == 7 && lines[6].starts_with("Usage:") { usage = lines.pop(); }
    if lines.len() != 6 {
        return Some(format!("expected 6 lines{}, found {}", if c.report_usage { " (and a Usage line on DONE and READY)" } else { "" }, lines.len()));
    }
    let first_re = if c.report_id { format!(r"^{FIRST}: .+ \[ID [^\]]+-\d+\]$") } else { format!(r"^{FIRST}: .+$") };
    let Some(m) = caps(&re(&first_re), lines[0]) else {
        return Some(format!("first line must be 'FIRST WORD: job name{}'", if c.report_id { " [ID role-job-number]" } else { "" }));
    };
    for (line, label) in lines[1..].iter().zip(["What:", "Where:", "Why:", "How:", "Need:"]) {
        if !line.starts_with(label) { return Some(format!("expected a line starting {label}")); }
    }
    if !lines[2].contains("touches:") { return Some("Where line lacks 'touches:'".into()); }
    let word = m[1].to_string();
    if c.report_usage && (word == "DONE" || word == "READY") && usage.is_none() { return Some("a DONE or READY needs a Usage line (scripts/usage.py prints it)".into()); }
    if word == "READY" && !is(&re(r"\d+\s*(/|of)\s*\d+|\d+ passed"), lines[4]) { return Some("READY's How line shows no test count".into()); }
    None
}

fn order_problem(text: &str) -> Option<String> {
    let lab = rei(r"^\s*(To|Job|Owner'?s words|Owns|Out|Done)\s*:\s*(.*)$");
    let mut labels: Vec<(String, String)> = vec![];
    for l in text.lines() {
        if let Some(m) = caps(&lab, l) {
            let k = m[1].to_lowercase().replace("owners", "owner's");
            if !labels.iter().any(|(x, _)| *x == k) { labels.push((k, m[2].to_string())); }
        }
    }
    for need in ["to", "job", "owner's words", "owns", "out", "done"] {
        match labels.iter().find(|(k, _)| k == need) {
            Some((_, v)) if !v.trim().is_empty() => {}
            _ => { let mut cap = need.to_string(); cap[..1].make_ascii_uppercase(); return Some(format!("an order needs a filled '{cap}:' line")); }
        }
    }
    let ow = &labels.iter().find(|(k, _)| k == "owner's words").unwrap().1;
    if !is(&re("[\"\u{201c}][^\"\u{201d}]{3,}[\"\u{201d}]"), ow) { return Some("the Owner's words line must quote his words in quotation marks".into()); }
    None
}

// ---- helpers ----
fn main_folder(cwd: &str) -> String {
    let mut cmd = Command::new("git");
    cmd.args(["rev-parse", "--git-common-dir"]);
    if !cwd.is_empty() { cmd.current_dir(cwd); }
    if let Ok(o) = cmd.output() {
        let p = String::from_utf8_lossy(&o.stdout).trim().to_string();
        if !p.is_empty() {
            let full = normalise(&Path::new(if cwd.is_empty() { "." } else { cwd }).join(&p));
            return if full.file_name().map(|n| n == ".git").unwrap_or(false) { full.parent().map(|x| x.to_string_lossy().to_string()).unwrap_or_default() } else { cwd.to_string() };
        }
    }
    cwd.to_string()
}
pub fn normalise(p: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for c in p.components() {
        match c { Component::ParentDir => { out.pop(); } Component::CurDir => {} o => out.push(o.as_os_str()) }
    }
    out
}
fn recipient_is_manager(to: &str, root: &str) -> bool {
    if is(&re(r"\bManager"), to) { return true; }
    if let Ok(t) = std::fs::read_to_string(Path::new(root).join("muster").join("CREW.md")) {
        for l in t.lines() { if !to.is_empty() && l.contains(to) && l.trim_start_matches(|c| c == '|' || c == ' ').starts_with("Manager") { return true; } }
    }
    false
}
/// The weekly goal (muster/GOAL.md): an ORDER whose job is not on its set list waits. No goal, or no set list, enforces nothing.
fn goal_problem(root: &str, job: &str) -> Option<String> {
    let text = std::fs::read_to_string(Path::new(root).join("muster").join("GOAL.md")).ok()?;
    let mut jobs: Vec<String> = vec![];
    let mut in_list = false;
    for l in text.lines() {
        if l.starts_with("Set list") { in_list = true; continue; }
        if in_list { if let Some(j) = l.strip_prefix("- ") { if !j.trim().is_empty() { jobs.push(j.trim().to_string()); } } else if !l.trim().is_empty() || !jobs.is_empty() { in_list = false; } }
    }
    if jobs.is_empty() || jobs.iter().any(|j| j == job) { return None; }
    let words = caps(&re(r#"(?m)^Goal \(his words\):\s*"(.*)"\s*$"#), &text).map(|m| m[1].to_string()).unwrap_or_default();
    let done = caps(&re(r"(?m)^Done when:\s*(.*)$"), &text).map(|m| m[1].trim().to_string()).unwrap_or_else(|| "not said".into());
    Some(format!("the owner's goal for the team is \"{words}\" (done when: {done}) and the job {job} is not on its set list, so it waits. He can change the goal any time: ask him, then run scripts/goal.py set"))
}

fn usage_at_limit(root: &str) -> bool {
    let cands = [exe_dir().join("..").join("scripts").join("usage.py"), Path::new(root).join(".muster-checks").join("usage.py")];
    for cand in cands {
        if cand.is_file() {
            for py in ["python3", "python"] {
                if let Ok(st) = Command::new(py).arg(&cand).output() { return st.status.code() == Some(3); }
            }
            return false;
        }
    }
    false
}

fn segments(cmd: &str) -> Vec<&str> { cmd.split(|c| c == ';' || c == '&' || c == '|' || c == '\n').collect() }

fn shell_words(t: &str) -> Vec<String> {
    let (mut out, mut cur, mut q, mut any, mut esc) = (vec![], String::new(), None::<char>, false, false);
    for ch in t.chars() {
        if esc { cur.push(ch); esc = false; continue; }
        match (q, ch) {
            (None, '\\') => { esc = true; any = true; }
            (Some('\''), '\'') | (Some('"'), '"') => q = None,
            (Some('"'), '\\') => esc = true,
            (Some(_), c) => cur.push(c),
            (None, '\'') | (None, '"') => { q = Some(ch); any = true; }
            (None, c) if c.is_whitespace() => { if any || !cur.is_empty() { out.push(std::mem::take(&mut cur)); any = false; } }
            (None, c) => { cur.push(c); any = true; }
        }
    }
    if any || !cur.is_empty() { out.push(cur); }
    out
}

fn shell_write_targets(cmd: &str) -> Vec<String> {
    let redirect = re(r#"(?<![<>&0-9])\d?>>?\s*("[^"]+"|'[^']+'|[^\s;&|<>]+)"#);
    let strip = re(r#"\d?>>?\s*("[^"]+"|'[^']+'|[^\s;&|<>]+)"#);
    let mut out: Vec<String> = vec![];
    for seg in segments(cmd) {
        for m in redirect.captures_iter(seg).filter_map(Result::ok) { out.push(m[1].trim_matches(|c| c == '"' || c == '\'').to_string()); }
        let words = shell_words(&sub(&strip, seg, " "));
        if words.is_empty() { continue; }
        let mut i = 0;
        while i < words.len() && (["sudo", "command", "env"].contains(&words[i].as_str()) || words[i].split('/').next().unwrap_or("").contains('=')) { i += 1; }
        if i >= words.len() { continue; }
        let prog = Path::new(&words[i]).file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default();
        let args = &words[i + 1..];
        let files: Vec<String> = args.iter().filter(|w| !w.starts_with('-')).cloned().collect();
        match prog.as_str() {
            "tee" => out.extend(files),
            "sed" if args.iter().any(|w| is(&re(r"^-[A-Za-z]*i"), w) || w.starts_with("--in-place")) => { if files.len() > 1 { out.extend(files[1..].iter().cloned()); } }
            "cp" | "mv" | "install" | "rsync" | "ln" if !files.is_empty() => out.push(files[files.len() - 1].clone()),
            "dd" => out.extend(args.iter().filter(|w| w.starts_with("of=")).map(|w| w[3..].to_string())),
            _ => {}
        }
    }
    out
}

fn expand_home(t: &str) -> String {
    if let Some(rest) = t.strip_prefix('~') { if let Ok(h) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) { return format!("{h}{rest}"); } }
    t.to_string()
}

// ---- PreToolUse ----
fn social_re() -> fancy_regex::Regex {
    let soc = r"(?:noted|received|thanks|thank you|got it|ok(?:ay)?|ack(?:nowledged)?|will do|and)";
    rei(&format!(r"^\s*{soc}\b(?:[\s.,!;&-]+{soc}\b)*[\s.,!;&-]*$"))
}

fn pretool(c: &Ctx, data: &Value, manager: bool) {
    let tool = s(data, "tool_name");
    let empty = Value::Object(Default::default());
    let inp = data.get("tool_input").unwrap_or(&empty);
    let root = main_folder(s(data, "cwd"));
    if tool == "SendMessage" { return send_message(c, data, inp, &root); }
    if tool == "Agent" || tool == "Task" { return helper_problem(inp, manager); }
    if matches!(tool, "Write" | "Edit" | "NotebookEdit") && !manager {
        let p = s(inp, "file_path").replace('\\', "/");
        if is(&c.protected, &p) {
            let base = p.rsplit('/').next().unwrap_or("");
            return deny(&format!("only the manager changes the owner's list, decisions, crew list, rules pages and muster/CLAUDE.md ({base})"));
        }
    }
    if tool == "Bash" {
        let cmd = s(inp, "command");
        let git = re(r"^\s*git\s+(?:-C\s+\S+\s+)?(add|commit)\b(.*)");
        let quoted = re(r#"("[^"]*"|'[^']*')"#);
        let musterpath = re(r"(?<![\w/.-])(muster/?|muster/[^\s]*\.\w+|muster/(rules|handovers|superseded|x-post)/\S*)(?=\s|$)");
        for seg in segments(cmd) {
            let Some(mg) = caps(&git, seg) else { continue };
            let args = sub(&quoted, &mg[2], " ");
            if is(&musterpath, &args) { return deny("nothing under muster/ is ever saved or committed"); }
        }
        if !manager {
            if let Some(pp) = &c.profile_protected {
                let base = { let cw = s(data, "cwd"); if cw.is_empty() { std::env::current_dir().unwrap_or_default() } else { cw.into() } };
                for tgt in shell_write_targets(cmd) {
                    let full = normalise(&base.join(expand_home(&tgt))).to_string_lossy().replace('\\', "/");
                    if is(pp, &full) { return deny(&format!("only the manager changes this project's manager-only files ({})", full.rsplit('/').next().unwrap_or(""))); }
                }
            }
            let redirect = re(r"(>|>>|tee\s+|sed\s+-i\S*\s+(''\s+)?\S*\s*)\s*\S*muster/(OWNERS-LIST|DECISIONS-LOG|CREW|CLAUDE|RULES-PAGE|REPORT)\.md");
            if is(&redirect, cmd) { return deny("only the manager changes the owner's list, decisions, crew list and muster/CLAUDE.md"); }
        }
    }
}

/// Helpers (item 36): a subagent is a side job. It may not stand in for a worker (only the manager's fresh checker, from the inspector
/// definition, is allowed), and its brief may not ask it to ship, push, message or ask the owner. Lines that say "never/not" are fine.
fn helper_problem(inp: &Value, manager: bool) {
    let kind = s(inp, "subagent_type").trim().trim_start_matches("muster:").to_lowercase();
    let roles = ["manager", "builder", "designer", "inspector", "design-inspector", "sketchpad", "ai-socket", "agent-teacher"];
    if roles.contains(&kind.as_str()) && !(manager && kind == "inspector") {
        return deny(&format!("a helper never stands in for a worker or the Inspector chat ({kind}); use a plain helper for the side job (only the manager's fresh checker for a small piece uses the inspector definition)"));
    }
    let ask = re(r"(?i)(scripts[/\\]ship\.sh|\bgit\s+push\b|\bSendMessage\b|\bAskUserQuestion\b)");
    let neg = rei(r"\b(never|not|no|without|don't|do not)\b|n't\b");
    for l in s(inp, "prompt").lines() {
        if is(&ask, l) && !is(&neg, l) {
            return deny("a helper never ships, pushes, messages other chats or talks to the owner; take that out of its brief and do it yourself");
        }
    }
}

fn send_message(c: &Ctx, data: &Value, inp: &Value, root: &str) {
    let msg = s(inp, "message");
    if is(&social_re(), msg) { return deny("no 'noted' or 'thanks' replies; send a message only when someone must act"); }
    let sent = || all_sent_text(s(data, "transcript_path"));
    if !c.text_form {
        // a data record: one JSON object, fixed keys, set values, no sentences
        let rec0: Value = serde_json::from_str(msg.trim()).unwrap_or(Value::Null);
        let things = project_things(s(data, "cwd"), s(&rec0, "sha")); // the worker's own copy at that sha, not the main folder
        if let Err(why) = crate::record::validate(msg, &things) { return deny(&format!("a message between chats is a data record (JSON with fixed keys and set values), never sentences, and this one is wrong: {why}")); }
        let rec: Value = serde_json::from_str(msg.trim()).unwrap_or(Value::Null);
        let (id, kind) = (s(&rec, "id"), s(&rec, "kind"));
        if sent().iter().any(|t| serde_json::from_str::<Value>(t.trim()).map(|r| s(&r, "id") == id).unwrap_or(false)) { return deny(&format!("this record's id {id} was already sent; a repeat is dropped")); }
        if (kind == "PASS" || kind == "FAIL") && (recipient_is_manager(s(inp, "to"), root) || s(&rec, "to").starts_with("manager")) {
            return deny("a PASS or FAIL copy for the manager goes on the board only, not as a message");
        }
        if kind == "ORDER" { if let Some(why) = goal_problem(root, s(&rec, "job")) { return deny(&why); } }
        if kind == "ORDER" && usage_at_limit(root) { return deny("the week is at 90% or more (scripts/usage.py exits 3): start no new order; finish and park what is running"); }
        return;
    }
    if c.orders_free && !is(&re(&format!(r"^\s*{FIRST}\s*:")), msg) { return; }
    let (bad_report, bad_order) = (report_problem(c, msg), order_problem(msg));
    if let (Some(br), Some(bo)) = (&bad_report, &bad_order) {
        let first = msg.trim().lines().next().unwrap_or("");
        if is(&rei(r"^\s*(To|Job)\s*:"), first) || is(&rei(r"(?m)^\s*Job\s*:"), msg) {
            return deny(&format!("a message between chats is a six-line report or an order, and this order is wrong: {bo}"));
        }
        return deny(&format!("a message between chats is a six-line report or an order, and this report is wrong: {br}"));
    }
    if let Some(m) = caps(&re(&format!(r"^\s*{FIRST}: .+ \[ID ([^\]]+)\]")), msg) {
        let idtag = format!("[ID {}]", &m[2]);
        if sent().iter().any(|t| t.contains(&idtag)) { return deny(&format!("this report's ID [{}] was already sent; a repeat is dropped", &m[2])); }
        if is(&re(r"^\s*(PASS|FAIL)\b"), msg) && recipient_is_manager(s(inp, "to"), root) { return deny("a PASS or FAIL copy for the manager goes on the board only, not as a message"); }
    }
    if bad_order.is_none() && usage_at_limit(root) { return deny("the week is at 90% or more (scripts/usage.py exits 3): start no new order; finish and park what is running"); }
}

// ---- Stop ----
/// Where the choice recorder really is: the project's own scripts folder, else this plugin's, else just its name.
fn recorder_path(root: &str, name: &str) -> String {
    for cand in [Path::new(root).join("scripts").join(name), exe_dir().join("..").join("scripts").join(name)] {
        if cand.is_file() { return normalise(&std::fs::canonicalize(&cand).unwrap_or(cand)).to_string_lossy().to_string(); }
    }
    name.to_string()
}

fn manager_reply_ok(t: &str) -> bool {
    if is(&rei(r"\bThe crew is idle\b"), t) { return true; }
    if is(&rei(r"(?s)\bis waiting for you\b.*\btype in\b"), t) { return true; }
    if is(&rei(r"\b(I need your yes|needs? your yes|your yes (is needed|to))\b"), t) { return true; }
    let has_q = t.contains('?');
    let has_choices = is(&re(r"(?m)^\*\*[A-D]\.\*\*"), t) || is(&rei(r"\bbuttons?\b"), t);
    has_q && has_choices
}

fn stop(c: &Ctx, data: &Value, manager: bool) {
    let text = s(data, "last_assistant_message");
    if text.is_empty() || data.get("stop_hook_active").and_then(Value::as_bool).unwrap_or(false) || bounced_this_turn(s(data, "transcript_path")) { return; }
    let tpath = s(data, "transcript_path");
    let uses = turn_blocks(tpath);
    let asked_at = uses.iter().rposition(|u| s(u, "name") == "AskUserQuestion");
    if manager {
        if let Some(idx) = asked_at.filter(|&i| !card_skipped(tpath, s(&uses[i], "id"))) {
            let recorded = uses[idx + 1..].iter().any(|u| s(u, "name") == "Bash" && u.get("input").map(|i| s(i, "command").contains(&c.recorder)).unwrap_or(false));
            if !recorded { block(&format!("a choice card was answered but not recorded: run {} with his exact answer (or --no-pick if he skipped the card or typed his own words) under its list item before ending the turn", recorder_path(&main_folder(s(data, "cwd")), &c.recorder))); }
            return;
        }
        if !manager_reply_ok(text) && !owner_asked(tpath) {
            block("to the owner the manager says only a question with its choices as buttons, a yes he must give, '<worker> is waiting for you: type in <chat>', or 'The crew is idle'. Rewrite the reply as one of those, or put the news on the board");
        }
        return;
    }
    if asked_at.is_some() || is(&re(r"^\s*Messages paused"), text) { return; }
    let body = text.trim();
    let bullet = re(r"^\s*[-*•] \S");
    let nb = body.lines().filter(|l| is(&bullet, l)).count();
    let title_ok = body.lines().next().map(|l| is(&re(r"^\s*\*\*[^*\n]+\s[·.]\s[^*\n]+\*\*\s*$"), l)).unwrap_or(false);
    if !title_ok || !(2..=3).contains(&nb) {
        block("your end-of-turn reply is a card: a bold title line 'WORD · job', then two or three '- ' bullets (what, the result with real numbers, what is left or what you need)");
    }
}

pub fn run() -> i32 {
    let Some(data) = read_stdin() else { return 0 };
    if stood_down(&data, "rules-check.py") { return 0; }
    let c = ctx();
    let first = first_message(s(&data, "transcript_path"));
    if !is(&c.crew, &first) && std::env::var("MUSTER_ASSUME_CREW").ok().as_deref() != Some("1") { return 0; }
    let manager = is_manager(&c, &first) || std::env::var("MUSTER_ASSUME_MANAGER").ok().as_deref() == Some("1");
    match s(&data, "hook_event_name") { "PreToolUse" => pretool(&c, &data, manager), "Stop" => stop(&c, &data, manager), _ => {} }
    0
}
#[allow(dead_code)]
fn _unused() { let _ = ROLE; }
