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

## Steps for the owner (no terminal needed; UNTESTED in Cursor, like everything here)
1. Open your project's folder in Cursor and start a new **Agent** chat there.
2. Paste this one message and press Enter. When Cursor asks to run a command, click Run/Allow.
   > Set up Muster for this project. First ask me for the project's name and one sentence on what I am building. Then get Muster (`git clone https://github.com/d4rthban3/muster` into a folder next to this project, unless it is already there), run its `cursor/setup.py` on this project's folder with that name and sentence, and show me the folders and starting-note files it prints.
3. For each agent it lists (**Manager first**): open that agent's folder in Cursor, start a new Agent chat, open the starting-note file it names, and paste its whole contents as your first message.
4. Talk only to the Manager. When it says "X is waiting for you: type in <chat>", open that chat and type anything.
5. To see what is waiting at any time: the top line of `muster/BOARD.md` ("Waiting on:").

*Already use a terminal?* Same result by hand: `git clone https://github.com/d4rthban3/muster`, then `python3 muster/cursor/setup.py "/path/to/your project" --name "Your Project" --vision "what you are building"` (`--builders 2` for a second builder, `--no-designer` to skip the designer).

## How the agents work together without messaging
- Every agent runs `python3 <main>/muster/tools/board_digest.py "<its chat name>"` at the start of each turn (the always-on rule says so) and reads what is addressed to it.
- Reports are entries on `muster/BOARD.md` (the six report lines in the entry); an order, READY, PASS, FAIL, NEED all work the same way. Nothing wakes an agent: **the owner opens a chat and types anything** (e.g. "check the board") when the Manager says that chat has something for it.
- A waiting agent says "type in <chat>" in its own window card and puts a NEED/STUCK/OWNER CALL entry on the board; the Manager's Stop check (`.cursor/hooks.json`) tells the owner once.
- `record-choice.py` and `decide.py` (in `muster/tools/`) are the only way choices and decisions are written. The same files the Claude Code edition uses.

## A second computer on the same project (two founder computers) — UNTESTED
For a second computer that opens the host's project files live (for example over a network share), Muster has a join mode. It writes **nothing** inside the project's `muster/` folder or the host's workspace; it makes this computer's own workspace folder (its change log, a starting note, a `git-as.sh` that commits under its own name), writes Cursor rules named for the computer (core plus the two-computer lines), and with `--copies clone` makes a local clone per builder and designer on its own `<name>/` branches (the safe way to get a copy: nothing is added to the shared repository's worktree list).
- By hand: `python3 cursor/setup.py "<project folder as this computer sees it>" --name "Project" --join --computer laptop2 --other desk1 [--copies clone]`. Or paste the same request into a Cursor Agent chat, as in the steps above.
- Then, in every chat on the second computer, paste the whole `START-HERE.md` from its workspace as the first message.
- The rules (also section 9c of `muster/CLAUDE.md`): read the other computer's change log first, write only your own, never override the other, no orders either way, `muster/` is written by the host's manager only, own branches and own git name.
- **Cannot be enforced across a network share:** file locks and two writers on one file. Each side avoids collisions by working on its own branches and in its own copies, reading the other's log and `git log` for a file before editing it, and one writer per shared file.

## Not ported (and why)
`ship.sh` (it releases a Claude plugin repo; in a project a builder pushes its passed branch fast-forward only), the talking check, the renewal-after-summary hook, PushNotification, paused-chat markers (`muster/CLAUDE.md` still describes them; ignore for Cursor), the usage meter. Cursor's own "Rules" are advisory text: nothing enforces them except the one Stop hook.

## Keeping it current
Paste this into your Cursor Agent chat (click Run/Allow when it asks): *"Update Muster to the newest version: update the Muster folder next to this project, then run its `cursor/setup.py` on this project again, and tell me what changed."* Setup never overwrites an existing file, so it also deletes nothing of yours; to refresh the rules themselves, ask the agent to delete the `.cursor/rules/muster-*.mdc` files first. *Already use a terminal?* `git pull` in the Muster folder, then run `setup.py` again.
