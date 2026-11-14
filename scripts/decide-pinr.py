#!/usr/bin/env python3
"""Record one founder decision in PINR's decisions log, only from his click or his own words (Muster D-022, items 80 and 86).

This is Muster's decide.py for PINR's layout. install-checks.py --profile pinr copies it to <project>/manager/decide.py.
Usage (the same flags PINR's recorder always had, plus --item and --manager):
  python3 manager/decide.py --title "..." --question "..." --picked "A. Go live" [--body "..."]
  python3 manager/decide.py --title "..." --question "..." --said "<his whole line>" [--chose "C"] [--body "..."] [--item N]
What it takes as his word:
  --picked          his click, exactly as the app returned it.
  --said "c"        a bare typed letter answering a lettered question; it names that lettered choice (--chose may name its option).
  --said "<line>"   his whole line, and --chose, the option's name, must appear in it; a line that leaves the choice open
                    ("or", "maybe", "either", "whatever looks better") is refused.
  --said "whatever muster manager tells you to do."   a line that hands the choice to someone he names ("whatever <who> tells
                    you to do") is recorded as exactly that, a handover to <who>; the manager never picks for him.
  --item N          optional proof against PINR's founder list: his whole line must be quoted under item N there.
Appends "**N. title (founder, date: "words", to <manager>'s question ...).** body" to PINR's decisions log and prints N.
The log and the list are named in <project>/.muster-checks/profile.json ("decision_log", "founder_list"). Standard library only.
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
try:
    PROFILE = json.load(open(os.path.join(PROJ, ".muster-checks", "profile.json"), encoding="utf-8"))
except (OSError, ValueError):
    PROFILE = {}
LOG = os.path.join(PROJ, PROFILE.get("decision_log", "PINR-claudecode-handoff/pinr-claude-code-starter-v2/DECISIONS-LOG.md"))
LIST = os.path.join(PROJ, PROFILE.get("founder_list", "Founder/FOUNDER-LIST.md"))
HEDGE = re.compile(r"\b(or|maybe|perhaps|whatever|either|any of|not sure|i guess|you choose|you pick|up to you|your call|surprise me)\b", re.I)
OPEN = re.compile(r"\b(or|maybe|perhaps|either|not sure|i guess|up to you|your call|surprise me)\b", re.I)
LETTER = re.compile(r"\(?([A-Da-d])\)?[.:!]*")
DELEGATE = re.compile(r"^\s*whatever\s+(?:the\s+)?([a-z][a-z0-9_ .-]{1,40}?)\s+(?:tells|says|tell|say|told|recommends)\s+(?:you|us|me)(?:\s+to\s+do)?\s*[.!]*\s*$", re.I)


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower().strip(" .!?,;:\"'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--question", required=True)
    ap.add_argument("--picked", help="his click, exactly as the app returned it")
    ap.add_argument("--said", help="his whole line, word for word")
    ap.add_argument("--chose", help="the choice his line names (with --said)")
    ap.add_argument("--body", default="")
    ap.add_argument("--item", type=int, help="his founder-list item; his whole line must be quoted there")
    ap.add_argument("--manager", default="the manager", help="the manager's chat name, for the entry")
    a = ap.parse_args()
    if bool(a.picked) == bool(a.said):
        sys.exit("decide: give exactly one of --picked or --said")
    words = a.picked or a.said
    how = ""
    if a.said:
        said = a.said.strip()
        m = LETTER.fullmatch(said)
        d = DELEGATE.match(said)
        if m:
            how = "his typed letter %s%s" % (m.group(1).upper(), (", " + a.chose) if a.chose else "")
        elif d and not OPEN.search(said):
            how = "he handed the choice to %s" % d.group(1).strip()
        else:
            if not a.chose:
                sys.exit("decide: refused. --said needs --chose, the option his line names")
            if HEDGE.search(said):
                sys.exit("decide: refused. His line leaves the choice open; ask him with lettered choices, your pick marked \"my pick\"")
            if norm(a.chose) not in norm(said):
                sys.exit("decide: refused. His line does not name the choice; ask him with lettered choices")
            how = "his own words naming %s" % a.chose
        if a.item is not None:
            try:
                lines = open(LIST, encoding="utf-8").read().split("\n")
            except OSError as err:
                sys.exit("decide: cannot read %s" % err)
            start = next((i for i, l in enumerate(lines) if re.match(r"^%d\.\s" % a.item, l)), None)
            if start is None:
                sys.exit("decide: refused. Item %d is not on the founder list." % a.item)
            end = start + 1
            while end < len(lines) and not re.match(r"^(\d+\.\s|#)", lines[end]):
                end += 1
            if norm(said) not in norm(" ".join(lines[start:end])):
                sys.exit("decide: refused. His whole line is not quoted under founder-list item %d; write it there first, or ask him." % a.item)
    try:
        text = open(LOG, encoding="utf-8").read()
    except OSError as err:
        sys.exit("decide: cannot read %s" % err)
    nums = [int(n) for n in re.findall(r"^\*\*(\d+)\.", text, re.M)]
    n = (max(nums) if nums else 0) + 1
    day = datetime.date.today().isoformat()
    body = ((" " + a.body) if a.body else "") + ((" (Recorded as: " + how + ".)") if how else "")
    entry = '\n\n**%d. %s (founder, %s: "%s", to %s\'s question %s).**%s\n' % (
        n, a.title.rstrip("."), day, words, a.manager, a.question, body)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(entry)
    print(n)


if __name__ == "__main__":
    main()
