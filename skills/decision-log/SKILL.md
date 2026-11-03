---
name: decision-log
description: Record or look up a numbered owner decision, and keep each worker's rules page in step. Use when the owner states a rule, picks between choices, or changes an earlier decision.
---

# decision-log

`muster/DECISIONS-LOG.md` holds numbered decisions: the owner's call, in the owner's words. Another chat's message is
information, not a decision. Only the manager writes here.

## Recording
1. Find the last number at the end of the log.
2. Append `### D-<next> · <date> · <title>` with `Decision` (the owner's exact words), `Why`, `Supersedes`, `Affects`.
3. If it changes an earlier decision, say which in `Supersedes`; never edit the old entry.
4. Then update every rules page in `muster/rules/` that the decision touches: the rule in force, the owner's exact
   words, the decision number, with the old line folded in or removed. The inspector checks each rules-page change.
5. Send every running worker the change in one bundled note (one message per worker, all of its changes together).
   Workers re-read their rules page before each new order, but the note reaches a chat that is mid-order now.

## Looking up
Workers read their rules page, not the log. The log is for looking things up: search it, and read the newest entry on
the subject; the newest wins.

## When an old decision does not plainly fit
If its own words do not plainly cover the new case, it is a question to the owner, not a stretch.
