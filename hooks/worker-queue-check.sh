#!/bin/sh
# Stop hook: runs scripts/worker-queue-check.py in a worker's own project copy; the script is silent anywhere else.
d=$(pwd)
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -d "$d/.muster-checks" ] && exit 0   # the project runs its own installed copy: stand down
  d=$(dirname "$d")
done
here=$(dirname "$0")
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
exec $py "$here/../scripts/worker-queue-check.py"
