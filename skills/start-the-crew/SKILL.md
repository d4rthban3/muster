---
name: start-the-crew
description: How the manager (or the setup) starts, renews and archives the crew's chats. Use at setup, when adding a worker, when a worker sends "DONE: renewal", and when three workers build so a second inspector is needed.
---

# start-the-crew

Every worker is a whole chat with: its name (role, underscore, three digits), its own copy of the project folder, the
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
setup, for the first crew):", then the five lines. The First line always begins with "read <plugin folder>/agents/
<role>.md and follow it for the rest of this chat" (the app cannot start a chat as a worker type), and names the
main project folder's full path for the rules page.

## In the desktop app
Use the app's tool for starting a session. Chat names there take only small letters, digits and dashes, so give it:
- the short name: the worker's name in small letters with dashes (made-up example: `builder-a-001`);
- the title: the worker's real name (`Builder_A_001`), which is what the owner sees;
- the model and effort from the worker's definition, and this chat's permission mode;
- the folder: the main project folder itself for the manager (no copy); its own copy (a separate worktree) for every
  other worker;
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
the setup page. Move each crew chat into it one by one. The chat that ran the setup is not a crew chat: it stays out of the
group. Moving chats into a group needs the owner's OK in some permission modes: ask first, in one question with two buttons
("I move them now" or "you drag them yourself"). On the first, use the app's sidebar tools; if the move is refused, tell the owner plainly
how to drag each chat into the group. Renewals go in the same group. Worker names stay as they are (Manager_001 ...),
so two projects can both have a Manager_001.
Archive an old chat with the app's archive tool (never delete).

## In a terminal
Write the project folder's path in single quotes in every command, with each apostrophe as `'\''` (see
"Folder paths in commands" in the setup command), because a project name may hold characters such as `$`.
- **The manager** is the one chat the owner opens themselves, in the main project folder, so it works on the shared
  files directly. Give them this one line to type there (in plain words):
  `claude -n Manager_001 --agent muster:manager --model claude-opus-5-5 --effort medium --permission-mode <this chat's mode> "<its starting note>"`
- **Every other worker** starts in the background, in its own copy, with one command from the project folder:
  ```
  claude --bg --name <Name_001> --agent muster:<role> --model <model> --effort medium --permission-mode <this chat's mode> --worktree <name-001> "<starting note>"
  ```
  It keeps running after the terminal closes.
- Names stay as the owner sees them (Manager_001 ...); to keep them apart from another project's crew underneath,
  write each background chat's id (printed when it starts) into `muster/CREW.md` and use the id, not the name, in
  `claude attach`, `claude stop` and renewals.
- Tell the owner, in plain words, how to look in on a worker: from the project folder, `claude agents --cwd .` shows
  only this project's crew; pick a chat to open it; the left arrow key returns.
- Archive: `claude stop <its id>`. The conversation is kept and can be opened again with `claude attach <its id>`.
- The folder must have been opened in Claude once (the trust question). If a start fails with "not trusted", tell the
  owner plainly to run `claude` in the project folder once and say yes; then start the chats again yourself.

## Renewal
On `DONE: renewal <Name_00N>`: start `<Name_00N+1>` the same way, its note's First line pointing at
`muster/handovers/<Name_00N>.md`; archive the old chat; update `muster/CREW.md`.

## Second inspector
When the workers that build (builders, the designer, Agent_Teacher) reach three, start `Design_Inspector_001`. It checks
what people see; Inspector_001 keeps what is behind the scenes and the manager's paperwork.

## Models
| Worker | Model |
|---|---|
| Manager_001, Inspector_001, Design_Inspector_001, Sketchpad_001, Agent_Teacher_001 | claude-opus-5-5 |
| Builder_A_001 (and B, C...), Designer_001, AI_Socket_001 | claude-sonnet-5-5 |
Every chat on medium effort; on the owner's "speed up", the manager and the inspectors go to high.
