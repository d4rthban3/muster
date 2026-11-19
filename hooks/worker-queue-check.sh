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
# the ready-built program first; no program, one that will not start, or one that ends with anything but exit 0 leaves it to the Python copy
out=$(printf '%s' "$ev" | sh "$here/../scripts/try-program.sh" "$(cd "$here/.." && pwd)" worker-queue) && { [ -z "$out" ] || printf '%s\n' "$out"; exit 0; }
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
printf '%s' "$ev" | $py "$here/../scripts/worker-queue-check.py"
