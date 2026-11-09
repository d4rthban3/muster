#!/usr/bin/env python3
"""Post one entry to the crew board (muster/BOARD.md in the main folder) in the six-line shape (owner's list item 41).
  board-post.py --from "Builder A_Muster_004" --to "Inspector_Muster_004, Manager_Muster_004" --word READY --job "helpers in chats" \
      --id builder-a-helpers-in-chats-2 --what "..." --where "...; touches: pages" --why "..." --how "..." --need "..." [--paused] [--folder DIR]
It only appends one entry at the end of the board, never edits or deletes one, and refuses anything that is not the shape in
muster/REPORT.md: first word one of DONE READY PASS FAIL STUCK NEED, every line filled and one line long, 'touches:' in Where, and
no key or password look-alikes. It is the one way a worker posts to the board; it changes no settings and nothing else."""
import argparse
import datetime
import os
import re
import subprocess
import sys

WORDS = ("DONE", "READY", "PASS", "FAIL", "STUCK", "NEED")
SECRET = re.compile(r"(sk-[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{12,}|AKIA[A-Z0-9]{12,}|password\s*[:=]|api[_-]?key\s*[:=])", re.I)


def main_folder(start):
    try:
        out = subprocess.run(["git", "-C", start, "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True).stdout.strip()
        full = os.path.normpath(os.path.join(start, out))
        return os.path.dirname(full) if os.path.basename(full) == ".git" else start
    except Exception:
        return start


def die(msg):
    print("BOARD POST REFUSED: " + msg)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="sender", required=True)
    ap.add_argument("--to", required=True)
    ap.add_argument("--word", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--id", default="")
    for k in ("what", "where", "why", "how", "need"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--paused", action="store_true", help="add the line 'Paused: yes' (messages are paused)")
    ap.add_argument("--folder", default=os.getcwd())
    a = ap.parse_args()
    word = a.word.upper()
    if word not in WORDS:
        die("the first word must be one of " + ", ".join(WORDS))
    fields = {k: getattr(a, k).strip() for k in ("what", "where", "why", "how", "need", "job", "sender", "to")}
    for k, v in fields.items():
        if not v or "\n" in v or "\r" in v:
            die("%s must be filled and one line long" % k)
        if SECRET.search(v):
            die("%s looks like a key or password; none goes on the board" % k)
    if "touches:" not in fields["where"]:
        die("the Where line needs 'touches: <none or the shared thing>'")
    root = main_folder(os.path.abspath(a.folder))
    board = os.path.join(root, "muster", "BOARD.md")
    if not os.path.isfile(board):
        die("no muster/BOARD.md in " + root)
    first = "%s: %s" % (word, fields["job"]) + (" [ID %s]" % a.id.strip() if a.id.strip() else "")
    lines = ["", "### %s | %s | %s -> %s | %s" % (datetime.date.today().isoformat(), word, fields["sender"], fields["to"], fields["job"]), "Status: open"]
    if a.paused:
        lines.append("Paused: yes")
    lines += [first, "What:  " + fields["what"], "Where: " + fields["where"], "Why:   " + fields["why"], "How:   " + fields["how"], "Need:  " + fields["need"]]
    with open(board, "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print("posted to the board: %s (%s -> %s)" % (first, fields["sender"], fields["to"]))


main()
