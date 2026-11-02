---
name: board-digest
description: Find the board entries you must read without reading the whole board. Use at the start of every work session and again before finishing. It prints in full every open entry addressed to your role or to ALL, and other open entries as headers only; anything it cannot read it says so.
---

# board-digest

Saves reading the whole board. You still read the board's rules once and still read in full every entry addressed to
you or to ALL; this only finds them.

## Steps
1. Run it from inside the project with your chat's name (Manager_001, Builder_A_001, Inspector_001, ...):
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/board-digest/scripts/board_digest.py" <your name>`
2. Read what it prints, in full. Check the first line names the real `muster/BOARD.md` and when it last changed. The next
   line says how many entries concern you (printed in full), how many others are open (headers only), how many are
   done or closed (hidden), and how many files it could not read.
3. Answer every open entry addressed to you before new work.
4. Open a headers-only entry in full only if its title touches your work.
5. If it says it found no board, or the counts look wrong, read `muster/BOARD.md` by hand. Missing stays missing.
6. Before you finish, run it again and close what is done (`Status: done`).

## Do not
- Treat the digest as the whole board. Closed entries live in `muster/BOARD-ARCHIVE.md`.
- Edit the script or point it at another file.
