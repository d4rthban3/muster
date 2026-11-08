# Installing Muster's coded rules in a project that does not use the plugin (for its manager)

Muster's rules are enforced by small hook programs (the owner, D-027: "code every rule"). A project that loads the Muster
plugin gets them automatically. A project that does not (for example PINR) installs them with one command.

1. Get a copy of the Muster plugin folder (its `scripts/install-checks.py` is the installer).
2. From the project's main folder run: `python3 <muster folder>/scripts/install-checks.py .`
3. It copies the checks into `.muster-checks/` and adds them to `.claude/settings.json`; your other settings stay.
4. Start the crew's chats fresh (a running chat reads hooks when it starts). The checks act only in chats whose first
   message names a crew role, never in the owner's own chats.
5. After each Muster update run the same command again to refresh the copies. `--remove` takes them away.

What it enforces: messages between chats are a six-line report or an order that quotes the owner's words; no "noted"
replies; a report ID is sent once; PASS and FAIL copies for the manager go on the board; no new order when the week is at
90%; only the manager changes the owner's list, the decisions log, the crew list and the rules pages; nothing under
`muster/` is saved or pushed; the manager's reply to the owner is a question with buttons, a yes, a waiting line or an
idle line; an answered choice card is recorded; every other chat ends its turn with a short card.
