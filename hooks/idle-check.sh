#!/bin/sh
# Stop hook: runs scripts/idle-check.py only in the manager's folder (muster/BOARD.md here); silent everywhere else.
d=$(pwd)
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -d "$d/.muster-checks" ] && exit 0   # the project runs its own installed copy: stand down
  d=$(dirname "$d")
done
[ -f muster/BOARD.md ] || exit 0
here=$(dirname "$0")
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
exec $py "$here/../scripts/idle-check.py"
