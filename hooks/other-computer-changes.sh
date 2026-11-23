#!/bin/sh
# UserPromptSubmit hook: prints the other computer's new CHANGES.md lines once per chat, only where muster/computers.txt names two computers
# (scripts/other-computer-changes.py). Silent everywhere else; never fails or blocks a turn (always exit 0).
here=$(dirname "$0")
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
$py "$here/../scripts/other-computer-changes.py" 2>/dev/null
exit 0
