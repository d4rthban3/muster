#!/bin/sh
# Pre-tool and Stop hook: runs rules-check.py only inside a Muster project (muster/CLAUDE.md in this folder or above).
d=$(pwd); found=""
while [ -n "$d" ] && [ "$d" != "/" ]; do
  [ -f "$d/muster/CLAUDE.md" ] && { found=1; break; }
  d=$(dirname "$d")
done
[ -n "$found" ] || exit 0
here=$(dirname "$0")
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
exec $py "$here/rules-check.py"
