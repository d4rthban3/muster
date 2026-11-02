---
description: Builder: run the two checks and send the READY report
argument-hint: <branch or piece>
---

Use the `ready-checks` skill for: $ARGUMENTS.
Run the two checks (all tests on the combined code via `run-checks`; whole-project search for the pattern just
changed). Only if both pass, send the six-line READY report (`muster/REPORT.md`) to the inspector and add it to `muster/BOARD.md`.
If either fails, report what failed and stop; do not post READY.
