# Muster protocol (for a second computer, and for anyone new)

Read this before every session; it is short on purpose. The full rules are `muster/CLAUDE.md`.

- **The owner's words come first**, taken literally. Anything that is not literal goes back to him as a question; nobody picks for him.
- **One writer per file.** Only the manager changes the owner's list, the decisions log, the crew list and the rules pages. A second computer reads them and writes only in its own workspace.
- **Reports** are six lines: `FIRST WORD: job [ID ...]`, What, Where (with `touches:`), Why, How (real numbers), Need. A READY shows a test count and a Usage line.
- **Orders** name the job, quote the owner's words, say what is owned and what is out, and what done looks like.
- **Nobody passes their own work.** A builder sends READY to the inspector; only an inspector's PASS lets work go live.
- **Never override the other computer.** Neither computer gives the other orders; what one needs from the other goes to the founder as a question.
- **Before every session** read, in order: this page, the builders' change log (`BUILDERS-LOG.md`, new lines only), the rules, the board, the other computer's CHANGES.md. After every session write one entry in your own CHANGES.md.
- **Rules are code where a script can check them** (hooks and `scripts/check-edition.py`); everything else is judgment, and when unsure you send a NEED, never a guess.
- **Branches and identity:** your own git name, branches that start with your computer's name and a slash.
