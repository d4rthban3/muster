---
name: start-the-crew
description: How the manager (or the setup) starts, renews and archives the crew's chats. Use at setup, when adding a worker, when a worker sends "DONE: renewal", and when three workers build so a second inspector is needed.
---

# start-the-crew

Every worker is a whole chat with: its name (role, underscore, three digits), its own copy of the project folder, the
model and effort from its definition, and the five-line starting note (`muster/START-NOTE.md`) as its first message.

## In the desktop app
Use the app's tool for starting a session: give it the name, the model and effort from the worker's definition, its
own folder copy (a separate worktree), and the five-line note as the first message. Archive an old chat with the
app's archive tool (never delete).

## In a terminal
For each worker, run one command from the project folder:
```
claude --bg --name <Name_001> --agent muster:<role> --model <model> --effort medium --worktree <name-001> "<five-line note>"
```
- The chat runs in the background with its own folder copy and keeps running after the terminal closes.
- Tell the owner, in plain words, how to watch and type into a chat: `claude agents` shows them all;
  `claude attach <Name_001>` opens one; the left arrow key returns.
- Archive: `claude stop <Name_001>`. The conversation is kept and can be opened again with `claude attach`.
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
