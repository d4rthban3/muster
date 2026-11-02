# Install and first run

## 1. Install
```bash
claude plugin marketplace add OWNER/REPO
claude plugin install muster@muster-kit
```
Check: `claude plugin list` shows `muster@muster-kit`. To try it from a local copy instead:
`claude plugin marketplace add ./path/to/this/folder`, same install command.

## 2. Set up a project
Open Claude Code in your project folder and run `/muster:init`. It creates `muster/` (roster, decisions log, board,
checks list), an `inspection/` folder, and a starter `CLAUDE.md` (or offers to append to yours). It never overwrites
and commits nothing. Answer its two questions; the answers become decision D-001.

## 3. Fill in the checks list
Open `muster/CHECKS.md`. One line per test command: `<folder> | <command> | <expected count>`. Run each once, and put
the printed count in. The `run-checks` skill compares against these.

## 4. Open one chat per role
- Chat 1: run `/muster:role manager`. Give it your goal.
- Chat 2: `/muster:role builder` (or `designer` for front-end work). Chat 3: `/muster:role inspector`.
- Two builders at once: give each its own git worktree (`git worktree add ../b2 -b builder/b2`), and non-overlapping
  files.
Update the roster table in `muster/CREW.md`.

## 5. Run one piece of work
1. Tell the manager the goal. It writes one order (`/muster:order`) naming the branch.
2. The builder does it, then `/muster:ready <branch>`: runs all tests on the combined code, searches the whole project
   for the changed pattern, posts the READY line.
3. The inspector reads the board (`/muster:board inspector`), runs the checks itself, and passes or fails.
4. The manager tells you when it is done. Say a rule out loud ("always do X") and the manager records it with
   `/muster:decide`.

## 6. Deploying and held work
- Builders/designers deploy only their own **site / front-end** work: `/muster:deploy <piece>` (dry run, lock, fresh
  clone, push check, verify live). Engine, data and back-end changes are never deployed by the builder.
- Held work stays on its branch. Before any push run `/muster:push-check <n>` with the number of commits you expect to
  send; it stops you if extra commits are waiting.
- Models: read-only agents default to a cheap model; the rest follow your choice. Each agent lists only the tools it
  needs (edit the `tools:` line in the plugin's agent file to change that).
- Put each chat's id in the roster in `muster/CREW.md` so chats can message each other.

## 7. Daily habits
Each chat runs `/muster:board <role>` at session start and before finishing. Long chat? Renew it at a natural break
with a handover note (skill `usage-habits`).

## Notes
- Only a new paid spend, a key, or deleting data needs your yes; change that in the decisions log.
- Nothing in the kit contacts the network or sends data anywhere.
