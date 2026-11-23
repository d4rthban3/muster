//! A worker-to-worker message is a data record, never a sentence (owner's list item 34: "Data fields only").
//! It is one JSON object with fixed keys; every value is a number, a version, a short code from a set list, or a list of codes.
//! A value that holds a space, or any key that is not listed, is refused: there is no room for English in a record.
use serde_json::{Map, Value};
use std::collections::HashSet;

const KINDS: [&str; 8] = ["READY", "DONE", "PASS", "FAIL", "STUCK", "NEED", "OWNER_CALL", "ORDER"];
const NEEDS: [&str; 6] = ["none", "pass_or_fail", "order", "owner_answer", "fix", "unblock"];
const DONE_WHEN: [&str; 4] = ["ready", "pass", "live", "report"];
/// An ORDER says what happens after the work: start (do it and send READY), hold (after PASS wait for the owner's go), ship (after PASS ship).
const ACTIONS: [&str; 3] = ["ship", "hold", "start"];
/// One free-text `note` (item 52): the only key that may hold sentences. Code checks its length, that it is one line of plain text, and that it carries no key or password.
const NOTE_MAX: usize = 400;
const KEYS: [&str; 17] = [
    "v", "kind", "id", "job", "from", "to", "sha", "version", "tests", "touches", "need", "usage", "owner_words", "owns", "out", "action", "note",
];

fn code(v: &Value, what: &str, lo: usize, hi: usize) -> Result<String, String> {
    let s = v.as_str().ok_or_else(|| format!("{what} must be a code (text without spaces)"))?;
    let ok = s.len() >= lo
        && s.len() <= hi
        && s.chars().all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-' || c == '_');
    if ok { Ok(s.to_string()) } else { Err(format!("{what} must be {lo}-{hi} characters of a-z, 0-9, - or _ (no spaces, no sentences)")) }
}

/// A short code: at most `words` words (split at - or _) and `max` characters, so a sentence cannot fit.
fn short_code(v: &Value, what: &str, max: usize, words: usize) -> Result<String, String> {
    let c = code(v, what, 1, max)?;
    if c.split(|ch| ch == '-' || ch == '_').filter(|w| !w.is_empty()).count() > words {
        return Err(format!("{what} may hold at most {words} words (it is a code, not a sentence)"));
    }
    Ok(c)
}

/// Things a record may name besides the project's own top-level folders and files.
pub const FIXED_THINGS: [&str; 7] = ["database", "file-store", "outside-connection", "board", "owners-list", "crew-files", "site"];

/// A top-level folder or file name as a code: lowercase, every run of other characters becomes one dash ("CHANGELOG.md" -> "changelog-md").
pub fn thing_code(name: &str) -> String {
    let mut o = String::new();
    for c in name.chars() {
        if c.is_alphanumeric() && c.is_ascii() { o.push(c.to_ascii_lowercase()); } else if !o.ends_with('-') { o.push('-'); }
    }
    o.trim_matches('-').to_string()
}

fn list_of_codes(v: &Value, what: &str, things: &HashSet<String>) -> Result<(), String> {
    let a = v.as_array().ok_or_else(|| format!("{what} must be a list of codes"))?;
    if a.len() > 12 { return Err(format!("{what} holds more than 12 entries")); }
    for x in a {
        let c = short_code(x, what, 24, 3)?;
        if !things.contains(&c) && !FIXED_THINGS.contains(&c.as_str()) {
            return Err(format!("{what} entry '{c}' is not a top-level folder or file of the project, or one of {}", FIXED_THINGS.join(", ")));
        }
    }
    Ok(())
}

/// A role code: manager, designer, inspector, design-inspector, sketchpad, ai-socket, agent-teacher, board, builder-a..z, inspector-a..z.
fn role_code(v: &Value, what: &str) -> Result<String, String> {
    let c = code(v, what, 1, 24)?;
    let fixed = ["manager", "designer", "inspector", "design-inspector", "sketchpad", "ai-socket", "agent-teacher", "board"];
    let lettered = |p: &str| c.strip_prefix(p).map(|r| r.len() == 1 && r.chars().all(|ch| ch.is_ascii_lowercase())).unwrap_or(false);
    if fixed.contains(&c.as_str()) || lettered("builder-") || lettered("inspector-") { Ok(c) } else { Err(format!("{what} must be a role code ({}, builder-a, inspector-b ...)", fixed.join(", "))) }
}

fn num(v: &Value, what: &str, max: u64) -> Result<u64, String> {
    let n = v.as_u64().ok_or_else(|| format!("{what} must be a whole number"))?;
    if n > max { Err(format!("{what} is above {max}")) } else { Ok(n) }
}

fn version(v: &Value) -> Result<(), String> {
    let s = v.as_str().ok_or("version must be x.y.z or null")?;
    let p: Vec<&str> = s.split('.').collect();
    if p.len() == 3 && p.iter().all(|x| !x.is_empty() && x.len() <= 6 && x.chars().all(|c| c.is_ascii_digit())) { Ok(()) } else { Err("version must be x.y.z".into()) }
}

fn sha(v: &Value) -> Result<(), String> {
    let s = v.as_str().ok_or("sha must be 7-40 hex characters or null")?;
    if (7..=40).contains(&s.len()) && s.chars().all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()) { Ok(()) } else { Err("sha must be 7-40 lowercase hex characters".into()) }
}

fn note(v: &Value) -> Result<(), String> {
    let s = v.as_str().ok_or("note must be text")?;
    if s.trim().is_empty() { return Err("note is empty (leave the key out)".into()); }
    if s.chars().count() > NOTE_MAX { return Err(format!("note is {} characters; the cap is {NOTE_MAX} (shorten it, or write the detail to a notes file and put only its name here)", s.chars().count())); }
    if s.chars().any(|c| c.is_control()) { return Err("note must be one line of plain text".into()); }
    let secret = fancy_regex::Regex::new(r"(?i)((?<![A-Za-z0-9])sk-[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{12,}|AKIA[A-Z0-9]{12,}|BEGIN [A-Z ]*PRIVATE KEY|password\s*[:=]|api[_-]?key\s*[:=]|token\s*[:=])").unwrap();
    if secret.is_match(s).unwrap_or(false) { return Err("a note never carries a key, password or token".into()); }
    Ok(())
}

fn opt<'a>(m: &'a Map<String, Value>, k: &str) -> Option<&'a Value> {
    m.get(k).filter(|v| !v.is_null())
}

/// Ok(()) when the text is one valid record; Err(why) otherwise. Every fault found is named in the one answer (joined with "; "), so a
/// record is rewritten once, not once per fault (item 132).
/// `things`: the project's top-level folder and file names as codes (see thing_code); touches, owns and out may name only these or FIXED_THINGS.
pub fn validate(text: &str, things: &HashSet<String>) -> Result<(), String> {
    let v: Value = serde_json::from_str(text.trim()).map_err(|_| "not a record: it must be one JSON object (data, not a sentence)".to_string())?;
    let m = v.as_object().ok_or("not a record: it must be one JSON object")?;
    let mut errs: Vec<String> = Vec::new();
    let unknown: Vec<String> = m.keys().filter(|k| !KEYS.contains(&k.as_str())).map(|k| format!("'{k}'")).collect();
    if !unknown.is_empty() { errs.push(format!("unknown key {}", unknown.join(", "))); }
    macro_rules! chk { ($e:expr) => { if let Err(x) = $e { errs.push(x); } }; }
    if let Some(n) = m.get("note") { chk!(note(n)); }
    if m.get("v").and_then(Value::as_u64) != Some(1) { errs.push("v must be 1".into()); }
    let kind: Option<&str> = match m.get("kind").and_then(Value::as_str) {
        None => { errs.push("kind is missing".into()); None }
        Some(k) if !KINDS.contains(&k) => { errs.push(format!("kind '{k}' is not one of {}", KINDS.join(", "))); None }
        Some(k) => Some(k),
    };
    let mut get = |key: &str, f: &dyn Fn(&Value) -> Result<String, String>, errs: &mut Vec<String>| -> Option<String> {
        match m.get(key) { None => { errs.push(format!("{key} is missing")); None } Some(x) => match f(x) { Ok(c) => Some(c), Err(e) => { errs.push(e); None } } }
    };
    let from = get("from", &|x| role_code(x, "from"), &mut errs);
    get("to", &|x| role_code(x, "to"), &mut errs);
    let job = get("job", &|x| short_code(x, "job", 32, 4), &mut errs);
    let id = get("id", &|x| code(x, "id", 1, 48), &mut errs);
    if let (Some(from), Some(job), Some(id)) = (&from, &job, &id) {
        let n = id.strip_prefix(&format!("{from}-{job}-")).unwrap_or("");
        if n.is_empty() || n.len() > 4 || !n.chars().all(|c| c.is_ascii_digit()) { errs.push(format!("id must be {from}-{job}-<number>")); }
    }
    if let Some(need) = get("need", &|x| code(x, "need", 1, 20), &mut errs) {
        if !NEEDS.contains(&need.as_str()) { errs.push(format!("need '{need}' is not one of {}", NEEDS.join(", "))); }
    }
    if let Some(x) = opt(m, "sha") { chk!(sha(x)); }
    if let Some(x) = opt(m, "version") { chk!(version(x)); }
    if let Some(t) = opt(m, "tests") {
        match t.as_object() {
            None => errs.push("tests must be {\"passed\":n,\"failed\":n}".into()),
            Some(o) => {
                if o.len() != 2 { errs.push("tests must hold exactly passed and failed".into()); }
                match o.get("passed") { None => errs.push("tests.passed is missing".into()), Some(x) => chk!(num(x, "tests.passed", 1_000_000).map(|_| ())) }
                match o.get("failed") { None => errs.push("tests.failed is missing".into()), Some(x) => chk!(num(x, "tests.failed", 1_000_000).map(|_| ())) }
            }
        }
    }
    if let Some(x) = m.get("touches") { chk!(list_of_codes(x, "touches", things)); }
    if let Some(u) = opt(m, "usage") {
        match u.as_object() {
            None => errs.push("usage must be {\"week_pct\":n}".into()),
            Some(o) => {
                if o.len() != 1 { errs.push("usage must hold exactly week_pct".into()); }
                match o.get("week_pct") { Some(Value::Null) => {}, Some(x) => chk!(num(x, "usage.week_pct", 100).map(|_| ())), None => errs.push("usage.week_pct is missing".into()) }
            }
        }
    }
    match kind {
        Some("READY") => {
            if opt(m, "sha").is_none() { errs.push("a READY needs sha".into()); }
            match opt(m, "tests") {
                None => errs.push("a READY needs tests".into()),
                Some(t) => if t["passed"].as_u64() == Some(0) && t["failed"].as_u64() == Some(0) { errs.push("a READY needs a test count above zero".into()); },
            }
            if m.get("touches").is_none() { errs.push("a READY needs touches (a list, empty if none)".into()); }
            if !m.contains_key("usage") { errs.push("a READY needs usage".into()); }
        }
        Some("DONE") => { if !m.contains_key("usage") { errs.push("a DONE needs usage".into()); } }
        Some(k @ ("PASS" | "FAIL")) => { if opt(m, "sha").is_none() { errs.push(format!("a {k} needs the sha it checked")); } }
        Some("ORDER") => {
            match m.get("owner_words") {
                None => errs.push("an ORDER needs owner_words (his list item or decision)".into()),
                Some(ow) => match ow.as_object() {
                    None => errs.push("owner_words must be {\"item\":n} or {\"decision\":\"D-027\"}".into()),
                    Some(o) => {
                        if o.len() != 1 { errs.push("owner_words must hold exactly one of item or decision".into()); }
                        match (o.get("item"), o.get("decision")) {
                            (Some(i), None) => chk!(num(i, "owner_words.item", 10_000).map(|_| ())),
                            (None, Some(d)) => {
                                let s = d.as_str().unwrap_or("");
                                if !(s.len() == 5 && s.starts_with("D-") && s[2..].chars().all(|c| c.is_ascii_digit())) { errs.push("owner_words.decision must look like D-027".into()); }
                            }
                            _ => { if o.len() == 1 { errs.push("owner_words must be item or decision".into()); } }
                        }
                    }
                },
            }
            for key in ["owns", "out"] {
                match m.get(key) { None => errs.push(format!("an ORDER needs {key}")), Some(x) => chk!(list_of_codes(x, key, things)) }
            }
            match m.get("action") {
                None => errs.push("an ORDER needs action (ship, hold or start)".into()),
                Some(x) => match code(x, "action", 1, 8) {
                    Err(e) => errs.push(e),
                    Ok(act) => if !ACTIONS.contains(&act.as_str()) { errs.push(format!("action '{act}' is not one of {}", ACTIONS.join(", "))); },
                },
            }
            let _ = DONE_WHEN;
        }
        _ => {}
    }
    if kind.is_some() && kind != Some("ORDER") && m.contains_key("action") { errs.push("action belongs to an ORDER only".into()); }
    if errs.is_empty() { Ok(()) } else { Err(errs.join("; ")) }
}

#[cfg(test)]
mod tests {
    use super::{thing_code, validate as v};
    use std::collections::HashSet;

    fn things() -> HashSet<String> { ["hooks", "scripts", "agents", "pinr-files", "changelog-md"].iter().map(|x| x.to_string()).collect() }
    fn validate(t: &str) -> Result<(), String> { v(t, &things()) }

    const READY: &str = r#"{"v":1,"kind":"READY","id":"builder-a-lean-rebuild-1","job":"lean-rebuild","from":"builder-a","to":"inspector","sha":"d082303","version":"0.3.49","tests":{"passed":48,"failed":0},"touches":["hooks"],"need":"pass_or_fail","usage":{"week_pct":null}}"#;

    #[test]
    fn a_record_parses() { assert_eq!(validate(READY), Ok(())); }

    #[test]
    fn english_text_is_refused() {
        assert!(validate("READY: card fix\nWhat: a\nWhere: b").is_err());
        assert!(validate("Please look at my branch when you can.").is_err());
    }

    #[test]
    fn a_sentence_inside_a_field_is_refused() {
        let bad = READY.replace("lean-rebuild", "please check my lean rebuild");
        assert!(validate(&bad).unwrap_err().contains("no spaces"));
        let bad = READY.replace("\"touches\":[\"hooks\"]", "\"touches\":[\"the hooks and the tests\"]");
        assert!(validate(&bad).is_err());
    }

    #[test]
    fn a_long_dashed_sentence_cannot_pass_as_a_code() {
        let long = "the-windows-test-fails-because-the-path-uses-backslashes";
        for key in ["job", "touches"] {
            let bad = if key == "job" { READY.replace("lean-rebuild", long).replace("builder-a-lean-rebuild-1", &format!("builder-a-{long}-1")) } else { READY.replace("\"hooks\"", &format!("\"{long}\"")) };
            assert!(validate(&bad).is_err(), "{key}");
        }
        assert!(validate(&READY.replace("\"from\":\"builder-a\"", "\"from\":\"the-builder-who-is-tired\"")).is_err());
        assert!(validate(&READY.replace("\"to\":\"inspector\"", "\"to\":\"somebody\"")).unwrap_err().contains("role code"));
    }

    #[test]
    fn a_sentence_one_word_per_entry_is_refused() {
        let bad = READY.replace("[\"hooks\"]", "[\"path\",\"uses\",\"backslashes\",\"on\",\"windows\"]");
        assert!(validate(&bad).unwrap_err().contains("not a top-level folder"));
        assert!(validate(&READY.replace("[\"hooks\"]", "[\"hooks\",\"scripts\",\"database\"]")).is_ok());
        assert!(validate(&READY.replace("[\"hooks\"]", "[]")).is_ok());
    }

    #[test]
    fn a_folder_or_file_name_becomes_a_code() {
        assert_eq!(thing_code("CHANGELOG.md"), "changelog-md");
        assert_eq!(thing_code("Claude Code"), "claude-code");
        assert_eq!(thing_code(".github"), "github");
    }

    #[test]
    fn the_id_is_from_job_and_a_number() {
        assert!(validate(&READY.replace("builder-a-lean-rebuild-1", "builder-a-lean-rebuild-one")).is_err());
        assert!(validate(&READY.replace("builder-a-lean-rebuild-1", "x-1")).is_err());
        assert!(validate(&READY.replace("builder-a-lean-rebuild-1", "builder-a-other-job-1")).is_err());
    }

    #[test]
    fn an_unknown_key_is_refused() {
        assert!(validate(&READY.replace("\"v\":1,", "\"v\":1,\"memo\":\"hi\",")).unwrap_err().contains("unknown key"));
    }

    #[test]
    fn need_comes_from_a_set_list() {
        assert!(validate(&READY.replace("pass_or_fail", "ok")).is_err());
        assert!(validate(&READY.replace("pass_or_fail", "none")).is_ok());
    }

    #[test]
    fn a_ready_needs_its_numbers() {
        assert!(validate(&READY.replace("\"tests\":{\"passed\":48,\"failed\":0},", "")).is_err());
        assert!(validate(&READY.replace("48", "0")).is_err());
        assert!(validate(&READY.replace("\"sha\":\"d082303\",", "")).is_err());
        assert!(validate(&READY.replace(",\"usage\":{\"week_pct\":null}", "")).is_err());
        assert!(validate(&READY.replace("0.3.49", "next")).is_err());
    }

    #[test]
    fn an_order_refers_to_his_words_by_number() {
        let o = r#"{"v":1,"kind":"ORDER","id":"manager-lean-rebuild-1","job":"lean-rebuild","from":"manager","to":"builder-a","owner_words":{"item":34},"owns":["hooks","agents"],"out":["pinr-files"],"action":"hold","need":"none"}"#;
        assert_eq!(validate(o), Ok(()));
        assert!(validate(&o.replace("{\"item\":34}", "\"Lean rebuild\"")).is_err());
        assert!(validate(&o.replace("\"item\":34", "\"decision\":\"D-027\"")).is_ok());
        assert!(validate(&o.replace("\"item\":34", "\"decision\":\"27\"")).is_err());
    }

    #[test]
    fn an_order_carries_an_action_from_the_set() {
        let o = r#"{"v":1,"kind":"ORDER","id":"manager-x-1","job":"x","from":"manager","to":"builder-a","owner_words":{"item":39},"owns":[],"out":[],"action":"ship","need":"order"}"#;
        for a in ["ship", "hold", "start"] { assert_eq!(validate(&o.replace("ship", a)), Ok(())); }
        assert!(validate(&o.replace(",\"action\":\"ship\"", "")).is_err());
        assert!(validate(&o.replace("\"ship\"", "\"go\"")).is_err());
        assert!(validate(&o.replace("\"ship\"", "\"ship now\"")).is_err());
        let p = r#"{"v":1,"kind":"PASS","id":"inspector-x-1","job":"x","from":"inspector","to":"builder-a","sha":"d082303","action":"ship","need":"none"}"#;
        assert!(validate(p).is_err());
    }

    #[test]
    fn a_pass_names_what_it_checked() {
        let p = r#"{"v":1,"kind":"PASS","id":"inspector-lean-rebuild-1","job":"lean-rebuild","from":"inspector","to":"builder-a","sha":"d082303","need":"none"}"#;
        assert_eq!(validate(p), Ok(()));
        assert!(validate(&p.replace("\"sha\":\"d082303\",", "")).is_err());
    }

    #[test]
    fn a_note_is_free_text_with_a_length_cap_and_no_secrets() {
        let n = |s: &str| READY.replacen("{\"v\":1,", &format!("{{\"v\":1,\"note\":\"{s}\","), 1);
        assert_eq!(validate(&n("Handover done: archive the old chats and read the new board.")), Ok(()));
        assert!(validate(&n(&"x".repeat(401))).is_err());
        assert!(validate(&n(&"x".repeat(400))).is_ok());
        assert!(validate(&n("token = abc")).is_err());
        assert!(validate(&n("")).is_err());
        assert!(validate(&n("line one\\nline two")).is_err());
        assert!(validate(&READY.replacen("{\"v\":1,", "{\"v\":1,\"memo\":\"hi\",", 1)).is_err());
    }
}
