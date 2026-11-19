#!/bin/sh
# Runs the board check at every stop; does nothing at all unless this folder holds muster/BOARD.md (the manager's folder).
d=$(pwd); wt=""
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -z "$wt" ] && { [ -f "$d/.muster-checks/board-stop.py" ] || [ -f "$d/.muster-checks/muster-checks" ] || [ -f "$d/.muster-checks/muster-checks.exe" ]; } && exit 0   # the project runs its own installed copy: stand down (not from inside a linked worktree: the copy belongs to the main folder only)
  [ -f "$d/.git" ] && wt=1
  d=$(dirname "$d")
done
[ -f muster/BOARD.md ] || exit 0
here=$(dirname "$0")
ev=$(cat)
# the ready-built program first; no program, one that will not start, or one that ends with anything but exit 0 leaves it to the Python copy
out=$(printf '%s' "$ev" | sh "$here/../scripts/try-program.sh" "$(cd "$here/.." && pwd)" board-stop) && { [ -z "$out" ] || printf '%s\n' "$out"; exit 0; }
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
printf '%s' "$ev" | $py "$here/board-stop.py"
