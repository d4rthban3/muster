#!/usr/bin/env python3
"""Worker queue check (owner's list item 70: "why do they keep going idle?"): before a worker's turn ends, read the
board and the owner's list for open work addressed to this worker. If there is some and the worker's last message
does not name it, the stop is refused once, so the worker does the work or says what it is waiting for.

Stop hook for a worker's chat (a manager's folder is left to idle-check.py). A worker is found by its own folder: the
"Folder copy" column of muster/CREW.md. The shared files are read from the main project folder (the parent of the git
common dir), never written. Open work = a board ORDER "-> <worker name> | <job>" whose Status is open and that no later PASS or DONE entry names, and an
open owner's-list item whose Stands line starts "with ... <worker name>" (a "standing" item never counts). Allowed through, silently: not a crew worker's
folder, nothing open, the last message names each open job (or item), the hook is already continuing
(stop_hook_active; it never loops), or any error. By hand: python3 scripts/worker-queue-check.py --list [--project DIR]
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def main_folder(cwd):
    try:
        out = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=cwd, capture_output=True, text=True, timeout=10).stdout.strip()
        if out:
            return os.path.dirname(os.path.realpath(os.path.join(cwd, out)))
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def my_name(main, cwd):
    """Crew name whose 'Folder copy' cell names this folder (its last path part)."""
    text = read(os.path.join(main, "muster", "CREW.md"))
    m = re.search(r"## Running now(.*?)(?:\n## |\Z)", text, re.S)
    here = os.path.basename(os.path.realpath(cwd).rstrip("/\\"))
    for line in (m.group(1) if m else "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0] not in ("Name", "") and re.search(r"(?:^|[/\\ ])%s(?:\s|$|\))" % re.escape(here), cells[3]):
            return cells[0]
    return ""


def norm(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def finished(blk, job):
    """True if this board entry is a PASS or DONE for the job (named in its heading or its first line)."""
    h = re.match(r"### \S+ \| (PASS|DONE) \| [^|]*\| (.*)", blk)
    if not h:
        return False
    first = (blk.splitlines() + ["", ""])
    return norm(job) in norm(h.group(2)) or norm(job) in norm(" ".join(first[1:4]).split("What:")[0])


def open_work(main, name):
    """[(label, key)] where key is the text the worker's last message must contain."""
    out = []
    board = read(os.path.join(main, "muster", "BOARD.md"))
    blocks = re.split(r"\n(?=### )", board)
    for i, blk in enumerate(blocks):
        h = re.match(r"### \S+ \| ORDER \| .*? -> ([^|]+?) \| (.*)", blk)
        if h and h.group(1).strip().lower() in (name.lower(), "all") and re.search(r"^Status:\s*open", blk, re.M | re.I):
            if h.group(1).strip().lower() == "all" and name.lower() not in blk.lower():
                continue  # an ALL order counts only if it names this worker
            job = h.group(2).strip()
            if any(finished(b, job) for b in blocks[i + 1:]):
                continue  # a later PASS or DONE names the same job: the order is finished, whatever its Status says
            out.append(("board order \"%s\"" % job, job))
    ol = read(os.path.join(main, "muster", "OWNERS-LIST.md"))
    m = re.search(r"(?:^|\n)## Open\n(.*?)(?:\n## |\Z)", ol, re.S)
    for blk in re.split(r"\n(?=\d+\. )", m.group(1) if m else ""):
        num = re.match(r"(\d+)\. ", blk.strip())
        st = re.search(r"^\s*Stands:\s*(.*)$", blk, re.M)
        if num and st and re.match(r"with\b[^;]*" + re.escape(name), st.group(1), re.I):
            out.append(("owner's list item %s" % num.group(1), "item %s" % num.group(1)))
    return out


def last_message(data):
    m = data.get("last_assistant_message")
    if isinstance(m, str):
        return m
    tp = data.get("transcript_path") or ""
    try:
        with open(tp, "rb") as fh:
            fh.seek(max(0, os.path.getsize(tp) - 200000))
            lines = fh.read().decode("utf-8", "ignore").splitlines()
        for line in reversed(lines):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") == "assistant":
                c = (e.get("message") or {}).get("content")
                return " ".join(b.get("text", "") for b in c if isinstance(b, dict)) if isinstance(c, list) else str(c)
    except OSError:
        pass
    return ""


def main(argv):
    cwd = os.getcwd()
    if "--project" in argv:
        cwd = argv[argv.index("--project") + 1]
    main_dir = main_folder(cwd)
    if not main_dir or not os.path.isfile(os.path.join(main_dir, "muster", "BOARD.md")):
        return 0
    if os.path.realpath(main_dir) == os.path.realpath(cwd):
        return 0  # the manager's own folder: idle-check.py handles it
    name = my_name(main_dir, cwd)
    if not name:
        return 0
    work = open_work(main_dir, name)
    if "--list" in argv:
        print("%s: %s" % (name, "; ".join(l for l, _ in work) or "nothing open"))
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if data.get("stop_hook_active") or not work:
        return 0
    msg = last_message(data).lower()
    missing = [l for l, k in work if k.lower() not in msg]
    if not missing:
        return 0
    print(json.dumps({"decision": "block", "reason":
        "Do not go idle: open work is addressed to you (%s). Do it now (the next piece), or if you are waiting, say in your reply "
        "what you are waiting for and name the job. If it is not yours, send the manager one NEED." % "; ".join(missing)}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:
        sys.exit(0)
