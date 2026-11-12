#!/usr/bin/env python3
"""Stop hook for the manager's chat: do not let the manager end a turn while the board holds an open question
for the owner that the manager's last message does not name.

Fires only in the manager's own chat (its first message names agents/manager.md or Manager_<project>_<digits>).
Self-contained on purpose: a project that does not use the plugin can copy just this one file.
Reads the hook's JSON from standard input. Reads only muster/BOARD.md in the session's own folder. Writes nothing,
sends nothing. Silent (exit 0, no output) when the board is clean, in a worker's copy, or on any error.
It blocks at most once per stop: when Claude Code is already continuing because of a stop hook
(stop_hook_active), it lets the stop through, so it can never loop.
"""
import json
import os
import re
import sys


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

MANAGER_RE = re.compile(r"agents[/\\]manager\.md|\bManager_[^_\n]*_\d{3}\b")
if PROFILE.get("manager_names"):
    MANAGER_RE = re.compile(MANAGER_RE.pattern + "|" + "|".join("(?:%s)" % x for x in PROFILE["manager_names"]))


HANDLED = ("done", "closed", "routed", "handled", "answered", "forwarded")


def entries(text):
    out, cur, fenced = [], None, False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            if cur is not None:
                cur["body"].append(line)
            continue
        if fenced:
            if cur is not None:
                cur["body"].append(line)
            continue
        if re.match(r"^\s*###\s", line):
            if cur:
                out.append(cur)
            parts = [p.strip(" #`") for p in line.split("|")]
            frm = re.sub(r"\s*->.*", "", parts[2]) if len(parts) > 2 else ""
            cur = {"kind": parts[1].upper() if len(parts) > 1 else "", "from": frm,
                   "job": parts[3] if len(parts) > 3 else "", "status": "open", "paused": False, "resumed": False, "body": []}
        elif cur is not None:
            cur["body"].append(line)
            m = re.match(r"^\s*status\s*:\s*([A-Za-z]+)", line, re.I)
            if m:
                cur["status"] = m.group(1).lower()
            if re.match(r"^\s*paused\s*:\s*yes", line, re.I):
                cur["paused"] = True
            if re.match(r"^\s*paused\s*:\s*no", line, re.I):
                cur["resumed"] = True
    if cur:
        out.append(cur)
    return out


def line_entries(text):
    """A board whose entries are single lines: 'DATE | KIND | from -> to | text' (PINR). No Status line exists, so an entry is
    never 'done'; entries are in file order (oldest first, new ones appended), and a chat is paused by its LAST entry saying 'Paused: yes'."""
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s*\d{4}-\d\d-\d\d\s*\|\s*([A-Za-z ]+?)\s*\|\s*([^|]*?)\s*\|\s*(.*)$", line)
        if not m:
            continue
        frm = re.sub(r"\s*->.*", "", m.group(2))
        out.append({"kind": m.group(1).upper(), "from": frm, "job": "", "status": "open",
                    "paused": bool(re.search(r"\bpaused\s*:\s*yes", line, re.I)),
                    "resumed": bool(re.search(r"\bpaused\s*:\s*no", line, re.I)), "body": [line]})
    return out


def is_manager_chat(transcript_path):
    """True only if the chat's FIRST user message names the manager's definition or a Manager_<project>_<digits> chat.
    The owner's own chats in the same folder, and any worker, do not. Unreadable means no (stay silent)."""
    try:
        with open(transcript_path, encoding="utf-8") as fh:
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
                c = str(c)[:6000]
                return bool(MANAGER_RE.search(c))
    except OSError:
        pass
    return False


PICKS = re.compile(r"fits what you want|fits what you said|i'?m recording|i am recording|i'?ll record|i will record|"
                   r"i went with|i'?ll go with|i will go with|i'?m going with|i am going with|i picked|i chose|i'?ve chosen|"
                   r"i have chosen|so [a-d] (fits|it is)|recording (it|that|this) as", re.I)
TOLD = re.compile(r"you (picked|chose|clicked|selected)", re.I)


def card_answered_this_turn(transcript_path):
    """True if an AskUserQuestion card was asked after the owner's last typed message (so its answer came this turn).
    Unknown (not found in the last 3 MB) counts as True: never block on a guess."""
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as fh:
            fh.seek(max(0, size - 3000000))
            raw = fh.read().decode("utf-8", "replace").split("\n")
    except OSError:
        return True
    last_human, card_after = None, False
    for line in raw:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        msg = d.get("message") or {}
        c = msg.get("content", "")
        if d.get("type") == "user":
            human = isinstance(c, str) or (isinstance(c, list) and any(
                isinstance(b, dict) and b.get("type") == "text" for b in c))
            if human:
                last_human, card_after = True, False
        elif d.get("type") == "assistant" and isinstance(c, list):
            if any(isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "AskUserQuestion" for b in c):
                card_after = True
    return True if last_human is None else card_after


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
    if data.get("stop_hook_active") or bounced_this_turn(data.get("transcript_path") or ""):
        return 0
    if os.environ.get("MUSTER_ASSUME_MANAGER") != "1" and not is_manager_chat(data.get("transcript_path") or ""):
        return 0  # the owner's own chat, or a worker: never nag it
    cwd = data.get("cwd") or os.getcwd()
    cwd = os.path.abspath(cwd)
    if "worktrees" in cwd.replace("\\", "/").split("/"):
        return 0  # a worker's own copy, not the manager's folder
    path = os.path.join(cwd, "muster", "BOARD.md")
    if PROFILE.get("board"):  # relative to the project folder that holds .muster-checks
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), PROFILE["board"])
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, encoding="utf-8") as fh:
            items = line_entries(fh.read()) if PROFILE.get("board_style") == "lines" else entries(fh.read())
    except OSError:
        return 0
    said = (data.get("last_assistant_message") or "").lower()
    # fallback for a worker that cannot write the main board: a .muster-paused file in its own folder copy
    import glob
    for p in sorted(glob.glob(os.path.join(cwd, ".claude", "worktrees", "*", ".muster-paused"))):
        who = os.path.basename(os.path.dirname(p))
        try:
            with open(p, encoding="utf-8") as fh:
                who = fh.readline().strip() or who
        except OSError:
            pass
        items.append({"kind": "", "from": who, "job": "", "status": "open", "paused": True, "resumed": False, "body": []})
    missed = []
    kinds_open = PROFILE.get("board_kinds_open", True)
    # a chat is paused NOW only if its LAST entry on the board says "Paused: yes" and is open: a later entry from the
    # same chat, "Paused: no", or Status done clears it (the owner typed in the chat and it carried on)
    last = {}
    for i, e in enumerate(items):
        last[e["from"]] = i
    for i, e in enumerate(items):
        if e["paused"] and (e["resumed"] or last[e["from"]] != i):
            e["paused"] = False
            if e["kind"] not in ("NEED", "STUCK", "OWNER CALL"):
                continue
        if e["status"] in HANDLED:
            continue
        # routed: a LATER entry written by the manager on the same job counts as handled (it answered or passed the item on),
        # so the same waiting line is not demanded again (item 59)
        if e["job"] and any(x["from"].lower().startswith("manager") and x["job"].lower() == e["job"].lower() for x in items[i + 1:]):
            continue
        if not (e["paused"] or (kinds_open and e["kind"] in ("NEED", "STUCK", "OWNER CALL"))):
            continue
        if (e["from"] and e["from"].lower() in said) or (e["job"] and e["job"].lower() in said):
            continue
        missed.append(e)
    picks = bool(PICKS.search(said)) and not TOLD.search(said) and not card_answered_this_turn(data.get("transcript_path") or "")
    if not missed and not picks:
        return 0
    if picks and not missed:
        print(json.dumps({"decision": "block", "reason": "You wrote that you are choosing or recording for the owner, but he "
                          "has not picked this turn. Do not decide for him: ask him now with a choice card, the option you "
                          "favour marked \"my pick\", and record nothing until he clicks."}))
        return 0
    names = "; ".join("%s (%s)" % (e["from"] or "a worker", "paused" if e["paused"] else e["kind"]) for e in missed)
    reason = ("The board holds open items for the owner that you have not told him about: %s. "
              "Before you stop, ask him the top one as a choice card, or say \"<worker> is waiting for you: "
              "type in <chat link>\" for a paused chat; then stop." % names)
    if picks:
        reason += (" Also: you wrote that you are choosing or recording for the owner, but he has not picked this turn; "
                   "ask him with a choice card, the option you favour marked \"my pick\", and record nothing until he clicks.")
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
