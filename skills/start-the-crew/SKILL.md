---
name: start-the-crew
description: How the manager (or the setup) starts, renews and archives the crew's chats. Use at setup, when adding a worker, when a worker sends "DONE: renewal", and when three workers build so a second inspector is needed.
---

# start-the-crew

Every worker is a whole chat with: its name (role, underscore, project name, underscore, three digits), its own copy of the project folder, the
model and effort from its definition, the five-line starting note (`muster/START-NOTE.md`) as its first message, and
**the same permission mode as the chat starting it** (the owner's own choice carries over; never a looser one). Never
try to turn off the app's message limits.

## Where each chat works
- **The manager works in the main project folder**, never in a copy: the owner's list, the rules pages, the board and
  the crew list are one shared copy there.
- **Every other worker works in its own copy** of the project folder, and reads the crew's shared files from the main
  project folder (give it that folder's full path in its starting note).

## The starting note
The first message of every new chat begins with the line "Your five-line starting note, from the manager (or from the
setup, for the first crew):". A worker's note (never the manager's) then has the line "Your end-of-turn reply is a short card for the owner to read in your own window (title, two or three bullets); the full report still goes by message." and the line "Re-read your rules page before starting each new order." and the line "Computer use only on the manager's order naming the owner's words and the one app; never the whole screen or the clipboard; if a step needs more, send STUCK."; then the five lines. The First line always begins with "read <plugin folder>/agents/
<role>.md and follow it for the rest of this chat" (the app cannot start a chat as a worker type), and names the
main project folder's full path for the rules page.

## In the desktop app
Use the app's tool for starting a session. Chat names there take only small letters, digits and dashes, so give it:
- the short name: the role in small letters with dashes, plus the digits (made-up example: `builder-a-001`);
- the title: the worker's full name, `<Role>_<project>_<digits>` (made-up example: `Builder A_MyProject_001`), which
  is what the owner sees;
- the model and effort from the worker's definition, and this chat's permission mode;
- the folder: the main project folder itself for the manager (no copy). For every other worker, **make its copy
  yourself first**: the app cannot make copies of a project folder it has no record of, which is every folder setup
  has just made, so its own copy option fails there. From the main project folder run
  `git worktree add '.claude/worktrees/<short-name>' -b 'muster/<short-name>'` (made-up example:
  `git worktree add '.claude/worktrees/builder-a-001' -b 'muster/builder-a-001'`; `.claude/` is kept out of saved
  versions), then start the worker in that copy's full path as a plain folder, with the app's own copy option off. If
  that copy's folder already exists, use it as it is; if only its branch exists, run
  `git worktree add '.claude/worktrees/<short-name>' 'muster/<short-name>'` (no `-b`). If git says the copy is "missing but already
  registered", run `git worktree prune`, then add it again. A renewal gets **its own new copy**, named for its role
  and its new number (see "Renewal"); never the old chat's copy and never another role's.
- the starting note as the first message.
**Order:** start the manager first, in the main folder, and wait until it is running; only then start the other
workers (their copies inherit the folder's trust).
**Trust:** the app starts no chat in a folder it has not been told to trust. If a start is refused for trust, tell the
owner in plain words: look for a trust box in the app and press Trust (or Yes); if an older trust box from another
folder is still waiting, answer that one first, then the box for this folder appears. When they say they have pressed
it, **start the chats again yourself**; never leave the owner to start them by hand.
**Top level, each on its own:** a chat started from another chat sits under it in the sidebar. Every crew chat must be
its own top-level chat: right after starting each one (the first crew, renewals and new workers alike), detach it to
the top level with the app's session tools. No crew chat sits under the manager or under the chat that ran the setup.
**Sidebar group:** every project's crew sits in its own sidebar group named with the project name the owner gave on
the setup page. Once every crew chat is running, make the group (or use one with that exact name) and move each crew
chat into it one by one. Never skip this step or leave it silently undone: if any chat is not in the group at the end,
say so in one line with what to do. The chat that ran the setup is not a crew chat: it stays out of the
group. Moving chats into a group needs the owner's OK in some permission modes: ask first, in one question with two buttons
("I move them now" or "you drag them yourself"). On the first, use the app's sidebar tools; if the move is refused, tell the owner plainly
how to drag each chat into the group. Renewals go in the same group. Each name carries its project, so two
projects' crews never share a name.
Archive an old chat with the app's archive tool (never delete). Archiving is automatic, without asking the owner: any chat whose work passes to another chat (a renewal, a replacement, a role ending) is archived once its handover is written and the chat taking over is running. Owner's words: "that archive should be automatic so long as the old workers are handed off and ready to be archived." (D-005).

## In a terminal
Write every value that holds the project name in single quotes, with each apostrophe as `'\''`: the project
folder's path, the chat name (`-n`, `--name`) and the starting note (see "Quoting in commands" in the setup command),
because a project name may hold characters such as `$` or an apostrophe. Never use double quotes for these.
- **The manager** is the one chat the owner opens themselves, in the main project folder, so it works on the shared
  files directly. Give them this one line to type there (in plain words):
  `claude -n 'Manager_<project>_001' --agent muster:manager --model claude-opus-5-5 --effort medium --permission-mode <this chat's mode> '<its starting note>'`
- **Every other worker** starts in the background, in its own copy, with one command from the project folder:
  ```
  claude --bg --name '<Role>_<project>_001' --agent muster:<role> --model <model> --effort medium --permission-mode <this chat's mode> --worktree <name-001> '<starting note>'
  ```
  It keeps running after the terminal closes.
- Names stay as the owner sees them (made-up example: `Manager_MyProject_001`); to keep them apart from another project's crew underneath,
  write each background chat's id (printed when it starts) into `muster/CREW.md` and use the id, not the name, in
  `claude attach`, `claude stop` and renewals.
- Tell the owner, in plain words, how to look in on a worker: from the project folder, `claude agents --cwd .` shows
  only this project's crew; pick a chat to open it; the left arrow key returns.
- Archive: `claude stop <its id>`. The conversation is kept and can be opened again with `claude attach <its id>`.
- The folder must have been opened in Claude once (the trust question). If a start fails with "not trusted", tell the
  owner plainly to run `claude` in the project folder once and say yes; then start the chats again yourself.

## Renewal
On `DONE: renewal <Role>_<project>_<N>`: start `<Role>_<project>_<N+1>` (three digits, counting up) the same way, in **its own new copy** (D-025): get the folder's short name from `python3 scripts/crew-plan.py copy-name "<Role>_<project>_<N+1>"` (made-up example: `builder-a-002`), make it from the old copy's branch so no work is lost (`git worktree add '.claude/worktrees/<short-name>' -b 'muster/<short-name>' 'muster/<old short-name>'`), and **before starting the chat** run `python3 scripts/crew-plan.py check-copy "<Role>_<project>_<N+1>" '.claude/worktrees/<short-name>'`: if it says REFUSED, the folder belongs to another role, so make the right one first. A renewed chat never runs in another role's old copy. The manager and the inspectors that work in the main folder keep it.
its note's First line pointing at `muster/handovers/<Role>_<project>_<N>.md` (only if the old chat wrote one; a chat with no job in progress writes none). In the desktop app, move the new chat to the
top level and file it in the project's sidebar group (one button if the app needs the owner's OK; never left nested
under the manager). Then archive the old chat automatically, without asking the owner (once its handover is written and the new chat is running; never deleted), and update `muster/CREW.md`.

## Two builders, only when the work allows
Builder A is the only builder by default. Start `Builder B_<project>_001` (same way as Builder A, its own folder copy,
the same model and effort) only when two open pieces of work can run side by side, and stop it when they cannot.
**Do the pieces overlap?** Read each order's "Owns" line. They do not overlap only if (1) no file or folder named in one
is the same as, or inside, one named in the other, and (2) neither needs a change the other must land first (for
example a script one calls and the other writes). Version files, the release file and CHANGELOG.md do not count: every
piece touches them and shipping (`scripts/ship.sh`) rebases them. Not sure? Treat it as overlapping: one builder.
**Start** Builder B only when at least two open orders fit the test above and each has a builder-sized piece to do; give
it only an order of the second kind. **Stop** it when its last piece has passed and been pushed and no open order fits
the test: write its handover only if a job is in progress, then archive it automatically, without asking the owner
(D-005; never delete), and update `muster/CREW.md`. Builder B counts as a building worker for the "three workers" rule below.

## Inspectors scale with the builders (D-025)
One inspector for every three builders, at least one: `python3 scripts/crew-plan.py inspectors <number of builders> --project <project>` prints how many and which builder's READYs go to which. Builders A to C go to `Inspector_<project>_001`, D to F to `Inspector B_<project>_001`, and so on (each READY names its inspector). When a builder is added that makes the count pass a multiple of three, start the next inspector the same way as any chat (own copy not needed: inspectors work in the main folder and write no project files; same model and effort, top level, in the project's sidebar group) before the new builder's first order, and tell the builders their inspector in their next order. When the builders shrink, archive the extra inspector automatically once its READYs are answered (D-005; never deleted). Inspectors do not check each other's work; the Design Inspector below is a separate rule.

## Small checks run inside the manager's chat (D-025)
A small piece is checked by a fresh, separate checker started inside the manager's chat, not by a message to an inspector chat; a big piece goes to an inspector chat. Ask `python3 scripts/crew-plan.py size <base> <branch>`: SMALL means at most 3 files and 60 changed lines, nothing in engine, data, database or deploy folders, nothing a visitor sees, and no rules or protocol file; BIG, or not sure, goes to an inspector. For a small piece, start a fresh subagent from the inspector definition (a different hand from the builder, and never the manager judging for itself), give it the READY and ask for a PASS or FAIL in the six-line shape; post its answer on the board, word for word, addressed to the builder (`Status: open`), with the line `Checked by: fresh checker`. The checker never writes project files. One checker per piece; a FAIL is fixed by the builder and checked by a new checker.

## Second inspector
When the workers that build (builders, the designer, Agent Teacher) reach three, start `Design Inspector_<project>_001`. It checks
what people see; Inspector_<project>_001 keeps what is behind the scenes and the manager's paperwork. Like every chat the
manager starts later (renewals, new workers, add-ons), it goes to the top level and into the project's sidebar group.

## Models
| Worker | Model |
|---|---|
| Manager_<project>_001, Inspector_<project>_001, Design Inspector_<project>_001, Sketchpad_<project>_001, Agent Teacher_<project>_001 | claude-opus-5-5 |
| Builder A_<project>_001 (and B, C...), Designer_<project>_001, AI Socket_<project>_001 | claude-sonnet-5-5 |
Every chat on medium effort; on the owner's "speed up", the manager and the inspectors go to high.
