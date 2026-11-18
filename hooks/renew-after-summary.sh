#!/bin/sh
# SessionStart hook (matcher "compact"): runs the check in renew-after-summary.py. Silent in any project without muster/CLAUDE.md
# in this folder or above it, so it costs nothing elsewhere.
d=$(pwd); found=""; wt=""
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -z "$wt" ] && [ -f "$d/.muster-checks/renew-after-summary.py" ] && exit 0   # the project runs its own installed copy: stand down (not from inside a linked worktree)
  [ -f "$d/.git" ] && wt=1
  [ -f "$d/muster/CLAUDE.md" ] && { found=1; break; }
  d=$(dirname "$d")
done
[ -n "$found" ] || exit 0
here=$(dirname "$0")
ev=$(cat)
# the ready-built program first; no program, one that will not start, or one that ends with anything but exit 0 leaves it to the Python copy
out=$(printf '%s' "$ev" | sh "$here/../scripts/try-program.sh" "$(cd "$here/.." && pwd)" renew) && { [ -z "$out" ] || printf '%s\n' "$out"; exit 0; }
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
printf '%s' "$ev" | $py "$here/renew-after-summary.py"
