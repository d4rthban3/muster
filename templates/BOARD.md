# Board

The record of finished pieces: one entry per finished piece, in the six-line report shape.
It wakes nobody: if someone must act, also send them a direct message.
When messages are paused, the report goes here instead, addressed to its reader; the manager reads the board at a session's start, before a session ends, and when a worker says its report is on the board.

## Rules
1. At the start of a session and before a session ends, run `/muster:board <your name>`. Read in full every entry addressed to you or to ALL.
2. Answer every open entry addressed to you before new work.
3. Close an entry (`Status: done`) when it is answered; do not delete it.
4. The manager moves entries older than 48 hours to `BOARD-ARCHIVE.md` when this file passes 50 KB.
5. No keys, passwords or private files on the board.

## Entry format
One header line (date | first word | from -> to | job name), then the six-line report.
Made-up example:
```
### 2026-01-31 | READY | Builder A_MyProject_001 -> Inspector_MyProject_001 | filter button move
Status: open
READY: filter button move
What:  moved the filter button to the right of the pills on the home page
Where: line of work "builder/filter-move", saved version 4f2a91c; touches: none
Why:   the owner's order 7
How:   all 48 tests pass on the combined work, and the one other "filter-btn" place was moved too
Need:  nothing; ready for the inspector
```

## Entries
