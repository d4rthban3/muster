---
name: usage-habits
description: Keep a chat's usage low; use at session start, before a big read or a long run.
---

# usage-habits

The short rule is "Usage first" at the top of `muster/CLAUDE.md`; this skill is its detail. Money and paid runs: skill `spend-diligence`.

Every turn re-reads the whole conversation, so a long chat costs more with every turn and big tool results are paid
for again each turn. These habits cut that cost; they never change what must be done.

## Never skipped
- The project `CLAUDE.md`, your area's `CLAUDE.md`, and any read a rule says to do "in full".
- The board before finishing, the board entry after a piece of work, the look at what is staged before every commit,
  and every rule in `CLAUDE.md` and `muster/CREW.md`. A saving never means skipping a check or an approval.
- Missing stays missing: if you did not read something, say so.

## Habits
0. **Check with small exact commands** (a count, a status code, one line); reuse proof already made (the free test run on the same version) instead of repeating it; near the limit ship what passed, park the rest and say what was left out.
1. **Read big files in part**: search, or read an offset and limit. Don't re-read a file you just edited. For the
   board use the digest. Read your rules page, not the whole decisions log.
2. **Cut command output before it returns, but never cut evidence.** Filter or limit it. When output is evidence (a
   test printout), save it whole to a file first and cut only what comes back to the chat.
3. **Prefer text to pictures.** Read a page as text unless how it looks is the question. When it is, the proof the owner
   asked for stays (a screenshot of every visible change before READY) but costs little:
   - a helper (subagent) takes and looks at the picture and returns one line plus the saved file's link, so the picture itself stays out of your chat;
   - save it small: the changed region, or a reduced scale;
   - the inspector opens the builder's saved file once instead of taking it again, and takes its own only if that file is missing or of another saved version;
   - never take or look at a picture twice on the same saved version.
4. **Batch independent calls** in one turn. Never batch a save, push or message with the check that decides whether
   it should happen.
5. **Message only when someone must act**, one bundled note per worker, as a data record; no "received"/"thanks"; never cut a finding.
6. **Don't spawn helpers, change your own model/effort, or open extra sessions** to save effort; that's the manager's
   and owner's call.
7. **Compact in place** (D-039): a crew chat's conversation is compacted by the app at about 130 000 tokens (160 000 for a manager) and the chat carries on; it does not renew
   because of a summary or a size. A PreCompact hook first writes the chat's open job, branch, saved version and next step on the board.

## Do not
- Change a rule, setting or another role's files to save usage.
- Trim a report so it can no longer be checked.
