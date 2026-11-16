#!/bin/sh
# Pre-tool hook for item 117 (blocking guards). Runs wherever the project's own profile (.muster-checks/profile.json, in this folder or
# above) has a guard, even where the project runs its own older installed copy of the checks; costs nothing elsewhere.
d=${CLAUDE_PROJECT_DIR:-$(pwd)}; found=""
if [ -n "$MUSTER_PROFILE" ] && [ -f "$MUSTER_PROFILE" ]; then grep -q '"guard"' "$MUSTER_PROFILE" 2>/dev/null && found=1
else
  while [ -n "$d" ] && [ "$d" != "/" ]; do
    [ -f "$d/.muster-checks/profile.json" ] && { grep -q '"guard"' "$d/.muster-checks/profile.json" 2>/dev/null && found=1; break; }
    d=$(dirname "$d")
  done
fi
[ -n "$found" ] || exit 0
here=$(dirname "$0")
bin=$(sh "$here/../scripts/find-binary.sh" "$(cd "$here/.." && pwd)" 2>/dev/null) && exec "$bin" guard
py=$(sh "$here/../scripts/find-python.sh" 2>/dev/null) || exit 0
exec $py "$here/rules-check.py" guard
