#!/bin/sh
# Runs the board check at every stop; does nothing at all unless this folder holds muster/BOARD.md (the manager's folder).
d=$(pwd)
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -d "$d/.muster-checks" ] && exit 0   # the project runs its own installed copy: stand down
  d=$(dirname "$d")
done
[ -f muster/BOARD.md ] || exit 0
here=$(dirname "$0")
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
exec $py "$here/board-stop.py"
