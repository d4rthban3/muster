---
description: Manager: write one order for one finished piece of work
argument-hint: <piece and role>
---

Use the `one-order-per-piece` skill. Write one order for: $ARGUMENTS.
Check first that: it names a branch or item; the done-condition is stated; out of scope is stated; files do not overlap
with another running order. Then send it to the worker and add it to `muster/BOARD.md`. If the owner has not said something the order needs
(how it should look, what counts as done, what is in or out), ask the owner first; never fill it in.
