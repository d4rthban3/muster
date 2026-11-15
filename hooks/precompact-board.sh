#!/bin/sh
# PreCompact hook: runs precompact-board.py (D-039). Silent in any project without muster/CLAUDE.md
# in this folder or above it, so it costs nothing elsewhere.
d=$(pwd); found=""; wt=""
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -z "$wt" ] && [ -f "$d/.muster-checks/precompact-board.py" ] && exit 0   # the project runs its own installed copy: stand down (not from inside a linked worktree)
  [ -f "$d/.git" ] && wt=1
  [ -f "$d/muster/CLAUDE.md" ] && { found=1; break; }
  d=$(dirname "$d")
done
[ -n "$found" ] || exit 0
here=$(dirname "$0")
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
exec $py "$here/precompact-board.py"
