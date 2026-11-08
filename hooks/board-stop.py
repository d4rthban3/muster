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
                   "job": parts[3] if len(parts) > 3 else "", "status": "open", "paused": False, "body": []}
        elif cur is not None:
            cur["body"].append(line)
            m = re.match(r"^\s*status\s*:\s*([A-Za-z]+)", line, re.I)
            if m:
                cur["status"] = m.group(1).lower()
            if re.match(r"^\s*paused\s*:\s*yes", line, re.I):
                cur["paused"] = True
    if cur:
        out.append(cur)
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
                return bool(re.search(r"agents[/\\]manager\.md|\bManager_[A-Za-z0-9 ]*_\d{3}\b", c))
    except OSError:
        pass
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("stop_hook_active"):
        return 0
    if not is_manager_chat(data.get("transcript_path") or ""):
        return 0  # the owner's own chat, or a worker: never nag it
    cwd = data.get("cwd") or os.getcwd()
    cwd = os.path.abspath(cwd)
    if "worktrees" in cwd.replace("\\", "/").split("/"):
        return 0  # a worker's own copy, not the manager's folder
    path = os.path.join(cwd, "muster", "BOARD.md")
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, encoding="utf-8") as fh:
            items = entries(fh.read())
    except OSError:
        return 0
    said = (data.get("last_assistant_message") or "").lower()
    missed = []
    for e in items:
        if e["status"] in ("done", "closed"):
            continue
        if not (e["paused"] or e["kind"] in ("NEED", "STUCK", "OWNER CALL")):
            continue
        if (e["from"] and e["from"].lower() in said) or (e["job"] and e["job"].lower() in said):
            continue
        missed.append(e)
    if not missed:
        return 0
    names = "; ".join("%s (%s)" % (e["from"] or "a worker", "paused" if e["paused"] else e["kind"]) for e in missed)
    reason = ("The board holds open items for the owner that you have not told him about: %s. "
              "Before you stop, ask him the top one as a choice card, or say \"<worker> is waiting for you: "
              "type in <chat link>\" for a paused chat; then stop." % names)
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
