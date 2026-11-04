#!/usr/bin/env bash
# Look at what is waiting BEFORE any push, so held commits cannot ride out on your push.
# Usage: push_check.sh <expected-commit-count> [remote] [branch]
# Prints every commit the push would send, every other local branch with unpushed work, and
# uncommitted files. Exit 1 if the count differs from what you expected.
set -u
[ $# -ge 1 ] || { echo "usage: push_check.sh <expected-commit-count> [remote] [branch]"; exit 2; }
expected=$1; remote=${2:-origin}; branch=${3:-$(git rev-parse --abbrev-ref HEAD)}
git fetch -q "$remote" 2>/dev/null || echo "note: could not fetch $remote; remote state may be old"
base="$remote/$branch"
range="$base..$branch"
# First push (no such branch on the remote): the whole branch goes out, its first commit included.
git rev-parse -q --verify "$base" >/dev/null || range="$branch"
echo "== Push of '$branch' to $remote would send:"
git log --format='  %h %an  %s' $range
n=$(git rev-list --count $range)
echo "== $n commit(s); you expected $expected"
echo "== Other local branches ahead of their remote (held work; stays unpushed unless it is the push):"
git for-each-ref --format='%(refname:short) %(upstream:short)' refs/heads | while read -r b up; do
  [ "$b" = "$branch" ] && continue
  if [ -n "$up" ]; then c=$(git rev-list --count "$up..$b" 2>/dev/null); else c=$(git rev-list --count "$b" --not "$branch" 2>/dev/null); fi
  [ "${c:-0}" -gt 0 ] && echo "  $b: $c commit(s) not pushed"
done
echo "== Uncommitted files:"
git status --porcelain | sed 's/^/  /'
crew=$(git log --format= --name-only $range -- ':(top)muster/' | sort -u)
if [ -n "$crew" ]; then
  echo "STOP: the push carries Muster's crew files (muster/), which stay on this computer only:"
  echo "$crew" | sed 's/^/  /'
  echo "  (A later commit that stops saving them does not help: the pushed history would still hold them.)"
  exit 1
fi
if [ "$n" -ne "$expected" ]; then
  echo "STOP: the push carries $n commit(s), not $expected. Find the extra ones (are they yours? are they held?) before pushing."
  exit 1
fi
echo "OK: the push carries exactly what you expected."
