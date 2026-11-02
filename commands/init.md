---
description: Set up the crew method in this project (CLAUDE.md, muster/ folder with roster, decisions log, board, checks list)
---

Set up the crew method in the current project. Work from the templates in `${CLAUDE_PLUGIN_ROOT}/templates/`.

1. Create `muster/` if missing. For each of `CREW.md`, `DECISIONS-LOG.md`, `BOARD.md` copy the template from
   `${CLAUDE_PLUGIN_ROOT}/templates/` **only if the target does not exist**; never overwrite. Create an empty
   `muster/BOARD-ARCHIVE.md` and an `inspection/` folder (with a `.gitkeep`).
2. Create `muster/CHECKS.md` if missing, with a header explaining the format (`<folder> | <command> | <expected count>`,
   one per line) and, from the project's real test setup (package.json scripts, pytest, go test, etc.), propose the
   test commands. Ask the user to confirm the expected counts after a first run; do not invent counts.
3. `CLAUDE.md`: if the project has none, copy `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md`. If it exists, show the
   user the sections that would be added and append them only after a yes. Fill in nothing you do not know.
4. Ask the owner two things, one at a time: (a) who is "the owner" (their name for the decisions log), (b) whether
   routine work may run without asking apart from spend, keys and deletes (default yes). Record the answer as decision
   D-001 in `muster/DECISIONS-LOG.md`, replacing the placeholder date in D-001, D-002 and D-003 with today's date.
5. Print what was created, what was skipped because it existed, and the next step: open one chat per role and run
   `/muster:role manager` in the first.

Do not commit anything; leave that to the user.
