#!/bin/sh
# SessionStart hook (matcher "compact"): runs the check in renew-after-summary.py. Silent in any project without muster/CLAUDE.md
# in this folder or above it, so it costs nothing elsewhere.
d=$(pwd); found=""
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -f "$d/muster/CLAUDE.md" ] && { found=1; break; }
  d=$(dirname "$d")
done
[ -n "$found" ] || exit 0
here=$(dirname "$0")
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
exec $py "$here/renew-after-summary.py"
