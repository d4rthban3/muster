#!/usr/bin/env python3
"""Turn-start news from the other computer (owner's list item 133, PINR rule 22).

Run as a UserPromptSubmit hook. On a project that names a second computer, prints the other computer's new
CHANGES.md lines the first time each chat sees them, so no chat starts a turn without them (CLAUDE.md section 9c:
"read the other computer's log first").

Off by default: it prints nothing and reads nothing unless the project has `muster/computers.txt` naming two computers.
That file is one line per computer:   <computer name> = <path to its CHANGES.md>
A path is relative to the project folder (the one that holds muster/); `..` and absolute paths work. `#` starts a comment.
This computer is the line whose name is this computer's git user name or login name (or MUSTER_COMPUTER, if set);
the other line is the log it reads. If it cannot tell which line is this computer, it prints nothing.

Seen mark per chat: ~/.claude/muster-seen/<chat id>.json (MUSTER_SEEN_DIR overrides), outside git, one number per log:
how many lines the chat has seen. A chat's first turn shows the newest lines (capped); after that only added lines.
Output is capped (MUSTER_CHANGES_CAP lines, default 12, newest kept; it says how many were left out).

Reads only. Never writes the log, never fails or blocks a turn: any trouble at all ends silently with exit 0.
"""
import getpass
import hashlib
import json
import os
import subprocess
import sys

CAP = 12


def project_root(start):
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, "muster", "computers.txt")):
            return d
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up


def read_computers(root):
    out = []
    with open(os.path.join(root, "muster", "computers.txt"), encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if "=" not in line:
                continue
            name, path = (p.strip() for p in line.split("=", 1))
            if name and path:
                out.append((name, path))
    return out


def my_names(root):
    names = set()
    env = os.environ.get("MUSTER_COMPUTER")
    if env:
        return {env.strip().lower()}
    try:
        names.add(getpass.getuser().lower())
    except Exception:
        pass
    try:
        g = subprocess.run(["git", "config", "user.name"], cwd=root, capture_output=True, text=True, timeout=5)
        if g.returncode == 0 and g.stdout.strip():
            names.add(g.stdout.strip().lower())
    except Exception:
        pass
    return names


def main():
    try:
        ev = json.loads(sys.stdin.read() or "{}")
    except Exception:
        ev = {}
    if not isinstance(ev, dict):
        ev = {}
    if ev.get("hook_event_name") not in (None, "UserPromptSubmit"):
        return
    root = project_root(ev.get("cwd") or os.getcwd())
    if not root:
        return
    comps = read_computers(root)
    if len(comps) != 2:
        return
    mine = my_names(root)
    me = [c for c in comps if c[0].lower() in mine]
    if len(me) != 1:
        return
    other = comps[1] if comps[0] is me[0] else comps[0]
    log = other[1] if os.path.isabs(other[1]) else os.path.normpath(os.path.join(root, other[1]))
    with open(log, encoding="utf-8", errors="replace") as f:
        lines = [ln.rstrip("\n") for ln in f.read().splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    total = len(lines)

    sdir = os.environ.get("MUSTER_SEEN_DIR") or os.path.join(os.path.expanduser("~"), ".claude", "muster-seen")
    sid = str(ev.get("session_id") or "no-chat")
    sid = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in sid)[:80] or "no-chat"
    mark_file = os.path.join(sdir, sid + ".json")
    try:
        with open(mark_file, encoding="utf-8") as f:
            marks = json.load(f)
        if not isinstance(marks, dict):
            marks = {}
    except Exception:
        marks = {}
    key = hashlib.sha1(os.path.abspath(log).encode("utf-8")).hexdigest()[:12]
    seen = marks.get(key)
    if not isinstance(seen, int) or seen < 0:
        seen = None

    if seen is not None and seen > total:
        new = []  # the log got shorter (rewritten): nothing counts as new; the mark catches up
    elif seen is None:
        new = [ln for ln in lines if ln.strip()]
    else:
        new = [ln for ln in lines[seen:] if ln.strip()]

    marks[key] = total
    try:
        os.makedirs(sdir, exist_ok=True)
        tmp = mark_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(marks, f)
        os.replace(tmp, mark_file)
    except Exception:
        pass  # no mark kept: the lines show again next turn, which is better than losing them

    if not new:
        return
    try:
        cap = max(1, int(os.environ.get("MUSTER_CHANGES_CAP") or CAP))
    except Exception:
        cap = CAP
    left = max(0, len(new) - cap)
    shown = new[-cap:]
    head = "Muster: %s's log has %d new line%s since you last looked (read it, never write it): %s" % (
        other[0], len(new), "" if len(new) == 1 else "s", log)
    out = [head]
    if left:
        out.append("(%d earlier line%s not shown; open the log for them)" % (left, "" if left == 1 else "s"))
    out.extend(shown)
    print("\n".join(out))


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass
    sys.exit(0)
