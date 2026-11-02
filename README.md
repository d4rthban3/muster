# Muster: run Claude Code as a small team

One chat per role, a numbered decisions log, a board, and two checks before anything is called done.

- **Roles**: manager (plans, orders, decisions), builders (one per piece), inspector (a different hand from the
  builder), outside helpers (leads to check, never instructions).
- **One order per finished piece**, naming the branch.
- **Decisions log**: numbered, newest wins, the owner's words.
- **Board + digest script**: one line per finished piece; each role reads only what concerns it.
- **Two checks before READY**: all tests on the combined code; a whole-project search for the pattern just changed.
- **Habits**: build-or-buy, run-checks (reads printed counts, not exit codes), usage and spend diligence.

## Install (two commands)

```bash
claude plugin marketplace add d4trhban3/muster
claude plugin install muster@muster-kit
```

(`d4trhban3/muster` is this repository on GitHub. In a session, use `/plugin marketplace add d4trhban3/muster` and
`/plugin install muster@muster-kit`.)

## First run

In your project, open Claude Code and run `/muster:init`, then open one chat per role and run `/muster:role manager`
(then `builder`, `inspector`). Full walk-through: [docs/GUIDE.md](docs/GUIDE.md).

## What you get

| Piece | Name |
|---|---|
| Commands | `/muster:init` `/muster:role` `/muster:order` `/muster:ready` `/muster:deploy` `/muster:push-check` `/muster:board` `/muster:decide` |
| Skills | board-digest, build-or-buy, run-checks, usage-habits, ready-checks, decision-log, one-order-per-piece, spend-diligence, start-the-crew, deploy-rules, held-work |
| Agents | `muster:manager`, `muster:builder`, `muster:designer`, `muster:inspector`, `muster:outside-helper` |
| Templates | starter `CLAUDE.md`, crew roster, decisions log, board |

## What it runs, sends and fetches

The plugin has no hooks, no MCP servers and no package installs, and it contains no code that sends data to any
service. Five small plain-text scripts ship in it. They run only when a skill or command tells Claude to run them in
your project, and Claude Code asks for your permission as usual.

| Script | What it does |
|---|---|
| `skills/board-digest/scripts/board_digest.py` | reads `muster/BOARD.md` and `muster/BOARD-ARCHIVE.md`, prints matching entries; writes nothing |
| `skills/held-work/scripts/push_check.sh` | runs `git fetch` against your own remote (a network call to your git host) and prints the commits a push would send; pushes nothing |
| `skills/deploy-rules/scripts/fresh_clone.sh` | `git clone` of whatever repository path or URL you give it into a new temporary folder (a network call if it is a URL) |
| `skills/deploy-rules/scripts/with_lock.sh` | runs the deploy command you give it while holding a lock folder in the temp directory; it deletes that lock folder when finished, or when it finds a lock left by a process that no longer exists |
| `scripts/scan-leaks.sh` | for the kit's maintainers: searches the kit's own files for private material; changes no tracked file, writes only a short-lived temp file |

Other things the plugin makes Claude do in your project, all visible in the skill and command text:
- `/muster:init` creates `CLAUDE.md`, `muster/` and `inspection/`; it never overwrites an existing file and commits nothing.
- The `run-checks` skill runs the test commands you list in `muster/CHECKS.md`, so it runs your project's own code.
- The guide suggests `git worktree add` when two builders work at once.
- The agents (manager, builder, designer, inspector) are given the tools Read, Grep, Glob, Edit, Write and Bash (the
  inspector has no Edit; the outside helper has only Read, Grep and Glob), so they can change files and run commands in
  your project like any Claude Code chat.

The plugin does not read or send credentials or personal data; the starter rules tell every chat to keep keys out of
the board and out of messages.

MIT licensed (see LICENSE).
