//! Stop check for crew chats: a reply to the owner names no bare file path and no saved-version code (port of hooks/talk-check.py).
use crate::common::*;
use serde_json::Value;

pub fn run() -> i32 {
    let Some(data) = read_stdin() else { return 0 };
    if stood_down(&data, "talk-check.py") { return 0; }
    let profile = load_profile();
    if data.get("stop_hook_active").and_then(Value::as_bool).unwrap_or(false) || profile.get("talk_check") == Some(&Value::Bool(false)) { return 0; }
    let text = s(&data, "last_assistant_message");
    if text.is_empty() { return 0; }
    let link = re(r"\[[^\]]*\]\([^)]*\)");
    let fence = re(r"(?s)```.*?```");
    let path = re(r"(?<![\w./-])(?:/Users/|/home/|[A-Za-z]:\\|(?:[\w.-]+/)+[\w.-]+\.\w{1,5}\b|[\w-]+\.(?:md|py|sh|json|html|yml|yaml|jsx?|tsx?|css|toml)\b)");
    let hex = re(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b");
    let body = sub(&fence, &sub(&link, text, " "), " ");
    let body = sub(&re(r"https?://\S+"), &body, " ");
    let bad_path = find(&path, &body).map(|m| m.as_str().to_string());
    let bad_hex = find(&hex, &body).map(|m| m.as_str().to_string());
    if bad_path.is_none() && bad_hex.is_none() { return 0; }
    if !is(&crew_re(&profile), &first_message(s(&data, "transcript_path"))) { return 0; }
    let what = match (&bad_path, &bad_hex) {
        (Some(p), _) => format!("a bare file path or file name (\"{p}\")"),
        (_, Some(h)) => format!("a saved-version code (\"{h}\")"),
        _ => String::new(),
    };
    say(&py_obj(&[("decision", "block".into()), ("reason", format!("Your reply to the owner has {what}. Say it again in plain words with each file as a clickable link and no saved-version codes."))]));
    0
}

pub const ROLE: &str = r"(?:Manager|Builder [A-Za-z]|Designer|Design Inspector|Inspector|Sketchpad|AI Socket|Agent Teacher)";

/// A chat is a crew chat if its first message names agents/<role>.md or a <Role>_<project>_<digits> name (plus a profile's names).
pub fn crew_re(profile: &Value) -> fancy_regex::Regex {
    let mut p = format!(r"agents[/\\](?:manager|builder|designer|inspector|design-inspector|sketchpad|ai-socket|agent-teacher)\.md|\b{ROLE}_[^\s_][^_\n]*_\d{{3}}\b");
    for x in pstrings(profile, "crew_names") { p.push_str(&format!("|(?:{x})")); }
    re(&p)
}
