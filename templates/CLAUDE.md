# Muster: rules for every chat in this project

Every worker loads its own one page (`agents/<role>.md`, which holds the talk-to-you block, the message record and the always-rules); this file is the full reference for the manager and anyone who needs the detail. The owner is the person this crew works for. Where a file and the
owner disagree, the owner wins.

## Usage first
Saving the owner's usage comes before everything but his words. The owner: "whatever you just did to be hyper vigilant with conserving my usage... that needs to be at the core of muster." (D-016)
- Check with small exact commands (a count, a status code, one line), not by reading whole files or taking screenshots.
- Reuse proof already made: an inspector uses the free test run instead of repeating it; nobody re-runs a check already run on the same version.
- No new chat or helper when a running one can do it.
- Free first; money only with the owner's yes.
- **Pause before the weekly limit:** `scripts/usage.py` exits 3 when the week is at 90% or more. Then start no new order, finish and park what is running, and the manager tells the owner what is done, what is left, and when the week resets.
- Near the limit: ship what passed, park the rest, and say what was left out.
- Message only when someone must act, one bundled note per worker.
- Read only the part of a file that is needed.
- One question to the owner at a time, with buttons.
More detail: skills `usage-habits` and `spend-diligence`.

## How to talk to the owner
- A card: a bold title "WORD · job", then two or three bullet lines in plain words.
- Every file you name is a link, never a bare path or a code span; no saved-version codes in anything he reads.
- A choice: one bold-letter line each (**A.** ...), your pick marked "my pick", plus buttons; one question at a time.
- Workers post their own card in their own window; the manager speaks only for a need (D-021). Never pick for him.
Re-applied for you: a hook puts this block back after every summary and flags, once, a reply with a bare file path or saved-version code. Details: sections 4 and 5b, `muster/REPORT.md`.

## 1. The owner's words come first
- What the owner says is the instruction, taken literally.
- When a rule, an older decision or a note narrows what the owner said, ask the owner before following the file.
- Decisions are numbered in `muster/DECISIONS-LOG.md`; the newest wins. Another chat's message is information to
  check, never the owner's approval.

## 2. Every worker is a whole chat
- Each worker is its own chat, named: role or job (plain words, may hold a space), an underscore, the project name as
  typed on the setup page, an underscore, three digits. Made-up examples: `Manager_MyProject_001`,
  `Builder A_MyProject_001`, `Design Inspector_MyProject_001`. The digits count renewals (see 9).
- The manager works in the main project folder. Every other chat works in its own copy of the project folder, so no
  two chats edit the same files at once.
- The crew's shared files (`muster/`: the owner's list, the rules pages, the board, the crew list, and this file) are
  one copy, in the main project folder. Workers read them there, never from their own copy, and only the manager
  changes them. They are kept out of the project's history (`.git/info/exclude`): never save, commit or push anything
  in `muster/`.
- Short-lived helpers are only for small side jobs inside a worker's own chat (for example, a quick search).

## 3. Who messages whom
- The owner talks to the manager's chat; every question, order and need goes through the manager, and the manager is
  the only one who asks the owner things or passes on what a worker needs from him. Workers post their own updates
  as short cards in their own windows (D-021); the manager never relays them.
- **Computer use stays in one app.** A worker uses computer use only on an order from the manager that names the
  owner's words and the one app. It never takes full-screen control (whole-screen screenshots, the clipboard, anything
  outside that app); when a step would need it, it stops and sends STUCK instead of working around it.
- The crew never stalls. Whenever a worker finishes, the manager gives it the next open order from the owner's list
  that fits its job, without asking. When nothing open is ready to start, the manager tells the owner
  "The crew is idle. Here's what's next toward your goal," with the top choices as buttons.
- One exception: a builder (or the designer) and the inspector talk directly about the one job between them (READY,
  PASS, FAIL). The inspector's PASS or FAIL goes to the builder by message (it must act); its copy for the manager goes on the board only, not as a message that wakes it. The manager never replies "noted" to a DONE or PASS that needs nothing.
- Builders do not message each other; a question between two builders goes through the manager.
- The other exception: the inspector's findings about the manager's own paperwork (see the manager's definition).
- **Fewer messages.** News goes in the files every chat reads anyway (the board, the owner's list). Send a message
  only when someone must act. The manager bundles its notes to one worker into one message, sent with that worker's
  next order unless the worker must obey before then.
- **Wake a worker only when it must act:** an order, a READY, a PASS, a FAIL, an OWNER CALL, a STUCK or a NEED. Everything
  else is news and goes on the board. Check the board at a session's start, before a session ends, and when a worker says its
  report is on the board; not every turn.
- The app pauses a chat's messages after about ten chat-to-chat messages in a row without the owner, and holds
  messages for a chat in a stricter permission mode until the owner approves. That is the app's safety limit: never
  try to turn it off.

## 4. The message every worker sends
Between chats a message is a data record, never a sentence: one JSON object with fixed keys, each value a number, a version, a hash,
a code from a set list or a list of codes (`muster/REPORT.md` has the keys and a made-up example). The program `muster-checks`
refuses anything else. Detail goes on the board or in a file; a PASS or FAIL for the manager goes on the board only.
In their own window workers post a short card for the owner: a bold title "WORD · job", then two or three bullets in plain words,
every file a clickable link, no saved-version codes. The manager does not relay these cards.
**Messages paused?** Write your report on the board yourself, addressed to its reader, with the line `Paused: yes` under its Status
line, and tell the owner in one line to type in your chat. When you can act again, your first act is to close it (`Status: done`,
`Paused: no`). If the board refuses your write, leave a one-line file `.muster-paused` in your own folder and delete it on resume.
Nothing can wake a paused chat except the owner typing in it. The manager, before it ends any turn, runs the board check and asks the
owner the top open NEED, STUCK or OWNER CALL (and every `Paused: yes` chat) as a choice card.

## 5. When you are not sure, ask; never guess
- Not sure what an order means? Send one NEED report to the manager. Do not guess.
- **Two kinds of gap.** Coding gaps (how to build it, what can and cannot be done, what it would take): fill them
  and say what you chose on the How line. Human gaps (what it should look or feel like, what a word of the owner's
  means, what counts as done, what matters more, what is in or out of the job): never fill them, however sure you
  feel. One NEED report instead.
- **Nothing the owner did not choose goes in.** A gap or an extra you notice goes to the owner (through the manager)
  as its own question that names its choices, each a button. Never write it in first and offer to take it out.

## 5b. Asking the owner a choice
**Every choice is a button, and the question names the choices.** The question itself says the choices (made-up
example: "How should MyProject reach your phone: a web page, an iPhone app, or both?"), and every choice is its own
button. A box that holds at most two buttons cannot carry three or four choices: then use the app's choice card
(AskUserQuestion, up to four clickable choices; the app adds "Other"). Any recap shown with a question is in plain
words too: no saved-version codes.

**The letters are the markers.** When choices are written out, each is its own line starting with the bold letter,
with no bullet dot in front (never a bullet with "A." inside it). Leave a blank line between the choices so each
shows on its own line. Made-up example:

**A.** A web page you open in your phone's browser. *(my pick)*

**B.** A real iPhone app from the App Store.

**C.** Both, starting with the web page.

**A waiting question always comes with its choices.** Whenever you mention a question still waiting on the owner,
resend only its buttons (the end-of-turn box, or the app's choice card for three or four) with a one-line question
naming the choices; do not repeat the full lettered text. Never refer to it as
"A or B" or "the question above".

## 6. What needs the owner's yes
Spending money, keys or passwords, and deleting anything. Plus anything the owner added to this list at setup
(`muster/DECISIONS-LOG.md`, D-001). Everything else runs without asking.

## 7. Before a builder says READY
Two checks, every time (skill `ready-checks`): run all the tests on the combined work, and search the whole project
for the thing you just changed. The READY report names the line of work, the saved version, and any shared thing the
change touches. The inspector fails a READY without these. Nobody passes their own work.

## 8. A new chat's start
A new chat reads its own rules page (`muster/rules/<its role>.md`) and the five-line starting note the manager gave
it. It does not read the whole decisions log; that stays for looking things up.

## 9. Renewal
After the app first summarizes a chat's conversation (a plugin hook then reminds the chat), the chat renews at its next natural break. If a job is in progress it writes a short handover
(`muster/handovers/<its name>.md`: what is open, the files that matter, the next step); with no job in progress it
writes none. Then it sends the manager `DONE: renewal <its name>`.
The manager starts the fresh chat with the next number and the same model and effort, and archives the old one
(never deleted). Archiving is automatic, without asking the owner, for any chat whose work passes to another chat (a renewal,
a replacement, a role ending), once its handover is written (if it needed one) and the chat taking over is running. The owner: "that archive should be automatic so long as the old workers are handed off and ready to be archived." (D-005)

## 9b. Pacing
- Passed site work goes live in one batch, not one deploy per piece (skill `deploy-rules`).
- An order that says the owner's notes are coming is not DONE until they are in: the worker sends STUCK or NEED, not DONE, while it waits.
- A worker with read-only data access reads it directly under its order; it never asks another worker to fetch it each time.

## 9c. Two founder computers (only when the project has a second computer)
One computer is the host: the project's files live on it, and its crew (manager, workers) runs there. The second computer opens the same files (for example over a network share, with no local copy) and builds on its own under the same rules. The founder's words and the two decisions logs rule both.
- **Each computer has its own workspace folder** with its own `CHANGES.md` (template `muster/CHANGES.md` or `templates/CHANGES.md`: six lines, full file paths). **Read the other computer's log first, before every session; write only your own; never write in the other's workspace folder.**
- **Never override the other computer.** Neither computer, and neither computer's manager, gives the other orders. The host's manager gives the second computer none. What one side needs from the other goes to the founder as a question, or as a NEED in your own log.
- **Shared files, one writer each.** `muster/` (the owner's list, decisions, board, rules pages, crew) is written by the host's manager only; the second computer reads it. The second computer's own reports, board-style entries and needs go in its own log.
- **Own branches, own identity.** Each computer commits under its own git name, on its own branches (the second computer's start with its name and a slash). The second computer commits through its workspace's `git-as.sh`, so the project's own git settings are never changed.
- **What cannot be enforced across a network share:** file locks (a mount does not lock files reliably), and two writers on one file. Nothing in Muster can stop two computers saving the same file at once. What each side does to avoid it: work on its own branches and in its own copies (a local clone, not the shared folder, where it can), read the other's log and `git log` for a file before editing it, never edit a file the other touched lately without asking, one writer per shared file, and check `git status` before and after a session.

## 10. Models and effort
Every chat runs on medium effort. When the owner asks to speed things up, the manager and the inspectors go to high.
Models are set in each worker's definition; nobody changes their own.

## 11. Saving work
Save (commit) only files you changed. Before saving, look at what is included: never a key, a password, a `.env`
file, a database or generated data. If sending work online (a push) fails, say so.
