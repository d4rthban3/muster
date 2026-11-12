#!/usr/bin/env python3
"""Stop hook for crew chats: flag, once, a reply that names a file as a bare path or file name (not a link) or carries a
saved-version code (a long hex word), because the owner reads these replies (muster/CLAUDE.md section 4).
Acts only in a crew chat (the first user message in the transcript names agents/<role>.md or <Role>_<project>_<digits>);
silent for the owner's own chats and any other project. Blocks at most once: with stop_hook_active it lets the stop through.
Reads only the hook JSON and the transcript's first message; writes nothing; any error means silence.
"""
import json
import os
import re
import sys

CREW = r"(?:Manager|Builder [A-Za-z]|Designer|Design Inspector|Inspector|Sketchpad|AI Socket|Agent Teacher)"
CREW_RE = re.compile(r"agents[/\\](?:manager|builder|designer|inspector|design-inspector|sketchpad|ai-socket|agent-teacher)\.md|\b%s_[^\s_][^_\n]*_\d{3}\b" % CREW)
def load_profile():
    """Optional project profile: profile.json beside this file (or the file named in MUSTER_PROFILE). None means Muster's own rules."""
    for cand in (os.environ.get("MUSTER_PROFILE"), os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile.json")):
        if cand and os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as fh:
                    d = json.load(fh)
                return d if isinstance(d, dict) else {}
            except (OSError, ValueError):
                return {}
    return {}


PROFILE = load_profile()
if PROFILE.get("crew_names"):
    CREW_RE = re.compile(CREW_RE.pattern + "|" + "|".join("(?:%s)" % x for x in PROFILE["crew_names"]))
LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")
FENCE = re.compile(r"```.*?```", re.S)
PATH = re.compile(r"(?<![\w./-])(?:/Users/|/home/|[A-Za-z]:\\|(?:[\w.-]+/)+[\w.-]+\.\w{1,5}\b|[\w-]+\.(?:md|py|sh|json|html|yml|yaml|jsx?|tsx?|css|toml)\b)")
HEX = re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")


def first_message(path):
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") != "user":
                    continue
                c = (d.get("message") or {}).get("content", "")
                if isinstance(c, list):
                    c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                return str(c)[:6000]
    except OSError:
        pass
    return ""


def stood_down(data):
    """The plugin's copy stands down where the project has its own installed copy (.muster-checks/<this file>), so a check never runs twice."""
    me = os.path.abspath(__file__)
    if os.path.basename(os.path.dirname(me)) == ".muster-checks":
        return False
    start = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, ".muster-checks", os.path.basename(me))):
            return True
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent


def bounced_this_turn(path):
    """True when a Stop hook already bounced a reply in this turn (the turn starts at the last message that is not hook feedback);
    a check bounces at most once per turn (item 57)."""
    bounced = False
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") != "user":
                    continue
                c = (d.get("message") or {}).get("content", "")
                if isinstance(c, list):
                    if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                        continue
                    c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                t = str(c).strip()
                if not t:
                    continue
                if t.startswith("Stop hook feedback") or t.startswith("Stop hook blocking error"):
                    bounced = True
                elif not t.startswith("<system-reminder"):
                    bounced = False
    except OSError:
        pass
    return bounced


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except Exception:
        return 0
    if stood_down(data):
        return 0
    if data.get("stop_hook_active") or PROFILE.get("talk_check") is False:
        return 0  # a profile can switch this off where the project runs its own talk check
    text = data.get("last_assistant_message") or ""
    if not text or bounced_this_turn(data.get("transcript_path") or ""):
        return 0
    body = FENCE.sub(" ", LINK.sub(" ", text))
    body = re.sub(r"https?://\S+", " ", body)
    bad_path = PATH.search(body)
    bad_hex = HEX.search(body)
    if not bad_path and not bad_hex:
        return 0
    if not CREW_RE.search(first_message(data.get("transcript_path") or "")):
        return 0  # the owner's own chat or another project
    what = ("a bare file path or file name (\"%s\")" % bad_path.group(0)) if bad_path else ("a saved-version code (\"%s\")" % bad_hex.group(0))
    print(json.dumps({"decision": "block", "reason": "Your reply to the owner has %s. Say it again in plain words with each file as a clickable link and no saved-version codes." % what}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
