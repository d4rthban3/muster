#!/usr/bin/env python3
"""PreCompact hook (D-039, item 105): a crew chat that is about to compact in place leaves one record on the board first: which chat, its open
job, its branch, its saved version and its next step, so the summary can lose detail without the crew losing the thread. Status: done, so it
asks nobody to act. Silent for any other chat (the owner's own chats, another project) and in a project with no muster/BOARD.md.
Reads the hook's JSON from stdin, the chat's transcript, and git; appends one entry to muster/BOARD.md of the main folder. Never blocks
the compaction: any error means silence and exit 0. The job and next step are read from the chat's own last messages (best effort)."""
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))


def crew_helper():
    spec = importlib.util.spec_from_file_location("renew_after_summary", os.path.join(HERE, "renew-after-summary.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(cwd, *args):
    try:
        r = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def main_folder(cwd):
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common.endswith(".git"):
        return os.path.dirname(common)
    return cwd


def last_facts(path):
    """The last job name and the last note this chat sent or received, from its own transcript."""
    job = note = ""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if "job" not in line and "note" not in line:
                    continue
                for m in re.finditer(r'\\?"job\\?":\s*\\?"([^"\\]{1,60})', line):
                    job = m.group(1)
                for m in re.finditer(r'\\?"note\\?":\s*\\?"([^"\\]{1,240})', line):
                    note = m.group(1)
    except OSError:
        pass
    return job, note


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except Exception:
        return 0
    h = crew_helper()
    path = data.get("transcript_path") or ""
    first = h.first_message(path)
    name = h.CHAT_NAME.search(first)
    role = h.ROLE_FILE.search(first)
    in_profile = any(p.search(first) for p in h.PROFILE_CREW)
    if not name and not role and not in_profile:
        return 0
    pm = next((m for m in (p.search(first) for p in h.PROFILE_CREW) if m), None)
    who = name.group(0) if name else (pm.group(0) if pm else (role.group(1) if role else "a crew chat"))
    cwd = data.get("cwd") or os.getcwd()
    board = os.path.join(main_folder(cwd), "muster", "BOARD.md")
    if not os.path.isfile(board):
        return 0
    branch = git(cwd, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    sha = git(cwd, "rev-parse", "--short", "HEAD") or "unknown"
    job, note = last_facts(path)
    now = datetime.datetime.now()
    slug = re.sub(r"[^a-z0-9]+", "-", who.lower()).strip("-")
    entry = ("\n### %s | DONE | %s -> Manager | compaction\nStatus: done\nDONE: compacted in place [ID compact-%s-%s]\n"
             "What:  this chat is compacting in place (D-039); it carries on, no renewal.\n"
             "Where: open job %s; branch %s at %s.\n"
             "Why:   the chat reached its size line (compact window, item 105).\n"
             "How:   next step, from its last message: %s\n"
             "Need:  none\n") % (now.strftime("%Y-%m-%d"), who, slug, now.strftime("%H%M%S"),
                                job or "none named in its last messages", branch, sha, note or "read its summary and the board entries addressed to it")
    with open(board, "a", encoding="utf-8") as fh:
        fh.write(entry)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
