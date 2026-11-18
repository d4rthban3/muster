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
ev=$(cat)
# the ready-built program first; a program that does not know this check yet (exit 2), or none at all, leaves it to the Python copy
if bin=$(sh "$here/../scripts/find-binary.sh" "$(cd "$here/.." && pwd)" 2>/dev/null); then
  printf '%s' "$ev" | "$bin" precompact; rc=$?
  [ "$rc" -ne 2 ] && exit "$rc"
fi
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
printf '%s' "$ev" | $py "$here/precompact-board.py"
