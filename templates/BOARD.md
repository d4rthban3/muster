# Board

The record of finished pieces. One entry per finished piece (READY, PASS, LIVE) with a link to the detail.
It wakes nobody: if someone must act, also send them a direct message.

## Rules
1. At the start of a session and before finishing, run `/muster:board <ROLE>`. Read every entry addressed to you or to
   ALL in full.
2. Answer every open entry addressed to you before new work.
3. Close an entry (`Status: done`) when it is answered; do not delete it.
4. The manager moves entries older than 48 hours to `BOARD-ARCHIVE.md` when this file passes 50 KB.
5. No keys, passwords or private files on the board.

## Entry format
Header is one line; `Status:` is the next line. Names in the header are role names (or ALL).
```
### 2026-01-31 | READY | builder-a -> inspector | login fix
Status: open
Branch: builder/login-fix   Commit: abc1234
Touches: none | shared database | file store | outside connection (name it)
Checks: all tests pass (N of N); searched whole project for <pattern>, no other hit
Detail: <link or path>
```

## Entries
