# Muster: a crew of Claude Code chats

Muster turns Claude Code into a small crew: a squad of workers geared to finish tasks efficiently, with a very high eye
for detail and quality, while protecting your usage. Each worker is its own chat. You talk to one of them, the
manager; it hands the work out, and nobody checks their own work.

## The crew
| Worker | What it does |
|---|---|
| Manager_001 | Your go-between and record keeper. Sorts what you say into orders, questions and ideas, keeps your list, and only asks you one question at a time. Never builds. |
| Builder_A_001 | Builds what you ask for. |
| Designer_001 | Builds what people see. |
| Inspector_001 | Checks the work, and checks the manager's record keeping. Never builds. |

Add-ons you can pick on the setup page: extra builders (Builder_B_001 and up), Sketchpad_001 (for playing with
ideas), AI_Socket_001 (for plugging in other AIs), and Agent_Teacher_001 (train your own agent in Claude Console).
When three or more workers build, a second inspector, Design_Inspector_001, joins to check what people see.

## Install
In Claude Code (the Code tab of the Claude desktop app, or a terminal), type these two lines, one at a time:
```
/plugin marketplace add d4trhban3/muster
/plugin install muster@muster-kit
```
Then, in the folder of your project, type:
```
/muster:setup
```
A setup page opens. Write what you are building, pick your crew, and press Start. Muster starts the chats for you.
Step by step: [docs/GUIDE.md](docs/GUIDE.md).

## What it runs, sends and fetches
The plugin has no hooks, no MCP servers and no package installs, and it contains no code that sends your data to any
outside service. Everything below runs only when a command or skill tells Claude to, and Claude Code asks your
permission as usual.

| Part | What it does |
|---|---|
| `setup/serve.py` | shows the setup page on your own computer only (`localhost`) and saves your choices to `muster/setup-choices.json`, then stops |
| `/muster:setup` | creates `CLAUDE.md` (if you have none) and the `muster/` folder in your project; never overwrites a file; saves nothing to your project's history; starts the crew's chats, each in its own copy of your project folder |
| `skills/board-digest/scripts/board_digest.py` | reads `muster/BOARD.md` and `muster/BOARD-ARCHIVE.md` and prints the entries for one worker; writes nothing |
| `skills/held-work/scripts/push_check.sh` | runs `git fetch` on your own online copy of the project (a network call to your git host) and shows what would be sent; sends nothing |
| `skills/deploy-rules/scripts/fresh_clone.sh` | makes a fresh copy of a project you name, from a folder or web address (a network call if it is a web address) |
| `skills/deploy-rules/scripts/with_lock.sh` | runs the publish command you give it while holding a lock folder, so two publishes cannot overlap; removes the lock when done |
| `scripts/scan-leaks.sh` | for the plugin's maintainers: searches the plugin's own files for private material |

The `run-checks` skill runs the test commands listed in `muster/CHECKS.md`, so it runs your project's own code. The
workers can read and change files and run commands in your project like any Claude Code chat; the inspectors have no
file-editing tools and are told never to change files. Muster does not read or send passwords or personal data.

MIT licensed (see LICENSE).

Muster is a community plugin. It is not made or supported by Anthropic.
