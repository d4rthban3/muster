# The report every worker sends

Every message a worker sends (to the manager, to the inspector, or back to a builder) is six lines. The first word is
always one of six: DONE, READY, PASS, FAIL, STUCK, NEED.

```
<FIRST WORD>: <job name, copied word for word from the manager's order>
What:  <what was done, one plain sentence>
Where: <where it is: the line of work and the saved version, a file, or a page address>; touches: <none, or the shared thing it touches, by name>
Why:   <the reason, or the decision it comes from>
How:   <what was checked, with real numbers, or "not checked">
Need:  <what is left out; what you need from the reader, and by when if it matters>
```

What the six first words mean:
- **DONE**: finished a job that needs no inspection.
- **READY**: finished; asking the inspector to check it.
- **PASS** / **FAIL**: the inspector's answer.
- **STUCK**: cannot go on; says why.
- **NEED**: needs something only the reader can give (an answer, a choice, a yes).

Who and when are not typed: the message carries them. Each line is one short sentence, with no lists inside a line.
No "received", no "thanks", no rules repeated, no keys or passwords.

## In a worker's own window
The full report goes only by message. In its own window a worker writes one short line saying what it sent and to
whom. Made-up example: "Sent READY to the inspector: crew switch".

## What the manager shows the owner
The whole team runs through one chat: the owner talks to the manager's chat only. There the manager shows a report
as a card: a bold title line "FIRST WORD · job name", then the parts as a light list, each a bold label and one short
sentence. Details (saved-version codes, file paths) go behind a link, never crammed in. No lists inside a line. One
Need per report. Nothing repeated from an earlier report.

Made-up example:

> **NEED · crew switch**
> - **What:** your five fixes are in both drafts; neither is saved
> - **Where:** [the rules draft](link)
> - **Why:** your review
> - **How:** each fix checked against the settled plan
> - **Need:** your word to save both files

Made-up example:
```
READY: filter button move
What:  moved the filter button to the right of the pills on the home page
Where: line of work "builder/filter-move", saved version 4f2a91c; touches: none
Why:   the owner's order 7, "filter button right of the pills"
How:   all 48 tests pass on the combined work, and the one other "filter-btn" place was moved too
Need:  nothing; ready for the inspector
```
