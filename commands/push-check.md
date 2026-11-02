---
description: Before any push, see exactly what would go out and what else is waiting
argument-hint: <number of commits you expect to push>
---

Use the `held-work` skill. Run `push_check.sh` with the expected count ($ARGUMENTS; ask if none was given) and report:
the commits it would send, other branches holding unpushed work, uncommitted files, and whether the count matches.
Do not push.
