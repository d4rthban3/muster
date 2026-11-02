---
name: ready-checks
description: The two checks a builder runs before saying READY, and the READY line itself. Use when a builder is finishing a piece of work, before posting READY on the board, and when an inspector is deciding whether a READY is valid.
---

# ready-checks

Build and inspect are different hands. The builder runs these two checks so the inspector never has to find what a
builder could have found.

## The two checks
1. **Run all tests on the combined code**, not just the new test: merge or rebase onto the current main line first,
   then run every suite in `muster/CHECKS.md` (skill `run-checks`). A pass on your branch alone proves little.
2. **Search the whole project for the pattern just changed.** If you fixed a bug in one call site, search for every
   other site with the same shape (function name, constant, query, format string) and fix or list each one.

## The READY line
Post to the board (and message the inspector) with all of:
```
### <date> | READY | <you> -> inspector | <piece>
Status: open
Branch: <branch>   Commit: <short hash>
Touches: none | <shared database / file store / outside connection, by name>
Checks: tests <passed>/<total> on combined code; searched for <pattern>: <n> other sites, <fixed/listed>
Detail: <link or path>
```

## Inspector side
Fail a READY that lacks any of: branch, commit, the "Touches" line, or the two checks. A fail is a normal outcome:
write what is missing, send it back, do not fix it yourself.

## Do not
- Say READY on work you have not run.
- Pass your own work.
