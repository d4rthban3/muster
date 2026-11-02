---
description: Builder: run the two checks and post the READY line
argument-hint: <branch or piece>
---

Use the `ready-checks` skill for: $ARGUMENTS.
Run the two checks (all tests on the combined code via `run-checks`; whole-project search for the pattern just
changed). Only if both pass, post the READY line to `muster/BOARD.md` and tell the inspector in a five-line message.
If either fails, report what failed and stop; do not post READY.
