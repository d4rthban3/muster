# Checks

Muster's own test commands, tracked in git so the free GitHub run can read them (`scripts/check-tests.py` reads this file and `muster/CHECKS.md`).
One line per test command: `<folder> | <command> | <expected count>`.

. | claude plugin validate . --strict | not checked yet
. | bash scripts/scan-leaks.sh | clean
. | bash scripts/version-check.sh | ok
. | python3 scripts/rules-check-selftest.py (also with MUSTER_CHECKS_BIN set to the built program) | all pass
. | python3 scripts/profile-selftest.py | all pass
. | python3 scripts/idle-check-selftest.py | all pass
. | python3 scripts/worker-queue-check-selftest.py | all pass
checks | cargo test | all pass
look | claude plugin test . (covers look/look.test.tsx) | 2 of 2 pass
