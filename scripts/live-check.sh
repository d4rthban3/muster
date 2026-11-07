#!/usr/bin/env bash
# Proves the NEW content is being served, not only that the page answers.
# Usage: live-check.sh <version> [docs-file added-line]   (env LIVE_CHECK_TRIES = tries, default 40; 15 s apart)
# 1. https://raw.githubusercontent.com/d4rthban3/muster/main/.claude-plugin/plugin.json must say <version>.
# 2. If given, the live site page for <docs-file> (docs/index.html -> the site root) must contain <added-line> exactly.
# Retries until both match or the tries run out. Exit 0 when proven, 1 (and says which part) when not.
version=$1; file=${2:-}; line=${3:-}
tries=${LIVE_CHECK_TRIES:-40}; base=${LIVE_SITE_BASE:-https://d4rthban3.github.io/muster}
raw=${LIVE_RAW_BASE:-https://raw.githubusercontent.com/d4rthban3/muster/main}
rel=${file#docs/}; [ "$rel" = index.html ] && rel=""
n=0; vok=0; pok=1; [ -n "$file" ] && [ -n "$line" ] && pok=0
while [ $n -lt "$tries" ]; do
  if [ $vok = 0 ]; then
    got=$(curl -fsS "$raw/.claude-plugin/plugin.json?x=$RANDOM" 2>/dev/null | grep -o '"version": *"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
    [ "$got" = "$version" ] && vok=1
  fi
  if [ $pok = 0 ]; then
    curl -fsS "$base/$rel?x=$RANDOM" 2>/dev/null | grep -qF -- "$line" && pok=1
  fi
  [ $vok = 1 ] && [ $pok = 1 ] && { echo "LIVE PROVEN: version $version${file:+ and a changed line of $file}"; exit 0; }
  n=$((n+1)); [ $n -lt "$tries" ] && sleep 15
done
[ $vok = 1 ] || echo "LIVE NOT PROVEN: the published plugin.json says '${got:-nothing}', not $version"
[ $pok = 1 ] || echo "LIVE NOT PROVEN: the live page for $file lacks the changed line"
exit 1
