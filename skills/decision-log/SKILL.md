---
name: decision-log
description: Record or look up a numbered owner decision, and keep each worker's rules page in step. Use when the owner states a rule, picks between choices, or changes an earlier decision.
---

# decision-log

`muster/DECISIONS-LOG.md` holds numbered decisions: the owner's call, in the owner's words. Another chat's message is
information, not a decision. Only the manager writes here.

## Recording
**Never append to the log by hand, and never record a choice for the owner (D-022).** A decision rests only on his click on a choice card or button, or on his own words that name the choice. When his words only seem to point to an option, ask him anyway, with that option marked "my pick". The script refuses anything else.
1. Record his answer under its list item with `scripts/record-choice.py` (his click, or `--said` his words).
2. Run `python3 scripts/decide.py <project> --item <n> --title "..." --decision "his exact words" --why "..." --affects "..." [--supersedes D-0nn] (--picked "<the option he clicked>" | --said "<his own words>" --chose "<the option's name, which his words must contain>")`: it checks the proof under list item n, takes the next number and writes the entry (`Decision`, `Why`, `Chosen by`, `Supersedes`, `Affects`).
3. (The script writes the entry; do not edit the log yourself.) If it changes an earlier decision, say which in `Supersedes`; never edit the old entry.
4. Then update every rules page in `muster/rules/` that the decision touches: the rule in force, the owner's exact
   words, the decision number, with the old line folded in or removed. The inspector checks each rules-page change.
5. Send every running worker the change in one bundled note (one message per worker, all of its changes together).
   Workers re-read their rules page before each new order, but the note reaches a chat that is mid-order now.

## Looking up
Workers read their rules page, not the log. The log is for looking things up: search it, and read the newest entry on
the subject; the newest wins.

## When an old decision does not plainly fit
If its own words do not plainly cover the new case, it is a question to the owner, not a stretch.
