# Muster for Cursor (full crew) — UNTESTED in Cursor

Muster's crew (manager, builder, designer, inspector) as separate Cursor agents, each in its own copy of the project,
with Muster's rules as Cursor rules and the same board, owner's list and decisions log. Built from Muster's core
files; written from Cursor's documentation and **never run inside Cursor**: everything marked *unconfirmed* below is
a thing to try on the first real run.

## What Cursor does and does not give us (checked against Cursor's docs)
| Need | Cursor | Used as |
|---|---|---|
| Rules | `.cursor/rules/*.mdc` (must be `.mdc`; `alwaysApply: true` is always on; no description and no globs means you open it with `@name`); `AGENTS.md` | `muster-core.mdc` always on; `muster-manager/builder/designer/inspector.mdc` opened with `@` from the starting note |
| Each agent its own copy | git worktrees (Agents Window, `/worktree`); `.cursor/worktrees.json` setup; Cursor may clean up worktrees (default cap 25) | `setup.py` makes plain `git worktree add` copies beside the project. *Unconfirmed:* Cursor's cleanup may delete copies it did not create; if so, make them with Cursor's own `/worktree` instead |
| Hooks | `.cursor/hooks.json`; `stop` can return `followup_message` (limit `loop_limit`); `sessionStart`, `preCompact` exist | the manager's Stop check (`cursor-stop.py`). *Unconfirmed:* what Cursor's transcript file looks like, so "the manager's agent" is recognised by `Manager_<project>_<digits>` near the top of it |
| Agents messaging each other | **not documented** | not used: the board is the channel |
| Notifications / waking an agent | **not documented** | not used: the owner opens the chat |
| Claude Code skills/plugins | Cursor loads `.claude/skills` (skills only); plugins: not confirmed | not used: Muster's scripts are called as plain commands |

## Steps for the owner
1. Get Muster: `git clone https://github.com/d4rthban3/muster` (anywhere on the computer).
2. In a terminal: `python3 muster/cursor/setup.py "/path/to/your project" --name "Your Project" --vision "what you are building"` (path to the clone's `cursor/setup.py`). Add `--builders 2` for a second builder, `--no-designer` to skip the designer.
3. It prints, per agent, a folder and a starting-note file. For each one (**Manager first**): open that folder in Cursor, start a new Agent chat, paste the whole starting note as your first message.
4. Talk only to the Manager. When it says "X is waiting for you: type in <chat>", open that chat and type anything.
5. To see what is waiting at any time: the top line of `muster/BOARD.md` ("Waiting on:").

## How the agents work together without messaging
- Every agent runs `python3 <main>/muster/tools/board_digest.py "<its chat name>"` at the start of each turn (the always-on rule says so) and reads what is addressed to it.
- Reports are entries on `muster/BOARD.md` (the six report lines in the entry); an order, READY, PASS, FAIL, NEED all work the same way. Nothing wakes an agent: **the owner opens a chat and types anything** (e.g. "check the board") when the Manager says that chat has something for it.
- A waiting agent says "type in <chat>" in its own window card and puts a NEED/STUCK/OWNER CALL entry on the board; the Manager's Stop check (`.cursor/hooks.json`) tells the owner once.
- `record-choice.py` and `decide.py` (in `muster/tools/`) are the only way choices and decisions are written. The same files the Claude Code edition uses.

## Not ported (and why)
`ship.sh` (it releases a Claude plugin repo; in a project a builder pushes its passed branch fast-forward only), the talking check, the renewal-after-summary hook, PushNotification, paused-chat markers (`muster/CLAUDE.md` still describes them; ignore for Cursor), the usage meter. Cursor's own "Rules" are advisory text: nothing enforces them except the one Stop hook.

## Keeping it current
`git pull` in the Muster clone, then run `setup.py` again: it never overwrites an existing file, so refresh rules by deleting `.cursor/rules/muster-*.mdc` first.
