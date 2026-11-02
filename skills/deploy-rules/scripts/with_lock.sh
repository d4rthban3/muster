#!/usr/bin/env bash
# Run a command while holding a named lock so two deploys cannot overlap.
# Usage: with_lock.sh <lock-name> <command> [args...]
# Exit 75 if another run holds the lock (rerun later). A lock left by a dead process is cleared.
set -u
[ $# -ge 2 ] || { echo "usage: with_lock.sh <lock-name> <command> [args...]"; exit 2; }
name=$1; shift
dir="${MUSTER_LOCK_DIR:-${TMPDIR:-/tmp}/muster-locks}"
mkdir -p "$dir"
lock="$dir/$name.lock"
if ! mkdir "$lock" 2>/dev/null; then
  pid=$(cat "$lock/pid" 2>/dev/null || true)
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    echo "LOCKED: '$name' is held by process $pid. Rerun when it finishes."
    exit 75
  fi
  echo "clearing stale lock '$name' (holder gone)"
  rm -rf "$lock"
  mkdir "$lock" || { echo "LOCKED: lost the race for '$name'"; exit 75; }
fi
echo $$ > "$lock/pid"
trap 'rm -rf "$lock"' EXIT INT TERM
"$@"
