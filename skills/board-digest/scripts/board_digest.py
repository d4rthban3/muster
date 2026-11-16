#!/usr/bin/env python3
"""Print the board entries a role must read, without reading the whole board.

Read-only: reads muster/BOARD.md and muster/BOARD-ARCHIVE.md, writes nothing, no network.

Usage:  python3 board_digest.py <ROLE> [project-dir]
        python3 board_digest.py Manager --mark-asked <job>   (manager only) after asking the owner that job's question, mark its
                                                              open entries "Asked:"; the digest then lists it apart as "waiting on
                                                              his answer, do not re-ask" until he answers (status done/closed) or
                                                              the entry text changes (item 120)

Entry format (see templates/BOARD.md):
    ### <date> | <DONE|READY|PASS|FAIL|STUCK|NEED> | <from> -> <to> | <job name>
    Status: open | done | closed
    ...body...

An entry is printed in full when its header names ROLE or ALL.
Other entries that are not done/closed are printed as headers only.
Anything that cannot be read is reported, never hidden.
"""
import glob
import os
import re
import sys
import time

for _s in (sys.stdout, sys.stderr):  # a project name with accents must print on any computer, whatever its console encoding
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CLOSED = {"done", "closed"}


def find_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(cur, "muster", "BOARD.md")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def parse(text):
    """Split into entries: (header, [lines], status)."""
    entries, cur = [], None
    fenced = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            if cur is not None:
                cur[1].append(line)
            continue
        if fenced:
            if cur is not None:
                cur[1].append(line)
            continue
        if re.match(r"^\s*###\s", line):
            if cur:
                entries.append(cur)
            cur = [line.strip(" `"), [line], "open"]
        elif cur is not None:
            cur[1].append(line)
            m = re.match(r"^\s*status\s*:\s*([A-Za-z]+)", line, re.I)
            if m:
                cur[2] = m.group(1).lower()
    if cur:
        entries.append(cur)
    return entries


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read(), None
    except OSError as err:
        return None, str(err)


ASKED = re.compile(r"^\s*asked\s*:", re.I)


def entry_hash(lines):
    """Short fingerprint of an entry without its Asked line: if the question changes, the mark no longer matches."""
    import hashlib
    body = "\n".join(l.rstrip() for l in lines if not ASKED.match(l)).strip()
    return hashlib.sha1(body.encode("utf-8")).hexdigest()[:8]


def is_asked(lines):
    """True when the entry carries an Asked mark that still matches its text (the question is unchanged since it was put to him)."""
    for l in lines:
        if ASKED.match(l):
            return l.split(":", 1)[1].split()[-1:] == [entry_hash(lines)]
    return False


def mark_asked(path, job):
    """Add (or refresh) the Asked line under the Status line of every open entry of this job. Changes nothing else."""
    text, err = read(path)
    if text is None:
        print("NOT WRITTEN: %s" % err)
        return 1
    src = text.split("\n")
    out, i, n = [], 0, 0
    while i < len(src):
        if re.match(r"^\s*###\s", src[i]):
            j = i + 1
            while j < len(src) and not re.match(r"^\s*###\s", src[j]):
                j += 1
            block = src[i:j]
            parts = [p.strip(" #`") for p in block[0].split("|")]
            st = next((re.match(r"^\s*status\s*:\s*([A-Za-z]+)", l, re.I) for l in block if re.match(r"^\s*status\s*:", l, re.I)), None)
            open_ = not (st and st.group(1).lower() in CLOSED)
            if open_ and len(parts) > 3 and parts[3].lower() == job.strip().lower():
                block = [l for l in block if not ASKED.match(l)]
                at = next((k for k, l in enumerate(block) if re.match(r"^\s*status\s*:", l, re.I)), 0) + 1
                block.insert(at, "Asked: %s %s" % (time.strftime("%Y-%m-%d"), entry_hash(block)))
                n += 1
            out.extend(block)
            i = j
        else:
            out.append(src[i])
            i += 1
    if not n:
        print("NOT MARKED: no open entry for the job %r" % job)
        return 1
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(out))
    print("Marked %d open entr%s for %r as asked (his answer is awaited; do not ask again)" % (n, "y" if n == 1 else "ies", job))
    return 0


def write_waiting_line(path, line):
    """Set the single "Waiting on:" line right under the board's title; changes nothing else."""
    text, err = read(path)
    if text is None:
        print("NOT WRITTEN: %s" % err)
        return
    lines = text.split("\n")
    for i, l in enumerate(lines):
        if l.startswith("Waiting on:"):
            lines[i] = line
            break
    else:
        lines[1:1] = ["", line] if lines and lines[0].startswith("#") else []
        if not (lines and lines[0].startswith("#")):
            lines[0:0] = [line, ""]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines))
    print("Wrote the Waiting on line at the top of %s" % path)


def main():
    # With no role name, read as the manager (the chat that reads the whole board).
    # --write-waiting (manager only): also rewrite the one "Waiting on:" line at the top of muster/BOARD.md.
    if "--mark-asked" in sys.argv:
        k = sys.argv.index("--mark-asked")
        job = sys.argv[k + 1] if k + 1 < len(sys.argv) else ""
        rest = [a for a in sys.argv[1:k] + sys.argv[k + 2:] if a]
        root0 = find_root(rest[1] if len(rest) > 1 else os.getcwd())
        if not job or root0 is None:
            print("NOT MARKED: needs a job name and a project with muster/BOARD.md")
            return 1
        return mark_asked(os.path.join(root0, "muster", "BOARD.md"), job)
    write_waiting = "--write-waiting" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--write-waiting"]
    # --board <file>: read exactly that board (and BOARD-ARCHIVE.md beside it); strictly read-only, for a second computer
    board_file = None
    if "--board" in args:
        k = args.index("--board")
        board_file = os.path.abspath(args[k + 1]) if k + 1 < len(args) else None
        args = args[:k] + args[k + 2:]
        write_waiting = False
    who = args[0].strip() if args and args[0].strip() else "Manager"
    role = who.lower()
    root = os.path.dirname(board_file) if board_file else find_root(args[1] if len(args) > 1 else os.getcwd())
    if board_file and not os.path.isfile(board_file):
        print("NOT FOUND: no board at %s. Read the board by hand." % board_file)
        return 1
    if root is None:
        print("NOT FOUND: no muster/BOARD.md in this folder or any parent. Read the board by hand.")
        return 1

    mine, others, closed, unreadable = [], [], 0, []
    board_entries = []
    word = re.compile(r"(?<![\w-])(?<!\w )(%s|all)(?![\w-])" % re.escape(role), re.I)
    for name in ("BOARD.md", "BOARD-ARCHIVE.md"):
        path = (os.path.join(root, name) if board_file else os.path.join(root, "muster", name))
        if board_file and name == "BOARD.md":
            path = board_file
        text, err = read(path)
        if text is None:
            if name == "BOARD.md" or os.path.exists(path):
                unreadable.append("%s (%s)" % (name, err))
            continue
        stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path)))
        print("Read %s, last changed %s" % (path, stamp))
        for header, lines, status in parse(text):
            if name == "BOARD.md":
                board_entries.append((header, lines, status))
            if status in CLOSED:
                closed += 1
            elif word.search(header):
                mine.append((name, "\n".join(lines).rstrip()))
            else:
                others.append((name, header))

    print("%d entries concern %s (printed in full), %d other open (headers only), "
          "%d done/closed (hidden), %d unreadable files"
          % (len(mine), who, len(others), closed, len(unreadable)))
    waiting, paused, owner_q = {}, [], []
    for _n, body in mine + [(n, h) for n, h in others]:
        m = re.search(r"->\s*([^|]+?)\s*\|", body.splitlines()[0] if body else "")
        if m:
            waiting[m.group(1)] = waiting.get(m.group(1), 0) + 1
    # who is paused NOW: a chat's LAST entry on the board decides. A later entry from the same chat (any kind), a
    # "Paused: no" line, or Status done/closed clears an older "Paused: yes"; a paused line older than the chat's last
    # entry is never used (D-020, resume).
    seq = []
    for _h, lines, status in board_entries:
        first = lines[0] if lines else ""
        parts = [p.strip(" #`") for p in first.split("|")]
        sender = re.sub(r"\s*->.*", "", parts[2]) if len(parts) > 2 else "?"
        body = "\n".join(lines)
        yes = bool(re.search(r"^\s*paused\s*:\s*yes", body, re.I | re.M)) and not re.search(r"^\s*paused\s*:\s*no", body, re.I | re.M)
        seq.append((sender, parts[1].upper() if len(parts) > 1 else "", parts[3] if len(parts) > 3 else "", yes, status, is_asked(lines)))
    last = {}
    for i, s in enumerate(seq):
        last[s[0]] = i
    for i, (sender, kind, job, yes, status, asked) in enumerate(seq):
        if status in CLOSED:
            continue
        is_p = yes and last[sender] == i
        if is_p:
            paused.append(sender)
            mt = re.search(r"->\s*([^|]+?)\s*\|", board_entries[i][1][0] if board_entries[i][1] else "")
            if mt and waiting.get(mt.group(1)):
                waiting[mt.group(1)] -= 1
                if not waiting[mt.group(1)]:
                    del waiting[mt.group(1)]
        if is_p or kind in ("NEED", "STUCK", "OWNER CALL"):
            owner_q.append((kind, sender, job, is_p, asked))
    # fallback for a worker that cannot write the main board: a file .muster-paused in its own folder copy
    for p in sorted(glob.glob(os.path.join(root, ".claude", "worktrees", "*", ".muster-paused"))):
        who_p = os.path.basename(os.path.dirname(p))
        try:
            with open(p, encoding="utf-8") as fh:
                who_p = (fh.readline().strip() or who_p)
        except OSError:
            pass
        if who_p not in paused:
            paused.append(who_p)
            owner_q.append(("", who_p, "paused (marker file)", True, False))
    bits = ["%s (%d)" % kv for kv in sorted(waiting.items())]
    bits += ["relay his answer to %s (never send him to type in it)" % p for p in paused]
    line = "Waiting on: " + (", ".join(bits) or "nobody")
    print(line)
    if write_waiting:
        try:  # the manager's run also keeps the board small: finished entries a day old or more move to the archive
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import board_archive
            n_moved = board_archive.archive(root)
            if n_moved:
                print("Moved %d finished entries to BOARD-ARCHIVE.md" % n_moved)
        except Exception as err:
            print("ARCHIVE SKIPPED: %s" % err)
        write_waiting_line(os.path.join(root, "muster", "BOARD.md"), line)
    fresh_q = [q for q in owner_q if not q[4]]
    asked_q = [q for q in owner_q if q[4]]
    order = {"OWNER CALL": 0, "STUCK": 1, "NEED": 2}
    if fresh_q:
        print("\nOWNER QUESTIONS (ask the owner the top one as lettered lines (***A.*** ...) under a bold heading line 'WORD \u00b7 job' before ending your turn, unless his own words answer it; then mark it: board_digest.py Manager --mark-asked <job>):")
        for kind, sender, job, is_p, _a in sorted(fresh_q, key=lambda q: (not q[3], order.get(q[0], 3))):
            print("  %s from %s: %s%s" % (kind or "REPORT", sender, job,
                  "  [PAUSED: relay his answer to %s]" % sender if is_p else ""))
    if asked_q:
        print("\nWAITING ON HIS ANSWER (already asked; do not ask again until he answers or the entry changes):")
        for kind, sender, job, is_p, _a in asked_q:
            print("  %s from %s: %s" % (kind or "REPORT", sender, job))
    for item in unreadable:
        print("UNREADABLE:", item)
    for name, body in mine:
        print("\n--- [%s] ---\n%s" % (name, body))
    if others:
        print("\nOther open entries (headers only):")
        for name, header in others:
            print("  [%s] %s" % (name, header))
    print("\nMissing stays missing: if a count looks wrong, read muster/BOARD.md by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
