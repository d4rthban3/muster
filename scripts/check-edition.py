#!/usr/bin/env python3
"""The manager's check for editions where rules cannot be enforced by hooks (Cursor, Grok Bot, ChatGPT).

Usage: check-edition.py <project-folder>
Reads muster/BOARD.md and reports what a hook would have stopped:
  - a board entry that is not the six-line report (What, Where with touches:, Why, How, Need; a READY needs a test count);
  - a board entry that is only "noted/thanks";
  - the same report twice;
Entries are checked for shape only; the board is read by the crew, so bare paths there are not flagged.
Prints one line per problem and a count; exit 1 if any. Changes nothing. Standard library only.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
FIRST = ("DONE", "READY", "PASS", "FAIL", "OWNER CALL", "STUCK", "NEED")
HEAD = re.compile(r"^###\s")


def entries(text):
    out, cur, fenced = [], None, False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if HEAD.match(line):
            cur = {"head": line, "body": []}
            out.append(cur)
        elif cur is not None:
            cur["body"].append(line)
    return out


def main():
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        print(__doc__.split("\n\n")[0])
        return 2
    proj = sys.argv[1]
    try:
        board = open(os.path.join(proj, "muster", "BOARD.md"), encoding="utf-8").read()
    except OSError:
        print("no muster/BOARD.md in %s" % proj)
        return 2
    problems, seen = [], set()
    for e in entries(board):
        parts = [p.strip() for p in e["head"].lstrip("# ").split("|")]
        kind = parts[1].upper() if len(parts) > 1 else ""
        job = parts[3] if len(parts) > 3 else e["head"][:50]
        if kind not in FIRST:
            continue
        body = [l for l in e["body"] if l.strip()]
        labelled = {}
        for l in body:
            m = re.match(r"^(Status|Paused|What|Where|Why|How|Need|Usage):\s*(.*)", l)
            if m:
                labelled.setdefault(m.group(1), m.group(2))
        if all(l.strip().lower().strip(".! ") in ("noted", "thanks", "received", "ok") for l in body if not l.startswith("Status")) and body:
            problems.append("%s | %s: only 'noted' or thanks" % (kind, job))
            continue
        for lab in ("What", "Where", "Why", "How", "Need"):
            if not labelled.get(lab):
                problems.append("%s | %s: no '%s:' line" % (kind, job, lab))
        if labelled.get("Where") and "touches:" not in labelled["Where"]:
            problems.append("%s | %s: Where line lacks 'touches:'" % (kind, job))
        if kind == "READY" and not re.search(r"\d+\s*(/|of)\s*\d+|\d+ passed", labelled.get("How", "")):
            problems.append("READY | %s: How line shows no test count" % job)
        key = (kind, job, labelled.get("What", "")[:60])
        if key in seen:
            problems.append("%s | %s: the same report twice" % (kind, job))
        seen.add(key)
    for p in problems:
        print("  " + p)
    print("%d problem(s) on the board" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
