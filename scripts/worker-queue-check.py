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

Line-style boards (PINR's profile: "board_style": "lines", "board": path relative to the folder that holds
.muster-checks, the installed copy beside profile.json; or MUSTER_PROFILE): lines look like
"date | KIND | from -> to | text. Action: start". There the worker is not found by its folder (workers share one folder)
but by its name in the chat's first message: the longest board name that message contains. Open work = a RULE, NEED,
READY, ORDER or FAIL line "-> <worker>" with Action start or ship, after the worker's own last DONE, PASS, FAIL,
READY or STUCK line (a report closes everything before it; nothing here names a job). The stop is allowed when the
reply names the line's sender or one of its first words. Muster's own board is unchanged.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_profile():
    for cand in (os.environ.get("MUSTER_PROFILE"), os.path.join(HERE, "profile.json")):
        if cand and os.path.isfile(cand):
            try:
                d = json.load(open(cand, encoding="utf-8"))
                return d if isinstance(d, dict) else {}
            except (OSError, ValueError):
                return {}
    return {}


PROFILE = load_profile()
LINE_RE = re.compile(r"^(\S+)\s*\|\s*([A-Za-z]+)\s*\|\s*(.*?)\s*->\s*(.*?)\s*\|\s*(.*)$")


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


def pick_name(first, names):
    """The chat's own name: the board name right after "You are", else the board name that appears earliest in the
    first message (the longest if two start at the same place). Never a neighbour named later (manager, inspector)."""
    low = first.lower()
    for n in sorted(names, key=len, reverse=True):
        if re.search(r"you are\s+(?:the\s+)?" + re.escape(n.lower()), low):
            return n
    hits = [(low.find(n.lower()), -len(n), n) for n in names if n.lower() in low]
    return min(hits)[2] if hits else ""


def line_open_work(board_text, name):
    """[(label, [keys])] for a line-style board; see the module note."""
    rows = []
    for ln in board_text.splitlines():
        m = LINE_RE.match(ln.strip())
        if m:
            rows.append((m.group(2).upper(), m.group(3).strip(), [x.strip() for x in m.group(4).split(",")], m.group(5)))
    mine = [i for i, (k, f, to, t) in enumerate(rows) if f.lower() == name.lower() and k in ("DONE", "PASS", "FAIL", "READY", "STUCK")]
    start = mine[-1] + 1 if mine else 0
    out = []
    for k, f, to, t in rows[start:]:
        if k in ("RULE", "NEED", "READY", "ORDER", "FAIL") and any(x.lower() == name.lower() for x in to) \
                and re.search(r"Action:\s*(start|ship)\b", t, re.I):
            words = [w.lower() for w in re.findall(r"[A-Za-z]{5,}", t)[:3]]
            out.append(("%s from %s: %s" % (k, f, t[:60]), [f] + words))
    return out


def line_names(board_text):
    names = set()
    for ln in board_text.splitlines():
        m = LINE_RE.match(ln.strip())
        if m:
            names.add(m.group(3).strip())
            names.update(x.strip() for x in m.group(4).split(","))
    return {n for n in names if "_" in n}


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


def main_lines(argv, cwd):
    """Line-style board (PINR): the worker is named in the chat's first message."""
    root = os.path.dirname(HERE) if os.path.basename(HERE) == ".muster-checks" else cwd
    board = read(os.path.join(root, PROFILE["board"]))
    if not board:
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}") if "--list" not in argv else {}
    except ValueError:
        return 0
    if "--list" in argv:
        name = argv[argv.index("--worker") + 1] if "--worker" in argv else ""
    else:
        first = first_message(data.get("transcript_path") or "")
        name = pick_name(first, line_names(board))
    if not name or re.search(r"\bManager_", name):
        return 0
    work = line_open_work(board, name)
    if "--list" in argv:
        print("%s: %s" % (name, "; ".join(l for l, _ in work) or "nothing open"))
        return 0
    if data.get("stop_hook_active") or not work:
        return 0
    msg = last_message(data).lower()
    missing = [l for l, keys in work if not any(k.lower() in msg for k in keys)]
    if not missing:
        return 0
    print(json.dumps({"decision": "block", "reason":
        "Do not go idle: open work is addressed to you (%s). Do it now, or if you are waiting, say in your reply what you are "
        "waiting for and name who gave it. If it is not yours, tell the manager." % "; ".join(missing)}))
    return 0


def main(argv):
    cwd = os.getcwd()
    if PROFILE.get("board_style") == "lines" and PROFILE.get("board"):
        return main_lines(argv, cwd)
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
