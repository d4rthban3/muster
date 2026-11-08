#!/usr/bin/env python3
"""Move finished board entries to muster/BOARD-ARCHIVE.md so the board stays small and every check reads only what is open.

Usage:  python3 board_archive.py [project-dir] [--days N] [--one-line] [--dry-run]
Moves, from muster/BOARD.md to the end of muster/BOARD-ARCHIVE.md, every entry that is done or closed AND at least N days old
(default 1; the age is the date in the entry's heading). Nothing open is ever moved; anything it cannot date stays.
Muster's format: an entry starts with a heading line "### <date> | <KIND> | <from> -> <to> | <job>" and has a line
"Status: done" (or closed). With --one-line (a board that keeps one line per entry, such as PINR's): a line that holds a date
YYYY-MM-DD and the word done or closed (any case) is one finished entry and moves the same way.
Prints what it moved. Standard library only.
"""
import datetime
import os
import re
import sys


def find_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(cur, "muster", "BOARD.md")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def split_entries(lines):
    """Return (head, entries): head = lines before the first '###' heading outside code fences; entries = [[lines]]."""
    head, entries, cur, fenced = [], [], None, False
    for line in lines:
        if line.strip().startswith("```"):
            fenced = not fenced
        if not fenced and re.match(r"^\s*###\s", line) and not line.strip().startswith("```"):
            if cur is not None:
                entries.append(cur)
            cur = [line]
        elif cur is not None:
            cur.append(line)
        else:
            head.append(line)
    if cur is not None:
        entries.append(cur)
    return head, entries


def entry_date(first):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", first)
    try:
        return datetime.date.fromisoformat(m.group(1)) if m else None
    except ValueError:
        return None


def finished(entry):
    for l in entry:
        m = re.match(r"^\s*status\s*:\s*([A-Za-z]+)", l, re.I)
        if m:
            return m.group(1).lower() in ("done", "closed")
    return False


def archive(root, days=1, one_line=False, dry=False, today=None):
    today = today or datetime.date.today()
    bpath = os.path.join(root, "muster", "BOARD.md")
    apath = os.path.join(root, "muster", "BOARD-ARCHIVE.md")
    with open(bpath, encoding="utf-8") as fh:
        text = fh.read()
    lines = text.split("\n")
    moved, keep = [], []
    if one_line:
        fenced = False
        for l in lines:
            if l.strip().startswith("```"):
                fenced = not fenced
            d = entry_date(l)
            if (not fenced and d and (today - d).days >= days and re.search(r"\b(done|closed)\b", l, re.I)
                    and not re.search(r"\b(open|waiting)\b", l, re.I)):
                moved.append(l)
            else:
                keep.append(l)
        moved_text = "\n".join(moved)
        new_board = "\n".join(keep)
    else:
        head, entries = split_entries(lines)
        out = list(head)
        for e in entries:
            d = entry_date(e[0])
            if d and (today - d).days >= days and finished(e):
                moved.append(e)
            else:
                out.extend(e)
        new_board = "\n".join(out)
        moved_text = "\n".join("\n".join(e).rstrip("\n") + "\n" for e in moved)
    if not moved:
        return 0
    if not dry:
        with open(apath, "a", encoding="utf-8", newline="") as fh:
            fh.write(("" if not os.path.exists(apath) or os.path.getsize(apath) == 0 else "\n") + moved_text.rstrip("\n") + "\n")
        with open(bpath, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_board)
    return len(moved)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    days = 1
    if "--days" in sys.argv:
        i = sys.argv.index("--days")
        days = int(sys.argv[i + 1])
        args = [a for a in args if a != sys.argv[i + 1]]
    root = find_root(args[0] if args else os.getcwd())
    if root is None:
        print("NOT FOUND: no muster/BOARD.md here or in any parent.")
        return 1
    n = archive(root, days, "--one-line" in sys.argv, "--dry-run" in sys.argv)
    print("%s %d finished entr%s %s BOARD-ARCHIVE.md" % ("Would move" if "--dry-run" in sys.argv else "Moved", n, "y" if n == 1 else "ies", "to"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
