#!/usr/bin/env python3
"""Cursor `stop` hook for the manager's agent. UNTESTED in Cursor (written from its hooks docs).

Cursor sends the hook JSON on stdin (workspace_roots, transcript_path, loop_count, status). If this is the manager's
agent and the board holds an open NEED, STUCK, OWNER CALL or paused chat that has not been flagged yet, it returns
{"followup_message": "..."} so the manager tells the owner. Each item set is flagged once (muster/.board-nagged), and
a follow-up that is already a follow-up (loop_count > 0) is let through, so it never loops. Silent otherwise.
The board logic is board-stop.py, the same file the Claude Code edition uses (run here with MUSTER_ASSUME_MANAGER=1).
Cursor's transcript format is not documented, so "manager's agent" means: the first 6000 characters of its transcript
name Manager_<project>_<digits> (the starting note does). Any error means silence.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):  # print on any computer, whatever its console encoding
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except Exception:
        print("{}")
        return 0
    if data.get("loop_count"):
        print("{}")
        return 0
    roots = data.get("workspace_roots") or []
    root = roots[0] if roots else os.getcwd()
    tp = data.get("transcript_path") or ""
    try:
        with open(tp, encoding="utf-8", errors="replace") as fh:
            head = fh.read(6000)
    except OSError:
        head = ""
    if not re.search(r"\bManager_[^\s_][^_\n]*_\d{3}\b", head):
        print("{}")
        return 0
    here = os.path.dirname(os.path.abspath(__file__))
    env = dict(os.environ, MUSTER_ASSUME_MANAGER="1")
    out = subprocess.run([sys.executable, os.path.join(here, "board-stop.py")], input=json.dumps(
        {"cwd": root, "stop_hook_active": False, "last_assistant_message": ""}),
        capture_output=True, text=True, env=env, timeout=20).stdout.strip()
    try:
        reason = json.loads(out)["reason"]
    except Exception:
        print("{}")
        return 0
    mark = os.path.join(root, "muster", ".board-nagged")
    key = hashlib.sha1(re.sub(r"\s+", " ", reason).encode("utf-8")).hexdigest()
    try:
        seen = open(mark, encoding="utf-8").read().split()
    except OSError:
        seen = []
    if key in seen:
        print("{}")
        return 0
    with open(mark, "w", encoding="utf-8") as fh:
        fh.write("\n".join((seen + [key])[-50:]))
    print(json.dumps({"followup_message": reason}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("{}")
        sys.exit(0)
