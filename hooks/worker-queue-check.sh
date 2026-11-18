#!/bin/sh
# Stop hook: runs the worker queue check in a worker's own project copy (the ready-built program first, scripts/worker-queue-check.py as the
# fallback); it is silent anywhere else.
d=$(pwd); wt=""
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -z "$wt" ] && { [ -f "$d/.muster-checks/worker-queue-check.py" ] || [ -f "$d/.muster-checks/muster-checks" ] || [ -f "$d/.muster-checks/muster-checks.exe" ]; } && exit 0   # the project runs its own installed copy: stand down (not from inside a linked worktree: the copy belongs to the main folder only)
  [ -f "$d/.git" ] && wt=1
  d=$(dirname "$d")
done
here=$(dirname "$0")
ev=$(cat)
# the ready-built program first; a program that does not know this check yet (exit 2), or none at all, leaves it to the Python copy
if bin=$(sh "$here/../scripts/find-binary.sh" "$(cd "$here/.." && pwd)" 2>/dev/null); then
  printf '%s' "$ev" | "$bin" worker-queue; rc=$?
  [ "$rc" -ne 2 ] && exit "$rc"
fi
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
printf '%s' "$ev" | $py "$here/../scripts/worker-queue-check.py"
