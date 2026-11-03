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
setup, for the first crew):". A worker's note (never the manager's) then has the line "Your end-of-turn reply is one line:
what you sent and to whom. Never a report to the person."; then the five lines. The First line always begins with "read <plugin folder>/agents/
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
  `git worktree add '.claude/worktrees/<short-name>' 'muster/<short-name>'` (no `-b`). A renewal starts in the same copy
  as the chat it replaces.
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
Archive an old chat with the app's archive tool (never delete).

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
On `DONE: renewal <Role>_<project>_<N>`: start `<Role>_<project>_<N+1>` (three digits, counting up) the same way,
its note's First line pointing at `muster/handovers/<Role>_<project>_<N>.md`; archive the old chat; update `muster/CREW.md`.

## Second inspector
When the workers that build (builders, the designer, Agent Teacher) reach three, start `Design Inspector_<project>_001`. It checks
what people see; Inspector_<project>_001 keeps what is behind the scenes and the manager's paperwork.

## Models
| Worker | Model |
|---|---|
| Manager_<project>_001, Inspector_<project>_001, Design Inspector_<project>_001, Sketchpad_<project>_001, Agent Teacher_<project>_001 | claude-opus-5-5 |
| Builder A_<project>_001 (and B, C...), Designer_<project>_001, AI Socket_<project>_001 | claude-sonnet-5-5 |
Every chat on medium effort; on the owner's "speed up", the manager and the inspectors go to high.
