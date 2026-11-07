---
name: ready-checks
description: The two checks a builder or the designer runs before sending READY, and the READY report itself. Use when finishing a piece of work, before sending READY, and when an inspector decides whether a READY is complete.
---

# ready-checks

Build and inspect are different hands. The builder runs these two checks so the inspector never has to find what the
builder could have found.

## The two checks
1. **Run all the tests on the combined work**, not just the new test: bring your line of work up to date with the
   main line first, then run every test listed in `muster/CHECKS.md` (skill `run-checks`). A pass on your own line
   of work alone proves little.
2. **Search the whole project for the thing you just changed.** If you fixed a mistake in one place, search for every
   other place with the same shape (the same name, setting, query or wording) and fix or list each one.

## The READY report (six lines, see `muster/REPORT.md`)
```
READY: <job name, word for word from the order>
What:  <what was done>
Where: <line of work and saved version>; touches: <none, or the shared database, file store or outside connection, by name>
Why:   <the order or decision it comes from>
How:   test command `<the exact command>`: <passed>/<total> passed, <failed> failed on the combined work; searched for <thing>: <n> other places, <fixed / listed>
Need:  <what is left out, or "nothing; ready for the inspector">
Usage: <the line scripts/usage.py prints>
```
If you add a test file, name it on the Where line: the manager adds it to `muster/CHECKS.md`, and `scripts/check-tests.py`
(run in the free test) fails when a test file on disk is missing from that list.
Send it to the inspector. The designer also names its screenshots on the Where line.

## Inspector side
FAIL a READY that lacks the line of work, the saved version, the "touches" part, or the two checks. A FAIL is a
normal outcome: say exactly what is missing and do not fix it yourself.

## Do not
- Send READY on work you have not run.
- Pass your own work.
