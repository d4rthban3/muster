---
name: board-digest
description: Find the board entries you must read without reading the whole board. Use at the start of a work session, before a session ends, and when a worker says its report is on the board; not every turn. It prints in full every open entry addressed to your role or to ALL, and other open entries as headers only; anything it cannot read it says so.
---

# board-digest

Saves reading the whole board. You still read the board's rules once and still read in full every entry addressed to
you or to ALL; this only finds them.

## Steps
1. Run it from inside the project with your chat's name (with no name it reads as Manager) (Manager_<project>_001, Builder A_<project>_001, Inspector_<project>_001, ...):
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/board-digest/scripts/board_digest.py" "<your name>"`
2. Read what it prints, in full. Check the first line names the real `muster/BOARD.md` and when it last changed. The next
   line says how many entries concern you (printed in full), how many others are open (headers only), how many are
   done or closed (hidden), and how many files it could not read.
3. Answer every open entry addressed to you before new work.
4. Open a headers-only entry in full only if its title touches your work.
5. If it says it found no board, or the counts look wrong, read `muster/BOARD.md` by hand. Missing stays missing.
6. Before a session ends, run it again and close what is done (`Status: done`). A worker NEED, STUCK or pause you have passed on counts as handled: write `Status: routed` on it, or post your own entry on the same job; the stop check then stops asking for it.

## The "Waiting on:" line
The digest prints it. The manager alone runs it with `--write-waiting` to keep the one line at the top of `muster/BOARD.md`
current; it changes nothing else in the file. Everyone else never writes the board with it.

## Do not
- Treat the digest as the whole board. Closed entries live in `muster/BOARD-ARCHIVE.md`.
- Edit the script or point it at another file.
