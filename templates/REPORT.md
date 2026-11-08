# The report every worker sends

Every message a worker sends (to the manager, to the inspector, or back to a builder) is six lines (a DONE or READY adds a seventh, the Usage line, below). The first word is
always one of six: DONE, READY, PASS, FAIL, STUCK, NEED (the inspector may also answer OWNER CALL, see below).

```
<FIRST WORD>: <job name, copied word for word from the manager's order> [ID <role>-<job>-<number>]
What:  <what was done, one plain sentence>
Where: <where it is: the line of work and the saved version, a file, or a page address>; touches: <none, or the shared thing it touches, by name>
Why:   <the reason, or the decision it comes from>
How:   <what was checked, with real numbers, or "not checked">
Need:  <what is left out; what you need from the reader, and by when if it matters>
```

The ID is short and counts up for that role and job (made-up example: `[ID Builder A-crew switch-2]`). A message whose
ID you have already seen is a repeat: drop it, do not answer it twice.

Usage line (DONE and READY only): `Usage: ` and what can really be read, from `python3 scripts/usage.py`, for example
`Usage: session $0.31 at list price; week 41% used (resets Thu 06 Feb); read at 14:39`. When a part cannot be read it
says so ("week limit not readable"); never type a number the script did not print.

What the six first words mean:
- **DONE**: finished a job that needs no inspection.
- **READY**: finished; asking the inspector to check it.
- **PASS** / **FAIL**: the inspector's answer.
- **OWNER CALL** (inspector only): a thing only the owner can decide; goes to the manager, who asks the owner.
- **STUCK**: cannot go on; says why.
- **NEED**: needs something only the reader can give (an answer, a choice, a yes).

Who and when are not typed: the message carries them. Each line is one short sentence, with no lists inside a line.
No "received", no "thanks", no rules repeated, no keys or passwords.

## In a worker's own window
The full report goes by message. In its own window a worker posts a short card for the owner to read there: a bold
title line "FIRST WORD · job name", then two or three bullet lines (what, the result with real numbers, what is left
or what it needs from him), plain words, files as links. Made-up example: title "READY · crew switch", "- moved the
switch to the top bar", "- 12 of 12 checks pass; the inspector has it".

## When messages are paused, and when they resume
A paused worker writes its report on the board with the line `Paused: yes`. When it can act again (the owner typed in its chat) its first act is to close those entries: `Status: done` and the line `Paused: no`. A chat counts as paused only while its last entry on the board says `Paused: yes`; a later entry from the same chat, `Paused: no` or `Status: done` clears it. A worker that cannot write the main board leaves a one-line file `.muster-paused` in its own folder (deleted on resume).

## Choices written out
**The letters are the markers.** When choices are written out, each is its own line starting with the bold letter,
with no bullet dot in front (never a bullet with "A." inside it). Leave a blank line between the choices so each
shows on its own line. Made-up example:

**A.** A web page you open in your phone's browser. *(my pick)*

**B.** A real iPhone app from the App Store.

**C.** Both, starting with the web page.

## A waiting question
A waiting question always comes with its choices. Whenever you mention a question still waiting on the owner,
resend only its buttons (the end-of-turn box, or the app's choice card for three or four) with a one-line question
naming the choices; do not repeat the full lettered text. Never refer to it as
"A or B" or "the question above".

## Every file named is a link
In every reply and report a person reads, write each file you name as a clickable
link, for example [muster/OWNERS-LIST.md](muster/OWNERS-LIST.md), never as bare text or a code span. A file outside
your own folders may not open from the link in the app; still link it and say where it is.

## What the manager shows the owner
The manager shows the owner only a question, a yes he must give (money, keys, deleting), "<worker> is waiting for you:
type in <chat>" (one linked line), and "the crew is idle, here's what's next" with buttons. It relays no LIVE, PASS,
DONE or Closed cards and no progress (D-021); each worker posts its own update in its own window. When the manager does
show a report that needs the owner's answer, it is a card: a bold title line "FIRST WORD · job name", then each part as its own bullet line, in the same order
(what, where, why, how), with the label words ("What:", "Where:" and the rest) left out. Never a paragraph.
Details (saved-version codes, file paths) go behind a link, never crammed in. No lists inside a line. A Need becomes
the question at the bottom, with its buttons. Nothing repeated from an earlier report.
Messages between chats keep all six labelled lines, for clean checking later.

Made-up example:

> **NEED · crew switch**
> - your five fixes are in both drafts; neither is saved
> - [the rules draft](link)
> - from your review
> - each fix checked against the settled plan
>
> Save both files now: yes, or not yet?

Made-up example:
```
READY: filter button move
What:  moved the filter button to the right of the pills on the home page
Where: line of work "builder/filter-move", saved version 4f2a91c; touches: none
Why:   the owner's order 7, "filter button right of the pills"
How:   all 48 tests pass on the combined work, and the one other "filter-btn" place was moved too
Need:  nothing; ready for the inspector
```
