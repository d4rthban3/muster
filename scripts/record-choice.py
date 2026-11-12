#!/usr/bin/env python3
"""Record an owner's choice on his list, word for word. The manager runs it after every choice card or button answer.

Usage: record-choice.py <project-folder> <item-number> --question "..." --option "A. ..." --option "B. ..." --picked "B. ..." [--said "his own words"]
Writes, under item <number> in muster/OWNERS-LIST.md (nothing else is changed), a block:
   Choice (<date>): <question>
     Options: every option's text, in order
     Picked: the one picked
     He said: his own words, if he typed any
With --no-pick (no --option, no --picked): "Picked: (no pick: he skipped the card)" or, with --said, "(no pick: he answered in his own words)"; nothing is decided.
Exit 1 and says why if the item is not found or the picked text is not one of the options. Standard library only.
"""
import argparse
import datetime
import os
import re
import sys

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("item", type=int)
ap.add_argument("--question", required=True)
ap.add_argument("--option", action="append", default=[])
ap.add_argument("--picked", default="")
ap.add_argument("--said", default="")
ap.add_argument("--no-pick", action="store_true", help="he skipped the card or answered in his own words (give them with --said): records that nothing was picked")
a = ap.parse_args()
if a.no_pick:
    a.picked = "(no pick: %s)" % ("he answered in his own words" if a.said else "he skipped the card")
elif not a.option or not a.picked:
    sys.exit("record-choice: pass --option (each one) and --picked, or --no-pick when he skipped the card or answered in his own words")

path = os.path.join(a.project, "muster", "OWNERS-LIST.md")
try:
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
except OSError as err:
    sys.exit("record-choice: cannot read %s (%s)" % (path, err))
if not a.no_pick and a.picked not in a.option and not a.said:
    sys.exit("record-choice: the picked text is not one of the options; pass it exactly, or pass --said for his own words")
# look only outside fenced ``` blocks (the list's made-up examples live in one) and, if the list has an "## Open"
# heading, only from there on
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
    sys.exit("record-choice: item %d not found in %s" % (a.item, path))
end = start + 1
while end < len(lines) and not re.match(r"^(\d+\.\s|#)", lines[end]):
    end += 1
while end > start + 1 and not lines[end - 1].strip():
    end -= 1
block = ["   Choice (%s): %s" % (datetime.date.today().isoformat(), a.question),
         "     Options: " + " | ".join(a.option),
         "     Picked: " + a.picked]
if a.said:
    block.append("     He said: " + a.said)
lines[end:end] = block
with open(path, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines))
print("Recorded under item %d: %s" % (a.item, a.picked))
