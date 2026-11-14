#!/bin/sh
# Stop hook: runs scripts/worker-queue-check.py in a worker's own project copy; the script is silent anywhere else.
d=$(pwd); wt=""
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -z "$wt" ] && { [ -f "$d/.muster-checks/worker-queue-check.py" ] || [ -f "$d/.muster-checks/muster-checks" ] || [ -f "$d/.muster-checks/muster-checks.exe" ]; } && exit 0   # the project runs its own installed copy: stand down (not from inside a linked worktree: the copy belongs to the main folder only)
  [ -f "$d/.git" ] && wt=1
  d=$(dirname "$d")
done
here=$(dirname "$0")
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
exec $py "$here/../scripts/worker-queue-check.py"
