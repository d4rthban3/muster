#!/bin/sh
# Pre-tool and Stop hook: runs rules-check.py only inside a Muster project (muster/CLAUDE.md in this folder or above).
d=$(pwd); wt=""; found=""
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -z "$wt" ] && { [ -f "$d/.muster-checks/rules-check.py" ] || [ -f "$d/.muster-checks/muster-checks" ] || [ -f "$d/.muster-checks/muster-checks.exe" ]; } && exit 0   # the project runs its own installed copy: stand down (not from inside a linked worktree: the copy belongs to the main folder only)
  [ -f "$d/.git" ] && wt=1
  [ -f "$d/muster/CLAUDE.md" ] && { found=1; break; }
  d=$(dirname "$d")
done
[ -n "$found" ] || exit 0
here=$(dirname "$0")
bin=$(sh "$here/../scripts/find-binary.sh" "$(cd "$here/.." && pwd)" 2>/dev/null) && exec "$bin" rules
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
exec $py "$here/rules-check.py"
