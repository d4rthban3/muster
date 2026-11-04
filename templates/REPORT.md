# The report every worker sends

Every message a worker sends (to the manager, to the inspector, or back to a builder) is six lines. The first word is
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
The full report goes only by message. In its own window a worker writes one short line saying what it sent and to
whom. Made-up example: "Sent READY to the inspector: crew switch".

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
The whole team runs through one chat: the owner talks to the manager's chat only. There the manager shows a report
as a card: a bold title line "FIRST WORD · job name", then each part as its own bullet line, in the same order
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
