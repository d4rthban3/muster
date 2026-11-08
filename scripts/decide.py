#!/usr/bin/env python3
"""Add one entry to muster/DECISIONS-LOG.md, only when it rests on the owner's click or his own words (D-022).

Usage: decide.py <project-folder> --item N --title "..." --decision "his exact words" --why "..." --affects "..."
                 (--picked "B. blue" | --said "his own words" --chose "blue" [--others "green"]) [--supersedes D-0nn]

The decision log is never appended by hand. This script refuses unless the owner's list item N (muster/OWNERS-LIST.md)
already holds the proof, written there by scripts/record-choice.py right after his answer:
  --picked  must equal a "Picked:" line under item N (his click on a choice card or button), or
  --said    must be his WHOLE typed line: the quoted words on item N's first line, or a whole "He said:" line (at least
            three words, never a piece of one), it must contain --chose, the name of the option chosen, and must not
            hedge ("or", "maybe", "whatever", "either"...) nor name any --others option. The manager's own lines never count.
A manager's own reading of his words is not proof: when his words seem to point to an option, ask him with that
option marked "my pick". Exit 1 and says why when the proof is missing. Standard library only.
"""
import argparse
import datetime
import os
import re
import sys

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--item", type=int, required=True)
ap.add_argument("--title", required=True)
ap.add_argument("--decision", required=True)
ap.add_argument("--why", required=True)
ap.add_argument("--affects", default="all")
ap.add_argument("--supersedes", default="none")
ap.add_argument("--picked", default="")
ap.add_argument("--said", default="")
ap.add_argument("--others", action="append", default=[], help="with --said: every other option's name; none may appear in his words")
ap.add_argument("--chose", default="", help="with --said: the option's name or label; it must appear in his words")
a = ap.parse_args()


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


if not a.picked and not a.said:
    sys.exit("decide: refused. A decision needs --picked (the option he clicked) or --said (his own words naming the choice). "
             "Do not choose for him: ask him with the option you favour marked \"my pick\".")
lpath = os.path.join(a.project, "muster", "OWNERS-LIST.md")
dpath = os.path.join(a.project, "muster", "DECISIONS-LOG.md")
try:
    with open(lpath, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    with open(dpath, encoding="utf-8") as fh:
        log = fh.read()
except OSError as err:
    sys.exit("decide: cannot read %s" % err)
fenced, begun, start = False, not any(l.strip() == "## Open" for l in lines), None
for i, l in enumerate(lines):
    if l.strip().startswith("```"):
        fenced = not fenced
        continue
    if fenced:
        continue
    if l.strip() == "## Open":
        begun = True
    if begun and start is None and re.match(r"^%d\.\s" % a.item, l):
        start = i
if start is None:
    sys.exit("decide: refused. Item %d is not on the owner's list." % a.item)
end = start + 1
while end < len(lines) and not re.match(r"^(\d+\.\s|#)", lines[end]):
    end += 1
block = lines[start:end]
if a.picked:
    ok = any(norm(l).startswith("picked:") and norm(l)[len("picked:"):].strip() == norm(a.picked) for l in block)
    how = "his click"
    if not ok:
        sys.exit("decide: refused. Item %d has no \"Picked: %s\" line. Record his click first with scripts/record-choice.py; "
                 "if he has not clicked, ask him." % (a.item, a.picked))
else:
    # only his own words count: the quoted words on the item's first line, and lines record-choice.py wrote as "He said:".
    # Never the manager's Kind, Did, Stands or Checked lines.
    his = re.findall(r'"([^"]+)"', block[0]) + [l.split(":", 1)[1] for l in block if norm(l).startswith("he said:")]
    how = "his own words"
    strip = lambda s: norm(s).strip(" .!?,;:\"'")
    if len(norm(a.said).split()) < 3 or not any(strip(a.said) == strip(h) for h in his):
        sys.exit("decide: refused. --said must be his WHOLE quoted line under item %d (the quoted words on its first line, or a "
                 "whole \"He said:\" line; at least three words), never a piece of it. Record what he typed with "
                 "record-choice.py --said; if his words only point toward an option, ask him." % a.item)
    hedge = re.search(r"\b(or|maybe|perhaps|whatever|either|any of|not sure|you choose|you pick|up to you|your call|surprise me)\b", norm(a.said))
    named = [o for o in a.others if o and norm(o) in norm(a.said)]
    if hedge or named:
        sys.exit("decide: refused. His words leave the choice open (\"%s\"), so they do not name one choice. Ask him with the "
                 "option you favour marked \"my pick\"." % (hedge.group(0) if hedge else named[0]))
    if not a.chose or norm(a.chose) not in norm(a.said):
        sys.exit("decide: refused. His words must name the choice: pass --chose with the option's name, and it must appear in "
                 "--said. If they do not name it, ask him with that option marked \"my pick\".")
nums = [int(n) for n in re.findall(r"^### D-(\d+)", log, re.M)]
num = "D-%03d" % ((max(nums) if nums else 0) + 1)
entry = ("### %s · %s · %s\nDecision: %s\nWhy: %s\nChosen by: %s (list item %d)\nSupersedes: %s\nAffects: %s\n"
         % (num, datetime.date.today().isoformat(), a.title, a.decision, a.why, how, a.item, a.supersedes, a.affects))
with open(dpath, "w", encoding="utf-8", newline="") as fh:
    fh.write(log.rstrip("\n") + "\n\n" + entry)
print("Recorded %s on %s's proof (item %d)" % (num, how, a.item))
