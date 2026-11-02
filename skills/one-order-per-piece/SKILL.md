---
name: one-order-per-piece
description: How a manager writes orders. Use when the manager is handing work to a builder or inspector. One order per finished piece of work, naming the branch or item, with a clear done-condition.
---

# one-order-per-piece

## Rules
1. **One order per finished piece**, never one per role or per step. If a piece needs a builder and then an
   inspector, the inspector's order comes when READY arrives.
2. **Name the branch or item.** The order must be unambiguous about where the work lives.
3. **State done.** What the READY line must show (tests, the search, what it touches).
4. **State what is out of scope**, so the builder lists unrelated problems instead of fixing them.
5. **Two builders at once only when their files do not overlap.** Say which files each owns.
6. **Orders carry no secrets.**

## Order template
```
To: <role>    Piece: <name>    Branch: <branch>
Goal: <one sentence>
Files you own: <list>        Out of scope: <list>
Done when: tests green on combined code; whole-project search for <pattern>; READY line posted.
```
