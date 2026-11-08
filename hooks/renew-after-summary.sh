#!/bin/sh
# SessionStart hook with matcher "compact": fires once, right after a chat's conversation was summarized.
# Tells a crew chat (one whose folder or a parent holds muster/CLAUDE.md) to hand over and renew at its next natural break.
# Silent in any other project. It is an event, not a stop, so it cannot loop.
d=$(pwd); found=""
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -f "$d/muster/CLAUDE.md" ] && { found=1; break; }
  d=$(dirname "$d")
done
[ -n "$found" ] || exit 0
printf '%s\n' 'Muster: your conversation was just summarized, so it is time to renew (muster/CLAUDE.md section 9). At your next natural break: if a job is in progress, write a short handover to muster/handovers/<your chat name>.md in the main project folder (what is open, the files that matter, the next step); then send the manager "DONE: renewal <your chat name>". Do this once, then carry on until the manager starts your fresh chat.'
