---
name: run-checks
description: Run the project's test commands and report the real result. Use when asked to "run the checks" or "run the tests", to confirm a change did not break anything, or before posting READY. It reads the printed counts and result lines itself, because an exit code alone can say "fine" when a test failed.
---

# run-checks

Runs the project's own test commands and reads their printout. It changes no tracked file, fixes nothing, signs
nothing off.

## Why
A suite's exit code is not a trustworthy result: some suites end normally even when a test fails. The honest result is
the printed count plus your own count of result lines in the full printout.

## Commands allowed
1. The commands listed in `muster/CHECKS.md` (one per line: `<folder> | <command> | <expected count>`).
2. A read-only search for test files, to compare with the list.
3. `git status --porcelain`, `git rev-parse HEAD`, `date`.
Nothing else. If a command asks for a key, a password or a network address, stop and report.

## Steps
1. Read `muster/CHECKS.md` as it is **now**, never from memory. Count the suites and say how many you found.
2. Record the starting state: commit id, date and time, `git status --porcelain`.
3. Run each command from its folder. Save the whole printout and exit code to a file in a temporary folder
   outside the project (the inspector never writes into the project).
4. For each suite record: exit code, last printed line and its count (`passed/total`), and your own count of result
   lines (a line that is exactly `PASS`/`FAIL`, begins with `PASS `/`FAIL `, or ends with `: PASS`/`: FAIL`).
5. **PASS** only if all hold: exit 0; printed count equals the expected count; no FAIL lines; your PASS-line count equals
   the total (if it differs, give both numbers and decide neither).
6. **FAIL** if any does not hold. A non-zero exit is always FAIL; a zero exit proves nothing alone.
7. **NOT RUN** if it did not run, printed nothing, or crashed before a count. Never call it PASS; never invent a count.
8. Search for test files that exist but are not listed, and listed commands whose file is missing.
9. Run `git status --porcelain` again; name any files that changed and say whether a suite could have written them.

## Report (plain)
- Use the six-line report (`muster/REPORT.md`); the How line says which sets of tests were run and which were not, e.g. "Suite A and B pass (40 of 40). Suite C: not
  run." Never write "all tests pass" without naming the sets.
- Then: state tested, suites found, a small table (suite, expected, printed, PASS lines, FAIL lines, exit code,
  result), the first failing test's name and printed reason for any FAIL, unlisted test files.
- One closing sentence on what a green result does and does not prove.

## Do not
- Edit a test or setting to make a result pass.
- Run anything outside the allowed list.
- Treat your result as an inspection: the inspector runs their own, independently.
- Print keys or secrets into the report.
