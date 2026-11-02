---
name: usage-habits
description: Keep a chat's usage low without losing required work. Use at the start of a session, before reading a big file, before taking screenshots, before a long run of tool calls, and when a chat has run long or a stage just finished. Says what to read in part, what to batch, when to hand over to a fresh chat, and what is never skipped.
---

# usage-habits

Every turn re-reads the whole conversation, so a long chat costs more with every turn and big tool results are paid
for again each turn. These habits cut that cost; they never change what must be done.

## Never skipped
- The project `CLAUDE.md`, your area's `CLAUDE.md`, and any read a rule says to do "in full".
- The board before finishing, the board entry after a piece of work, the look at what is staged before every commit,
  and every rule in `CLAUDE.md` and `muster/CREW.md`. A saving never means skipping a check or an approval.
- Missing stays missing: if you did not read something, say so.

## Habits
1. **Read big files in part**: search, or read an offset and limit. Don't re-read a file you just edited. For the
   board use the digest. Read your rules page, not the whole decisions log.
2. **Cut command output before it returns, but never cut evidence.** Filter or limit it. When output is evidence (a
   test printout), save it whole to a file first and cut only what comes back to the chat.
3. **Prefer text to pictures.** Read a page as text unless how it looks is the question; reduced size when full size
   isn't needed.
4. **Batch independent calls** in one turn. Never batch a save, push or message with the check that decides whether
   it should happen.
5. **The six-line report**: write only to ask, answer or report; no "received"/"thanks"; never cut a finding.
6. **Don't spawn helpers, change your own model/effort, or open extra sessions** to save effort; that's the manager's
   and owner's call.
7. **Renew after the app's first summary**: at the next natural break write `muster/handovers/<your name>.md` (only
   work in progress: what is open, the files that matter, the next step, anything you did not verify) and send the
   manager `DONE: renewal <your name>`. The manager starts the fresh chat and archives this one.

## Do not
- Change a rule, setting or another role's files to save usage.
- Trim a report so it can no longer be checked.
