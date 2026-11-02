---
description: Manager: write one order for one finished piece of work
argument-hint: <piece and role>
---

Use the `one-order-per-piece` skill. Write one order for: $ARGUMENTS.
Check first that: it names a branch or item; the done-condition is stated; out of scope is stated; files do not overlap
with another running order. Then post it to `muster/BOARD.md` as a NOTE header addressed to the role and show it to the
user. If the user has not told you which role does it, ask.
