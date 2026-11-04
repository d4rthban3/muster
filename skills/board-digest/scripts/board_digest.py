#!/usr/bin/env python3
"""Print the board entries a role must read, without reading the whole board.

Read-only: reads muster/BOARD.md and muster/BOARD-ARCHIVE.md, writes nothing, no network.

Usage:  python3 board_digest.py <ROLE> [project-dir]

Entry format (see templates/BOARD.md):
    ### <date> | <DONE|READY|PASS|FAIL|STUCK|NEED> | <from> -> <to> | <job name>
    Status: open | done | closed
    ...body...

An entry is printed in full when its header names ROLE or ALL.
Other entries that are not done/closed are printed as headers only.
Anything that cannot be read is reported, never hidden.
"""
import os
import re
import sys
import time

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


def main():
    # With no role name, read as the manager (the chat that reads the whole board).
    name = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else "Manager"
    role = name.lower()
    root = find_root(sys.argv[2] if len(sys.argv) > 2 else os.getcwd())
    if root is None:
        print("NOT FOUND: no muster/BOARD.md in this folder or any parent. Read the board by hand.")
        return 1

    mine, others, closed, unreadable = [], [], 0, []
    word = re.compile(r"(?<![\w-])(?<!\w )(%s|all)(?![\w-])" % re.escape(role), re.I)
    for name in ("BOARD.md", "BOARD-ARCHIVE.md"):
        path = os.path.join(root, "muster", name)
        text, err = read(path)
        if text is None:
            if name == "BOARD.md" or os.path.exists(path):
                unreadable.append("%s (%s)" % (name, err))
            continue
        stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path)))
        print("Read %s, last changed %s" % (path, stamp))
        for header, lines, status in parse(text):
            if status in CLOSED:
                closed += 1
            elif word.search(header):
                mine.append((name, "\n".join(lines).rstrip()))
            else:
                others.append((name, header))

    print("%d entries concern %s (printed in full), %d other open (headers only), "
          "%d done/closed (hidden), %d unreadable files"
          % (len(mine), name, len(others), closed, len(unreadable)))
    waiting = {}
    for _n, body in mine + [(n, h) for n, h in others]:
        m = re.search(r"->\s*([^|]+?)\s*\|", body.splitlines()[0] if body else "")
        if m:
            waiting[m.group(1)] = waiting.get(m.group(1), 0) + 1
    print("Waiting on: " + (", ".join("%s (%d)" % kv for kv in sorted(waiting.items())) or "nobody"))
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
