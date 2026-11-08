# <Computer name> Workspace — change log

This computer's own log. Appended by any AI working on this computer after every session, newest entry at the top. One entry per session, six lines, full file paths. No keys, no passwords, no private credentials, ever. A missing entry is a breach of the protocol.

**Only this computer writes here.** The other computer's log is read, never written. Read the other computer's log before every session.

## Entry format (made-up example below)
```
DONE: <short change name — the same in every entry about it>
What:  <what was done overall, one plain sentence>
Where:
  - <ACTION>  <full file path>  L<start>-L<end>  (<one-line annotation>)
  - <ACTION>  <full file path>  (<one-line annotation>)
  Branch: <branch name> | Commit: <hash, or "not committed">
Why:   <the reason or the founder's instruction>
How:   <what was checked, with real numbers, or "not checked">
Need:  <what is left for the next builder, or "nothing">
```
ACTION is one of ADDED / EDITED / DELETED / RENAMED / MOVED. One line per file touched; no file is left out, even a one-line edit. The first word may be DONE, READY, PASS, FAIL, STUCK or NEED, as in `muster/REPORT.md`.

Made-up example:
```
DONE: header colour
What:  made the shop header navy
Where:
  - EDITED  Shop/site/header.css  L4-L9  (navy background)
  Branch: computer2/header | Commit: 4f2a91c
Why:   the founder asked for a navy header
How:   page opened on this computer; 3 of 3 checks pass
Need:  nothing
```

## Log
