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
    is(&re(r"^Manager_[^_\n]*?(?:_\d{3})?$"), tok) || manager_names(c).iter().any(|r| is(r, tok))
}

/// The chat's own crew name (or agents/<role>.md) in its starting note, if any.
fn own_token(c: &Ctx, first: &str) -> Option<String> {
    let mut best: Option<(usize, String)> = None;
    for lead in [r"\bJob:\s*[*`]{0,2}", r"\b(?:you are|i am|i'm)\s+(?:the\s+)?[*`]{0,2}"] {
        let l = rei(lead);
        let mut at = 0;
        while let Some(m) = l.find_from_pos(first, at).ok().flatten() {
            let tail = &first[m.end()..];
            let anchored = re(&format!("^(?:{})", c.crew.as_str()));
            if let Some(cm) = find(&anchored, tail) {
                // a profile pattern may swallow "You are " before the name
                let name = rei(r"^(?:you are|i am|i'm)\s+(?:the\s+)?[*`]{0,2}").replace(cm.as_str(), "").to_string();
                if best.as_ref().map(|b| m.start() < b.0).unwrap_or(true) { best = Some((m.start(), name)); }
                break;
            }
            at = m.end().max(m.start() + 1);
            if at >= first.len() { break; }
        }
    }
    best.map(|b| b.1)
}

fn is_manager(c: &Ctx, first: &str) -> bool {
    if let Some(tok) = own_token(c, first) { return token_is_manager(c, &tok); }
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
// ---- the crew lists: the manager in force (items 94, 101) ----
fn name_num(n: &str) -> Option<(String, u32)> {
    let m = caps(&re(r"^(.+?_[^_\s|]+?)(?:_(\d{3}))?$"), n)?; // D-040: a name is <Role>_<project>; old names may still carry a number
    Some((m[1].to_string(), m.get(2).and_then(|x| x.as_str().parse().ok()).unwrap_or(0)))
}
fn is_manager_name(profile: &Value, n: &str) -> bool {
    is(&re(r"^Manager_[^_\s|]+(?:_\d{3})?$"), n) || pstrings(profile, "manager_names").iter().any(|x| is(&re(&format!("^(?:{x})$")), n))
}
/// [(name, chat id, is a manager)] of the running crew rows: Muster's own "Running now" table; a profile's crew list in full.
fn crew_rows(root: &str, profile: &Value) -> Vec<(String, String, bool)> {
    let mut lists = vec![(Path::new(root).join("muster").join("CREW.md"), true)];
    if let Some(p) = profile.get("crew_list").and_then(Value::as_str) { lists.push((Path::new(root).join(p), false)); }
    let idre = re(r"local_[^\s|]+");
    let mut out = vec![];
    for (path, own) in lists {
        let Ok(mut text) = std::fs::read_to_string(path) else { continue };
        if own {
            text = caps(&re(r"(?s)## Running now(.*?)(?:\n## |\z)"), &text).map(|m| m[1].to_string()).unwrap_or_default();
        }
        for l in text.lines() {
            if !l.trim_start().starts_with('|') { continue; }
            let first = l.trim().trim_matches('|').split('|').next().unwrap_or("").trim().trim_matches(|c| c == '*' || c == '`').to_string();
            let id = find(&idre, l).map(|m| m.as_str().to_string());
            if name_num(&first).is_some() && (id.is_some() || !own) {
                let mgr = is_manager_name(profile, &first);
                out.push((first, id.unwrap_or_default(), mgr));
            }
        }
    }
    out
}
/// The newest manager of each project in the crew lists: where a worker's report goes, never the one in its memory.
fn managers_in_force(root: &str, profile: &Value) -> Vec<(String, String)> {
    let mut best: Vec<(String, u32, String, String)> = vec![];
    for (name, id, mgr) in crew_rows(root, profile) {
        let Some((pre, n)) = name_num(&name) else { continue };
        if !mgr { continue; }
        match best.iter_mut().find(|b| b.0 == pre) {
            Some(b) => { if n >= b.1 { *b = (pre, n, name, id); } }
            None => best.push((pre, n, name, id)),
        }
    }
    best.into_iter().map(|b| (b.2, b.3)).collect()
}
fn recipient_is_manager(to: &str, root: &str) -> bool {
    let to = to.trim();
    let profile = load_profile();
    let force = managers_in_force(root, &profile);
    if !force.is_empty() { return !to.is_empty() && force.iter().any(|(n, i)| to == n || to == i); }
    if is(&re(r"\bManager"), to) { return true; }
    let names: Vec<fancy_regex::Regex> = pstrings(&profile, "manager_names").iter().map(|x| re(&format!("^(?:{x})"))).collect();
    let mut lists = vec![Path::new(root).join("muster").join("CREW.md")];
    if let Some(p) = profile.get("crew_list").and_then(Value::as_str) { lists.push(Path::new(root).join(p)); }
    for path in lists {
        if let Ok(t) = std::fs::read_to_string(path) {
            for l in t.lines() {
                let row = l.trim_start_matches(|c| c == '|' || c == ' ');
                if !to.is_empty() && l.contains(to) && (row.starts_with("Manager") || names.iter().any(|n| is(n, row))) { return true; }
            }
        }
    }
    false
}
fn manager_now(root: &str) -> String {
    let f = managers_in_force(root, &load_profile());
    if f.is_empty() { return String::new(); }
    format!("; the manager in force is {} (from the crew list)", f.iter().map(|(n, i)| if i.is_empty() { n.clone() } else { format!("{n} ({i})") }).collect::<Vec<_>>().join(" / "))
}
fn sessions_dir() -> Option<PathBuf> {
    if let Ok(d) = std::env::var("MUSTER_SESSIONS_DIR") { if !d.is_empty() { return Some(PathBuf::from(d)); } }
    let home = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")).unwrap_or_default();
    let appdata = std::env::var("APPDATA").unwrap_or_default();
    [Path::new(&home).join("Library/Application Support/Claude/claude-code-sessions"), Path::new(&appdata).join("Claude/claude-code-sessions"), Path::new(&home).join(".config/Claude/claude-code-sessions")]
        .into_iter().find(|p| p.is_dir())
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

/// Show first (item 63): a question to him about how something looks must come after the pictures were shown in the same turn.
const LOOK: &str = r"\b(colou?rs?|mock-?ups?|layouts?|fonts?|icons?|logos?|pictures?|images?|screenshots?|appearance|visuals?|dark mode|light mode|spacing|banners?)\b";
const LOOK_WEAK: &str = r"\b(looks?|looking|designs?|styl(?:e|es|ing)|themes?)\b";
const LOOK_SCREEN: &str = r"\b(pages?|screens?|sites?|websites?|apps?|buttons?|headers?|footers?|tiles?|cards?|charts?|dashboards?|tabs?|menus?|ui|display|phones?|mobile|windows?|panes?|panels?|texts?|on screen|homepage|web)\b";
fn pictures_shown(uses: &[Value]) -> bool {
    let img = rei(r"\.(png|jpe?g|gif|webp|svg|html?|pdf)\b");
    uses.iter().any(|u| {
        let inp = u.get("input").cloned().unwrap_or(Value::Null);
        match s(u, "name") {
            "SendUserFile" => is(&img, &inp.to_string()) || s(&inp, "display") == "render",
            "Artifact" => true,
            "AskUserQuestion" => inp.get("questions").and_then(Value::as_array).map(|qs| qs.iter().any(|q| q.get("options").and_then(Value::as_array).map(|os| os.iter().any(|o| !s(o, "preview").is_empty())).unwrap_or(false))).unwrap_or(false),
            _ => false,
        }
    })
}
/// Item 88: only the sentences that end in a question mark, never a lettered choice line.
fn question_part(text: &str) -> String {
    let choice = re(r"^\s*\W*[A-Z]\.\W");
    let q = re(r"[^.!?\n]*\?");
    let mut out: Vec<String> = vec![];
    for line in text.lines() {
        if is(&choice, line) { continue; }
        for m in q.find_iter(line).flatten() { out.push(m.as_str().to_string()); }
    }
    out.join(" ")
}
fn look_unshown(question: &str, uses: &[Value]) -> bool { (is(&rei(LOOK), question) || (is(&rei(LOOK_WEAK), question) && is(&rei(LOOK_SCREEN), question))) && !pictures_shown(uses) }

/// Group check (item 79): a chat really started this turn (not a card that only proposes one) must be followed by move_sessions into the
/// project's group and then a list_sessions read-back.
/// Item 97: what a manager may say to the owner: a lettered question, a yes he must give, the idle card (never "type in <chat>", item 103).
/// Item 123: while the crew works and nothing needs the owner, ONE status line is allowed: "Working: Engine on rug-archive-seed, Site on launch-signs-show".
fn status_line(t: &str) -> bool {
    let t = t.trim();
    t.lines().count() == 1 && t.chars().count() <= 300 && is(&re(r"^Working: \S.* on \S"), t)
}
fn owner_form_ok(t: &str) -> bool {
    if status_line(t) { return true; }
    if is(&rei(r"\bThe crew is idle\b"), t) { return true; }
    if is(&rei(r"\b(I need your yes|needs? your yes|your yes (is needed|to))\b"), t) { return true; }
    let letters = re(r"(?m)^\*\*\*[A-D]\.\*\*\*").find_iter(t).count();
    letters >= 2 || (t.contains('?') && letters >= 1)
}
fn is_news(t: &str) -> bool { is(&re(r"\b(PASS|LIVE|DONE)\b"), t) || is(&rei(r"\b(shipped|passed|merged|released|progress|landed|finished)\b"), t) }

fn group_unfiled(uses: &[Value]) -> bool {
    let starts = |u: &Value| s(u, "name").ends_with("start_session") && !matches!(u.get("input").map(|i| s(i, "initiation")).unwrap_or(""), "offer" | "own_initiative");
    let Some(last) = uses.iter().rposition(|u| starts(u)) else { return false };
    let Some(moved) = uses.iter().skip(last + 1).position(|u| s(u, "name").ends_with("move_sessions")) else { return true };
    !uses.iter().skip(last + 1 + moved + 1).any(|u| s(u, "name").ends_with("list_sessions"))
}

/// Founder orders (item 76): a reply that says it cannot or will not do a task, or argues with it, when he typed it.
fn refuses_order(t: &str) -> bool {
    // "I can't tell which one" is a question's lead-in, not a refusal
    let t = &sub(&rei(r"\bi\s+(?:can(?:'|’)?t|cannot)\s+(?:tell|know|see|find|work\s+out|be\s+sure|understand|decide)\b"), t, " ");
    is(&rei(r"\b(i\s+can(?:'|’)?t|i\s+cannot|i\s+won(?:'|’)?t|i(?:'|’)?m\s+unable|i\s+am\s+unable|i(?:'|’)?m\s+not\s+able|i\s+am\s+not\s+able|i\s+(?:would|'d)\s+advise\s+against|i\s+don(?:'|’)?t\s+think\s+(?:we|you)\s+should|i\s+(?:am\s+)?not\s+going\s+to|that\s+is\s+not\s+possible|that(?:'|’)?s\s+not\s+possible|i\s+disagree|i\s+don(?:'|’)?t\s+agree|that(?:'|’)?s\s+a\s+bad\s+idea|would\s+be\s+a\s+mistake|i\s+took\s+(?:that|this)\s+to\s+mean|i\s+assumed|i\s+interpreted|you\s+(?:probably|likely|really)\s+mean|what\s+you\s+(?:really|probably)\s+mean|i\s+read\s+(?:that|this)\s+as|i(?:'|’)ll\s+do\s+[^.]{0,60}\s+instead|i\s+will\s+do\s+[^.]{0,60}\s+instead)\b"), t)
}

// ---- blocking guards (item 117): a project's own "guard" config says which folders are protected and which public repos it may push to ----
fn secret_shapes() -> fancy_regex::Regex {
    re(r"AKIA[0-9A-Z]{16}|\bgh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|\bxox[abprs]-[A-Za-z0-9-]{10,}|\b[sr]k_live_[A-Za-z0-9]{16,}|\bsk-ant-[A-Za-z0-9_-]{20,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}|\bAIza[0-9A-Za-z_-]{35}|-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")
}
const SECRET_WHY: &str = "a key or secret value is about to be written into {} (item 117): keep it in an ignored .env file, never in a tracked file, a commit message or a message; a placeholder like <your-key> or a .env.example is fine";

fn secret_in(text: &str) -> bool {
    if is(&secret_shapes(), text) { return true; }
    let env_line = re(r#"(?m)^[ \t]*(?:export[ \t]+)?[A-Za-z][A-Za-z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE)[A-Za-z0-9_]*[ \t]*=[ \t]*["']?([^\s"'#]{8,})"#);
    let placeholder = rei(r"^(?:<.*>|\$.*|\{\{.*|%.*%|\.{3,}|\*{3,}|x{3,}.*|your[-_ ].*|my[-_ ].*|changeme.*|change[-_]me.*|replace.*|example.*|placeholder.*|dummy.*|redacted.*|secret|password|token|none|null|todo|test.*|(.)\1{5,})$");
    for m in env_line.captures_iter(text).flatten() {
        if let Some(v) = m.get(1) { if !is(&placeholder, v.as_str()) { return true; } }
    }
    false
}

fn under(path: &str, folder: &str) -> bool {
    let (p, f) = (path.replace('\\', "/"), folder.replace('\\', "/"));
    let (p, f) = (p.trim_end_matches('/'), f.trim_end_matches('/'));
    p == f || p.starts_with(&format!("{f}/"))
}

fn in_protected(path: &Path, conf: &Value) -> bool {
    let p = normalise(path).to_string_lossy().replace('\\', "/");
    pstrings(conf, "protected_folders").iter().any(|f| under(&p, f) && !under(&p, &format!("{}/.claude/worktrees", f.trim_end_matches('/'))))
}

fn repo_of(url: &str) -> Option<(String, String)> {
    let m = caps(&re(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$"), url.trim())?;
    Some((m[1].to_string(), m[2].to_string()))
}

/// True/False from the GitHub CLI; None when it cannot be told (then nothing is refused). MUSTER_GUARD_PUBLIC names public repos for the self-tests.
fn repo_public(owner: &str, name: &str) -> Option<bool> {
    if let Ok(forced) = std::env::var("MUSTER_GUARD_PUBLIC") { return Some(forced.split(',').any(|x| x.trim() == name)); }
    let out = Command::new("gh").args(["repo", "view", &format!("{owner}/{name}"), "--json", "isPrivate", "-q", ".isPrivate"]).output().ok()?;
    match String::from_utf8_lossy(&out.stdout).trim() { "false" => Some(true), "true" => Some(false), _ => None }
}

fn guard_shell(cmd: &str, cwd: &str, conf: &Value) -> Option<String> {
    let mut cur: PathBuf = if cwd.is_empty() { std::env::current_dir().unwrap_or_default() } else { cwd.into() };
    let sep = re(r"&&|\|\||[;&|\n]");
    let public_repos: Vec<Value> = conf.get("public_repos").and_then(Value::as_array).cloned().unwrap_or_default();
    let flat = sub(&sep, cmd, "\u{1}");
    for seg in flat.split('\u{1}') {
        let w = shell_words(seg);
        if w.is_empty() { continue; }
        if w[0] == "cd" && w.len() > 1 { cur = normalise(&cur.join(expand_home(&w[1]))); continue; }
        let mut i = 0;
        while i < w.len() && (matches!(w[i].as_str(), "sudo" | "command" | "env") || w[i].split('/').next().unwrap_or("").contains('=')) { i += 1; }
        if i >= w.len() || Path::new(&w[i]).file_name().and_then(|x| x.to_str()) != Some("git") { continue; }
        let mut a: &[String] = &w[i + 1..];
        let mut wh = cur.clone();
        while !a.is_empty() && a[0].starts_with('-') {
            if a[0] == "-C" && a.len() > 1 { wh = normalise(&cur.join(expand_home(&a[1]))); a = &a[2..]; } else { a = &a[1..]; }
        }
        if a.is_empty() { continue; }
        let (sub, rest) = (a[0].as_str(), &a[1..]);
        if !pstrings(conf, "protected_folders").is_empty() && in_protected(&wh, conf) {
            let bad = sub == "reset"
                || (sub == "stash" && !rest.first().map(|r| r == "list" || r == "show").unwrap_or(false))
                || (sub == "checkout" && rest.iter().any(|r| r == "." || r == "-f" || r == "--force"))
                || (sub == "restore" && rest.iter().any(|r| r == "."));
            if bad { return Some(format!("git {sub} is not run in a protected main folder (item 117): it can throw away other chats' unsaved work; do it in your own copy, or ask the manager")); }
        }
        if sub == "push" {
            let pos: Vec<&String> = rest.iter().filter(|r| !r.starts_with('-')).collect();
            let remote = pos.first().map(|r| r.as_str()).unwrap_or("origin");
            let url = if remote.contains("github.com") { remote.to_string() } else {
                Command::new("git").args(["-C", &wh.to_string_lossy(), "remote", "get-url", remote]).output().map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string()).unwrap_or_default()
            };
            if let Some((owner, name)) = repo_of(&url) {
                if let Some(r) = public_repos.iter().find(|x| s(x, "name") == name) {
                    let sc = s(r, "scanner");
                    return Some(format!("a push to {name} goes only through its scanner (item 117): run {}", if sc.is_empty() { "the project's scanner" } else { sc }));
                }
                if !pstrings(conf, "push_allowed").iter().any(|x| *x == name) && repo_public(&owner, &name) == Some(true) {
                    return Some(format!("{name} is a public repo and this project does not allow pushing to it (item 117): ask the manager"));
                }
            }
        }
    }
    None
}

fn guard_problem(tool: &str, inp: &Value, cwd: &str, conf: &Value) -> Option<String> {
    let why = |w: &str| SECRET_WHY.replace("{}", w);
    match tool {
        "Bash" => {
            let cmd = s(inp, "command");
            if let Some(w) = guard_shell(cmd, cwd, conf) { return Some(w); }
            if is(&re(r"\bgit\s+(?:-C\s+\S+\s+)?commit\b"), cmd) && secret_in(cmd) { return Some(why("a commit message")); }
            None
        }
        "SendMessage" => if secret_in(s(inp, "message")) { Some(why("a message")) } else { None },
        "Write" | "Edit" | "MultiEdit" | "NotebookEdit" => {
            let path = s(inp, "file_path");
            let body = ["content", "new_string", "new_source"].iter().map(|k| s(inp, k)).collect::<Vec<_>>().join(" ");
            if is(&re(r"\.env\.(?:example|sample|template|dist)$"), path) || !secret_in(&body) { return None; }
            let folder = Path::new(path).parent().map(|p| p.to_string_lossy().to_string()).filter(|p| !p.is_empty()).unwrap_or_else(|| ".".into());
            let ignored = Command::new("git").args(["-C", &folder, "check-ignore", "-q", path]).status().map(|st| st.success()).unwrap_or(false);
            if ignored { None } else { Some(why("a tracked file")) }
        }
        _ => None,
    }
}

/// True when a bold 'WORD . job' heading line stands above the first lettered choice line (item 120).
fn title_above_choices(text: &str) -> bool {
    let letter = re(r"^\*\*\*[A-D]\.\*\*\*");
    let title = re(r"^\s*\*\*[^*\n]+\s[\u{b7}.]\s[^*\n]+\*\*\s*$");
    for l in text.lines() {
        if is(&letter, l) { return false; }
        if is(&title, l) { return true; }
    }
    false
}

fn pretool(c: &Ctx, data: &Value, manager: bool) {
    let tool = s(data, "tool_name");
    let empty = Value::Object(Default::default());
    let inp = data.get("tool_input").unwrap_or(&empty);
    let root = main_folder(s(data, "cwd"));
    if let Some(conf) = c.profile.get("guard").filter(|g| g.is_object()) {
        if let Some(why) = guard_problem(tool, inp, s(data, "cwd"), conf) { return deny(&why); }
    }
    if tool == "SendMessage" { return send_message(c, data, inp, &root, manager); }
    if tool == "Agent" || tool == "Task" { return helper_problem(inp, manager); }
    if tool.ends_with("start_session") {
        // a started chat's card title is its final name: "Start Engine_PINR_006" would stay (item 69)
        let t = s(inp, "title");
        if is(&rei(r"^\s*start\s+\S+_\S+?(?:_\d{3})?\s*$"), t) { return deny(&format!("a started chat's card title is its final name: use the worker's full name without a prefix (not \"{t}\")")); }
        return;
    }
    if tool.ends_with("__wrap_up") { // item 119: the app's next-step box is not used; questions go only through Muster's clickable choices
        if !s(inp, "ask").trim().is_empty() || inp.get("actions").map(|a| !a.is_null() && a.as_array().map(|x| !x.is_empty()).unwrap_or(true)).unwrap_or(false) {
            return deny("no question or buttons in the app's wrap-up call (item 119): leave ask and actions out, so no grey next-step box is drawn; put any question to the owner in the chat as lettered choices (***A.*** ... with a blank line between, your pick marked \"my pick\")");
        }
        return;
    }
    if tool == "AskUserQuestion" {
        if manager { return deny("no choice card (it locks the chat until he answers): write the question in the chat as lettered lines, ***A.*** ... one per line with a blank line between, your pick marked \"my pick\"; he answers by typing a letter. Keep working on anything that does not depend on his answer"); } // item 80, D-037
        return;
    }
    // item 108, D-027: the Muster files are the only rulebook; no crew chat writes crew rules into its own memory
    let mem_dir = re(r"/\.claude/projects/[^/]+/memory/");
    let rule_words = re(r"\b[Mm]uster\b|\bcrew\b|rules page|\bD-0\d\d\b|\bitem \d{2,3}\b|\b(?:Manager|Builder|Inspector|Designer)[ _]|\b(?:READY|STUCK)\b");
    const MEMORY_WHY: &str = "the Muster files are the only rulebook (item 108): do not write crew rules into your own memory; if a rule is missing or wrong, send the manager a NEED";
    if matches!(tool, "Write" | "Edit" | "MultiEdit" | "NotebookEdit") {
        let mp = s(inp, "file_path").replace('\\', "/");
        let body = ["content", "new_string", "new_source"].iter().map(|k| s(inp, k)).collect::<Vec<_>>().join(" ");
        if is(&mem_dir, &mp) && is(&rule_words, &body) { return deny(MEMORY_WHY); }
    }
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
        let cmd_no_path = sub(&re(r"\S*/\.claude/projects/\S*"), cmd, " ");
        if is(&rule_words, &cmd_no_path) {
            let base = { let cw = s(data, "cwd"); if cw.is_empty() { std::env::current_dir().unwrap_or_default() } else { cw.into() } };
            for tgt in shell_write_targets(cmd) {
                let full = normalise(&base.join(expand_home(&tgt))).to_string_lossy().replace('\\', "/");
                if is(&mem_dir, &full) { return deny(MEMORY_WHY); }
            }
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

/// Item 97: two reports of the same job and first word with nothing changed (only the ID differs).
fn report_key(m: &str) -> Option<String> {
    if let Ok(Value::Object(mut o)) = serde_json::from_str::<Value>(m.trim()) { o.remove("id"); return Some(Value::Object(o).to_string()); }
    let c = caps(&re(&format!(r"(?s)^\s*{FIRST}: (.+?) \[ID [^\]]+\]\s*\n(.*)$")), m)?;
    Some(format!("{}|{}|{}", &c[1], &c[2], sub(&re(r"\s+"), c[3].trim(), " ")))
}
fn dup_report(to: &str, msg: &str, path: &str) -> bool {
    let Some(k) = report_key(msg) else { return false };
    all_sent_pairs(path).iter().any(|(t, m)| t == to && report_key(m).as_deref() == Some(k.as_str()))
}
const DUP_WHY: &str = "this report (same job and first word) was already sent to this chat with nothing changed; send it again only when something changed (item 97)";

/// Item 115: his question gets an answer, not an order. A manager's order to a worker in a turn his question started is refused unless it
/// cites his recorded choice (owner_words item with a Choice line under it).
fn question_order_problem(c: &Ctx, manager: bool, root: &str, msg: &str, rec: Option<&Value>, path: &str) -> Option<String> {
    if !manager || !owner_questioned(path) { return None; }
    let item: Option<i64> = match rec {
        Some(r) => { if s(r, "kind") != "ORDER" { return None; } r.get("owner_words").and_then(|o| o.get("item")).and_then(Value::as_i64) }
        None => {
            if !is(&rei(r"(?m)^\s*(Job|Owner'?s words)\s*:"), msg) { return None; }
            caps(&rei(r"\bitem\s+(\d+)"), msg).and_then(|m| m[1].parse().ok())
        }
    };
    let rel = c.profile.get("founder_list").and_then(Value::as_str).unwrap_or("muster/OWNERS-LIST.md");
    if let Some(i) = item { if choice_recorded(root, rel, i) { return None; } }
    Some("his question gets an answer, not an order (item 115): answer it in plain words; any action it might lead to goes back to him as lettered choices with your pick, and an order follows only after his recorded choice (cite that list item, with its Choice line)".to_string())
}

fn send_message(c: &Ctx, data: &Value, inp: &Value, root: &str, manager: bool) {
    let msg = s(inp, "message");
    if is(&social_re(), msg) { return deny("no 'noted' or 'thanks' replies; send a message only when someone must act"); }
    let sent = || all_sent_text(s(data, "transcript_path"));
    if !c.text_form {
        // a data record: one JSON object, fixed keys, set values, no sentences
        let rec0: Value = serde_json::from_str(msg.trim()).unwrap_or(Value::Null);
        let things = project_things(s(data, "cwd"), s(&rec0, "sha")); // the worker's own copy at that sha, not the main folder
        if let Err(why) = crate::record::validate(msg, &things) { return deny(&format!("a message between chats is a data record (JSON with fixed keys and set values), never sentences, and this one is wrong: {why}")); }
        let rec: Value = serde_json::from_str(msg.trim()).unwrap_or(Value::Null);
        if let Some(why) = question_order_problem(c, manager, root, msg, Some(&rec), s(data, "transcript_path")) { return deny(&why); }
        let (id, kind) = (s(&rec, "id"), s(&rec, "kind"));
        if sent().iter().any(|t| serde_json::from_str::<Value>(t.trim()).map(|r| s(&r, "id") == id).unwrap_or(false)) { return deny(&format!("this record's id {id} was already sent; a repeat is dropped")); }
        if kind == "ORDER" { if let Some(why) = goal_problem(root, s(&rec, "job")) { return deny(&why); } }
        if kind == "ORDER" && usage_at_limit(root) { return deny("the week is at 90% or more (scripts/usage.py exits 3): start no new order; finish and park what is running"); }
        if dup_report(s(inp, "to"), msg, s(data, "transcript_path")) { return deny(DUP_WHY); }
        return;
    }
    if let Some(why) = question_order_problem(c, manager, root, msg, None, s(data, "transcript_path")) { return deny(&why); }
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
        if dup_report(s(inp, "to"), msg, s(data, "transcript_path")) { return deny(DUP_WHY); }
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
    if status_line(t) { return true; } // the working status line (item 123)
    if t.chars().count() <= 300 && t.trim().lines().count() <= 3 && is(&rei(r"\bon the board\b"), t) { return true; } // a short pointer to the news (item 60)
    if is(&rei(r"\bThe crew is idle\b"), t) { return true; }
    if is(&rei(r"\b(I need your yes|needs? your yes|your yes (is needed|to))\b"), t) { return true; }
    let has_q = t.contains('?');
    let letters = re(r"(?m)^\*\*\*[A-D]\.\*\*\*").find_iter(t).count(); // lettered lines are the question form (D-037)
    letters >= 2 || (has_q && letters >= 1) // two or more lettered choices are the question, with or without a "?" (item 91)
}

/// True when this turn was started by his own typed message (not an app event, another chat or hook feedback).
fn owner_typed_last(path: &str) -> bool {
    let ends = rei(r"<cross-session-message|<task-notification|<side-sessions-event|<ci-monitor-event|\[SYSTEM NOTIFICATION");
    let neutral = rei(r"^\s*(<system-reminder|Stop hook feedback|Stop hook blocking error)");
    let mut typed = false;
    for d in lines_of(path) {
        if s(&d, "type") != "user" { continue; }
        let c = msg_content(&d);
        if let Value::Array(a) = &c { if a.iter().any(|b| s(b, "type") == "tool_result") { continue; } }
        let t = content_text(&c);
        if t.trim().is_empty() { continue; }
        if is(&ends, &t) { typed = false; } else if !is(&neutral, &t) { typed = true; }
    }
    typed
}


fn stop(c: &Ctx, data: &Value, manager: bool) {
    let text = s(data, "last_assistant_message");
    // Founder orders (item 76): NOT subject to the once-per-turn pass. A manager reply that refuses, says it cannot, argues with or
    // reinterprets a task he typed is refused every time; the only way through is doing it, or one short question to him.
    if manager && !text.is_empty() && refuses_order(text) && owner_typed_last(s(data, "transcript_path")) {
        block("he gave you an order in his own words, and a coded rule says you do it: no refusing, no \"cannot\", no arguing, no reinterpreting (item 76). Do the task now, or if you are unsure ask him ONE short question, nothing else");
        return;
    }
    if text.is_empty() || data.get("stop_hook_active").and_then(Value::as_bool).unwrap_or(false) || bounced_this_turn(s(data, "transcript_path")) { return; }
    let tpath = s(data, "transcript_path");
    let uses = turn_blocks(tpath);
    if manager && group_unfiled(&uses) && !is(&rei(r"\bdrag\b"), text) {
        block("you started a chat this turn but did not file it: after start_session call move_sessions into the project's group, then read it back with list_sessions (skill start-the-crew). If the app refuses a step, say so and name what to drag");
        return;
    }
    let asked_at = uses.iter().rposition(|u| s(u, "name") == "AskUserQuestion");
    if manager {
        if let Some(letter) = typed_letter_answer(tpath) {
            let recorded = uses.iter().any(|u| s(u, "name") == "Bash" && u.get("input").map(|i| s(i, "command").contains(&c.recorder)).unwrap_or(false));
            if !recorded {
                block(&format!("he answered your lettered question by typing \"{letter}\", and it is not recorded: run {} with the question, every option's text and the one he picked (word for word) under its list item before ending the turn", recorder_path(&main_folder(s(data, "cwd")), &c.recorder)));
            }
            return; // a turn that answers his typed letter is handled once recorded
        }
        if let Some(idx) = asked_at.filter(|&i| !card_skipped(tpath, s(&uses[i], "id"))) {
            let recorded = uses[idx + 1..].iter().any(|u| s(u, "name") == "Bash" && u.get("input").map(|i| s(i, "command").contains(&c.recorder)).unwrap_or(false));
            if !recorded { block(&format!("a choice card was answered but not recorded: run {} with his exact answer{} under its list item before ending the turn", recorder_path(&main_folder(s(data, "cwd")), &c.recorder), if c.recorder == "record-choice.py" { " (or --no-pick if he skipped the card or typed his own words)" } else { "" })); } // never name a flag the project's recorder lacks
            return;
        }
        if letters_not_bold_italic(text) {
            block("write each choice letter bold and italic, like ***A.*** red, one line per choice with a blank line between (item 80)");
            return;
        }
        if is(&rei(r"\bis waiting for you\b|\btype (?:it |your \w+ |anything )?in (?:the |that |this )?[\w .-]*\b(?:chat|window)\b"), text) {
            block("never send the owner to type in a worker's chat (item 103): carrying his approval is your job; forward his quoted go to the worker that asked, by message, and say nothing to him");
            return;
        }
        if is_news(text) && !owner_form_ok(text) && !owner_asked(tpath) {
            block("never tell the owner PASS, LIVE, DONE, shipped or progress news (item 97): his chat gets only a lettered question, a yes he must give, or the idle card. When nothing needs him, end this turn with no text at all");
            return;
        }
        if news_with_question(text) && !owner_asked(tpath) {
            block("news does not ride along with a question (item 114): his chat gets the question alone; the news goes to the board only");
            return;
        }
        if question_repeated(tpath, text) {
            block("he has already been asked this question and has not answered (item 114): do not put it to him again; keep working on what does not depend on his answer, and end this turn with no text");
            return;
        }
        if re(r"(?m)^\*\*\*[A-D]\.\*\*\*").find_iter(text).count() >= 2 && !is(&rei(r"\bmy pick\b"), text) {
            block("every lettered question carries your pick: mark one choice *(my pick)* and give a one-line reason, looks included; a pick is advice only and nothing is ordered until he answers (item 100)");
            return;
        }
        if re(r"(?m)^\*\*\*[A-D]\.\*\*\*").find_iter(text).count() >= 2 && !title_above_choices(text) {
            block("a question to the owner opens with a bold heading line 'WORD \u{b7} job' (like **ASK \u{b7} score-audit**) above the lettered choices, so it draws as a card (item 120)");
            return;
        }
        if text.contains('?') && look_unshown(&question_part(text), &uses) {
            block("a question about how something looks comes after the pictures: show them to him first in this turn (send-file with render, or card previews), then ask");
            return;
        }
        if !manager_reply_ok(text) && !owner_asked(tpath) && !(peer_started(tpath) && text.trim().chars().count() <= 300 && text.trim().lines().count() <= 3) { // a short routine reply to another chat's message is not bounced (item 75)
            block("to the owner the manager says only a question with its choices as lettered lines (***A.*** ...), a yes he must give, 'The crew is idle', or the one status line 'Working: <who> on <job>, ...' while the crew works; never send him to type in a worker's chat, relay his answer yourself (item 103). Rewrite the reply as one of those, or put the news on the board");
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
        return;
    }
    if is(&re(r"^\s*\*\*(DONE|READY|PASS|FAIL|STUCK|NEED)\b"), body) { // item 65: every report reaches the manager as a message
        let root = main_folder(s(data, "cwd"));
        // SendMessage (to) or the app's older send_message tool (session_id); either reaches the manager
        if !uses.iter().any(|u| u.get("input").map(|i| (s(u, "name") == "SendMessage" && recipient_is_manager(s(i, "to"), &root)) || (s(u, "name").ends_with("send_message") && recipient_is_manager(s(i, "session_id"), &root))).unwrap_or(false)) {
            let w = body.split_whitespace().next().unwrap_or("").trim_matches('*');
            block(&format!("a report reaches the manager as a message as well as the board (item 65): send the manager your {w} report with SendMessage (a different ID from any copy to someone else), then end the turn with the card{}", manager_now(&root)));
        }
    }
}

/// The profiles of the project this chat works in, joined: the file named in MUSTER_PROFILE, and in the chat's folder or any folder
/// above it both .muster-checks/profile.json and the profile a live stand-in (.muster-checks/live.json) points to. The first guard
/// found wins; crew names from all are kept.
fn project_profile(data: &Value) -> Value {
    let mut cands: Vec<std::path::PathBuf> = vec![];
    if let Ok(p) = std::env::var("MUSTER_PROFILE") { if !p.is_empty() { cands.push(p.into()); } }
    let start = std::env::var("CLAUDE_PROJECT_DIR").ok().filter(|x| !x.is_empty()).unwrap_or_else(|| {
        let c = s(data, "cwd"); if c.is_empty() { std::env::current_dir().map(|p| p.to_string_lossy().to_string()).unwrap_or_default() } else { c.to_string() }
    });
    let mut d = std::path::PathBuf::from(start);
    loop {
        let mc = d.join(".muster-checks");
        if let Some(lj) = std::fs::read_to_string(mc.join("live.json")).ok().and_then(|t| serde_json::from_str::<Value>(&t).ok()) {
            if let (Some(m), Some(p)) = (lj.get("muster").and_then(Value::as_str), lj.get("profile").and_then(Value::as_str)) {
                if !m.is_empty() && !p.is_empty() { cands.push(std::path::Path::new(m).join(p)); }
            }
        }
        cands.push(mc.join("profile.json"));
        match d.parent() { Some(p) if p != d => d = p.to_path_buf(), _ => break }
    }
    let mut guard: Option<Value> = None;
    let mut names: Vec<Value> = vec![];
    for c in cands {
        if !c.is_file() { continue; }
        let Some(j) = std::fs::read_to_string(&c).ok().and_then(|t| serde_json::from_str::<Value>(&t).ok()).filter(Value::is_object) else { continue };
        if guard.is_none() { if let Some(g) = j.get("guard").filter(|g| g.is_object()) { guard = Some(g.clone()); } }
        for n in j.get("crew_names").and_then(Value::as_array).cloned().unwrap_or_default() { if !names.contains(&n) { names.push(n); } }
    }
    let mut out = serde_json::Map::new();
    if let Some(g) = guard { out.insert("guard".into(), g); }
    out.insert("crew_names".into(), Value::Array(names));
    Value::Object(out)
}

/// Item 117 on its own: the guard in a project's own profile blocks even where the project runs its own older installed copy.
pub fn run_guard() -> i32 {
    let Some(data) = read_stdin() else { return 0 };
    if s(&data, "hook_event_name") != "PreToolUse" { return 0; }
    let prof = project_profile(&data);
    let Some(conf) = prof.get("guard").filter(|g| g.is_object()) else { return 0 };
    let first = first_message(s(&data, "transcript_path"));
    if !is(&crew_re(&prof), &first) && std::env::var("MUSTER_ASSUME_CREW").ok().as_deref() != Some("1") { return 0; }
    let empty = Value::Object(Default::default());
    if let Some(why) = guard_problem(s(&data, "tool_name"), data.get("tool_input").unwrap_or(&empty), s(&data, "cwd"), conf) { deny(&why); }
    0
}

pub fn run() -> i32 {
    let Some(data) = read_stdin() else { return 0 };
    if stood_down(&data, "rules-check.py") { return 0; }
    let c = ctx();
    let mut first = first_message(s(&data, "transcript_path"));
    if !is(&c.crew, &first) { // a compaction rewrote the first message and no .muster-first was kept: the summary may say who the chat is
        let summ = compact_summary(s(&data, "transcript_path"));
        if !summ.is_empty() && own_token(&c, &summ).is_some() { first = summ; }
    }
    if !is(&c.crew, &first) && std::env::var("MUSTER_ASSUME_CREW").ok().as_deref() != Some("1") { return 0; }
    remember_first(s(&data, "transcript_path"), &first);
    let manager = is_manager(&c, &first) || std::env::var("MUSTER_ASSUME_MANAGER").ok().as_deref() == Some("1");
    match s(&data, "hook_event_name") { "PreToolUse" => pretool(&c, &data, manager), "Stop" => stop(&c, &data, manager), _ => {} }
    0
}
#[allow(dead_code)]
fn _unused() { let _ = ROLE; }
