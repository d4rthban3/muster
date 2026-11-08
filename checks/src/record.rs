//! A worker-to-worker message is a data record, never a sentence (owner's list item 34: "Data fields only").
//! It is one JSON object with fixed keys; every value is a number, a version, a short code from a set list, or a list of codes.
//! A value that holds a space, or any key that is not listed, is refused: there is no room for English in a record.
use serde_json::{Map, Value};

const KINDS: [&str; 8] = ["READY", "DONE", "PASS", "FAIL", "STUCK", "NEED", "OWNER_CALL", "ORDER"];
const NEEDS: [&str; 6] = ["none", "pass_or_fail", "order", "owner_answer", "fix", "unblock"];
const DONE_WHEN: [&str; 4] = ["ready", "pass", "live", "report"];
const KEYS: [&str; 15] = [
    "v", "kind", "id", "job", "from", "to", "sha", "version", "tests", "touches", "need", "usage", "owner_words", "owns", "out",
];

fn code(v: &Value, what: &str, lo: usize, hi: usize) -> Result<String, String> {
    let s = v.as_str().ok_or_else(|| format!("{what} must be a code (text without spaces)"))?;
    let ok = s.len() >= lo
        && s.len() <= hi
        && s.chars().all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-' || c == '_');
    if ok { Ok(s.to_string()) } else { Err(format!("{what} must be {lo}-{hi} characters of a-z, 0-9, - or _ (no spaces, no sentences)")) }
}

fn list_of_codes(v: &Value, what: &str) -> Result<(), String> {
    let a = v.as_array().ok_or_else(|| format!("{what} must be a list of codes"))?;
    if a.len() > 32 { return Err(format!("{what} holds more than 32 codes")); }
    for x in a { code(x, what, 1, 64)?; }
    Ok(())
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

fn opt<'a>(m: &'a Map<String, Value>, k: &str) -> Option<&'a Value> {
    m.get(k).filter(|v| !v.is_null())
}

/// Ok(()) when the text is one valid record; Err(why) otherwise.
pub fn validate(text: &str) -> Result<(), String> {
    let v: Value = serde_json::from_str(text.trim()).map_err(|_| "not a record: it must be one JSON object (data, not a sentence)".to_string())?;
    let m = v.as_object().ok_or("not a record: it must be one JSON object")?;
    for k in m.keys() {
        if !KEYS.contains(&k.as_str()) { return Err(format!("unknown key '{k}'")); }
    }
    if m.get("v").and_then(Value::as_u64) != Some(1) { return Err("v must be 1".into()); }
    let kind = m.get("kind").and_then(Value::as_str).ok_or("kind is missing")?;
    if !KINDS.contains(&kind) { return Err(format!("kind '{kind}' is not one of {}", KINDS.join(", "))); }
    for k in ["id", "job", "from", "to"] {
        code(m.get(k).ok_or_else(|| format!("{k} is missing"))?, k, 1, 64)?;
    }
    let need = m.get("need").ok_or("need is missing")?;
    let need = code(need, "need", 1, 20)?;
    if !NEEDS.contains(&need.as_str()) { return Err(format!("need '{need}' is not one of {}", NEEDS.join(", "))); }
    if let Some(x) = opt(m, "sha") { sha(x)?; }
    if let Some(x) = opt(m, "version") { version(x)?; }
    if let Some(t) = opt(m, "tests") {
        let o = t.as_object().ok_or("tests must be {\"passed\":n,\"failed\":n}")?;
        if o.len() != 2 { return Err("tests must hold exactly passed and failed".into()); }
        num(o.get("passed").ok_or("tests.passed is missing")?, "tests.passed", 1_000_000)?;
        num(o.get("failed").ok_or("tests.failed is missing")?, "tests.failed", 1_000_000)?;
    }
    if let Some(x) = m.get("touches") { list_of_codes(x, "touches")?; }
    if let Some(u) = opt(m, "usage") {
        let o = u.as_object().ok_or("usage must be {\"week_pct\":n}")?;
        if o.len() != 1 { return Err("usage must hold exactly week_pct".into()); }
        match o.get("week_pct") { Some(Value::Null) => {}, Some(x) => { num(x, "usage.week_pct", 100)?; }, None => return Err("usage.week_pct is missing".into()) }
    }
    match kind {
        "READY" => {
            if opt(m, "sha").is_none() { return Err("a READY needs sha".into()); }
            let t = opt(m, "tests").ok_or("a READY needs tests")?;
            if t["passed"].as_u64() == Some(0) && t["failed"].as_u64() == Some(0) { return Err("a READY needs a test count above zero".into()); }
            if m.get("touches").is_none() { return Err("a READY needs touches (a list, empty if none)".into()); }
            if !m.contains_key("usage") { return Err("a READY needs usage".into()); }
        }
        "DONE" => { if !m.contains_key("usage") { return Err("a DONE needs usage".into()); } }
        "PASS" | "FAIL" => { if opt(m, "sha").is_none() { return Err(format!("a {kind} needs the sha it checked")); } }
        "ORDER" => {
            let ow = m.get("owner_words").ok_or("an ORDER needs owner_words (his list item or decision)")?;
            let o = ow.as_object().ok_or("owner_words must be {\"item\":n} or {\"decision\":\"D-027\"}")?;
            if o.len() != 1 { return Err("owner_words must hold exactly one of item or decision".into()); }
            match (o.get("item"), o.get("decision")) {
                (Some(i), None) => { num(i, "owner_words.item", 10_000)?; }
                (None, Some(d)) => {
                    let s = d.as_str().unwrap_or("");
                    if !(s.len() == 5 && s.starts_with("D-") && s[2..].chars().all(|c| c.is_ascii_digit())) { return Err("owner_words.decision must look like D-027".into()); }
                }
                _ => return Err("owner_words must be item or decision".into()),
            }
            list_of_codes(m.get("owns").ok_or("an ORDER needs owns")?, "owns")?;
            list_of_codes(m.get("out").ok_or("an ORDER needs out")?, "out")?;
            let dw = m.get("need").and_then(Value::as_str).unwrap_or("");
            let _ = (dw, DONE_WHEN);
        }
        _ => {}
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::validate;

    const READY: &str = r#"{"v":1,"kind":"READY","id":"builder-a-lean-1","job":"lean-rebuild","from":"builder-a","to":"inspector","sha":"d082303","version":"0.3.49","tests":{"passed":48,"failed":0},"touches":["hooks"],"need":"pass_or_fail","usage":{"week_pct":null}}"#;

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
    fn an_unknown_key_is_refused() {
        assert!(validate(&READY.replace("\"v\":1,", "\"v\":1,\"note\":\"hi\",")).unwrap_err().contains("unknown key"));
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
        let o = r#"{"v":1,"kind":"ORDER","id":"manager-lean-1","job":"lean-rebuild","from":"manager","to":"builder-a","owner_words":{"item":34},"owns":["hooks","agents"],"out":["pinr-files"],"need":"none"}"#;
        assert_eq!(validate(o), Ok(()));
        assert!(validate(&o.replace("{\"item\":34}", "\"Lean rebuild\"")).is_err());
        assert!(validate(&o.replace("\"item\":34", "\"decision\":\"D-027\"")).is_ok());
        assert!(validate(&o.replace("\"item\":34", "\"decision\":\"27\"")).is_err());
    }

    #[test]
    fn a_pass_names_what_it_checked() {
        let p = r#"{"v":1,"kind":"PASS","id":"inspector-lean-1","job":"lean-rebuild","from":"inspector","to":"builder-a","sha":"d082303","need":"none"}"#;
        assert_eq!(validate(p), Ok(()));
        assert!(validate(&p.replace("\"sha\":\"d082303\",", "")).is_err());
    }
}
