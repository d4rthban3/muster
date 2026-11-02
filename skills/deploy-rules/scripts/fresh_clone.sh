#!/usr/bin/env bash
# Make a fresh clone of the repo at a ref, to deploy from. Never deploy from a working copy.
# Usage: fresh_clone.sh <repo-path-or-url> <ref> [target-dir]   (prints the clone path and HEAD)
set -eu
[ $# -ge 2 ] || { echo "usage: fresh_clone.sh <repo> <ref> [target-dir]"; exit 2; }
repo=$1; ref=$2
dir=${3:-$(mktemp -d "${TMPDIR:-/tmp}/muster-deploy.XXXXXX")}
[ -z "$(ls -A "$dir" 2>/dev/null)" ] || { echo "target not empty: $dir"; exit 1; }
git clone -q "$repo" "$dir"
git -C "$dir" checkout -q "$ref"
echo "path: $dir"
echo "head: $(git -C "$dir" rev-parse HEAD)"
git -C "$dir" status --porcelain | grep -q . && { echo "UNEXPECTED: fresh clone is not clean"; exit 1; }
exit 0
