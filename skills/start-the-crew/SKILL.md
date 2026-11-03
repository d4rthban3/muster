---
name: start-the-crew
description: How the manager (or the setup) starts, renews and archives the crew's chats. Use at setup, when adding a worker, when a worker sends "DONE: renewal", and when three workers build so a second inspector is needed.
---

# start-the-crew

Every worker is a whole chat with: its name (role, underscore, three digits), its own copy of the project folder, the
model and effort from its definition, the five-line starting note (`muster/START-NOTE.md`) as its first message, and
**the same permission mode as the chat starting it** (the owner's own choice carries over; never a looser one). Never
try to turn off the app's message limits.

## In the desktop app
Use the app's tool for starting a session. Chat names there take only small letters, digits and dashes, so give it:
- the short name: the worker's name in small letters with dashes (made-up example: `builder-a-001`);
- the title: the worker's real name (`Builder_A_001`), which is what the owner sees;
- the model and effort from the worker's definition, its own folder copy (a separate worktree), and this chat's
  permission mode;
- the five-line note as the first message. The app cannot start a chat as a worker type, so the note's First line
  begins with "read <plugin folder>/agents/<role>.md and follow it for the rest of this chat".
If the app says the folder is not trusted, tell the owner plainly to say yes to the trust box, then try again.
**Sidebar group:** every project's crew sits in its own sidebar group named after the project (the project folder's
name). Create the group with the app's sidebar tools if it does not exist yet, and put every crew chat in it, renewals
too. Worker names stay as they are (Manager_001 ...), so two projects can both have a Manager_001.
Archive an old chat with the app's archive tool (never delete).



## In a terminal
For each worker, run one command from the project folder:
```
claude --bg --name <Name_001> --agent muster:<role> --model <model> --effort medium --permission-mode <this chat's mode> --worktree <name-001> "<five-line note>"
```
- The chat runs in the background with its own folder copy and keeps running after the terminal closes.
- Names stay as the owner sees them (Manager_001 ...); to keep them apart from another project's crew underneath,
  write each chat's id (printed when it starts) into `muster/CREW.md` and use the id, not the name, in `claude attach`,
  `claude stop` and renewals.
- Tell the owner, in plain words, how to watch and type into a chat: from the project folder, `claude agents --cwd .`
  shows only this project's crew; pick a chat to open it; the left arrow key returns.
- Archive: `claude stop <its id>`. The conversation is kept and can be opened again with `claude attach <its id>`.
- The folder must have been opened in Claude once (the trust question). If a start fails with "not trusted", tell the
  owner plainly to run `claude` in the project folder once and say yes, then try again.

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
