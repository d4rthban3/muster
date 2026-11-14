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
bin=$(sh "$here/../scripts/find-binary.sh" "$(cd "$here/.." && pwd)" 2>/dev/null) && exec "$bin" board-stop
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
exec $py "$here/board-stop.py"
