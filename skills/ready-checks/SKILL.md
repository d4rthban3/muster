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

## The READY record (see `muster/REPORT.md`)
```
{"v":1,"kind":"READY","id":"builder-a-card-fix-1","job":"card-fix","from":"builder-a","to":"inspector","sha":"<saved version>","version":null,"tests":{"passed":12,"failed":0},"touches":["<shared thing, or empty>"],"need":"pass_or_fail","usage":{"week_pct":41}}
```
`tests` is the combined work's count from the exact test command; the search for what you changed and what it found go on the board
entry for the job (data in the record, detail on the board). A READY with no sha, no test count above zero, no `touches` or no `usage`
is refused by the check.
If you add a test file, name it on the board entry: the manager adds it to `muster/CHECKS.md`, and `scripts/check-tests.py`
(run in the free test) fails when a test file on disk is missing from that list.
Send it to the inspector. The designer also names its screenshots on the board entry: for a small visible change one dark and one light picture at one size. The inspector re-runs only the changed tests plus one full run on the merged work, so say which tests changed.

## Inspector side
FAIL a READY that lacks the line of work, the saved version, the "touches" part, or the two checks. A FAIL is a
normal outcome: say exactly what is missing and do not fix it yourself.

## Do not
- Send READY on work you have not run.
- Pass your own work.
