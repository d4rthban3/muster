#!/usr/bin/env bash
# Before publishing: the version must go up whenever the plugin's files change, or "claude plugin update" will not
# pick the change up. Fails (exit 1) if the plugin and marketplace versions differ, or if anything changed since the
# published line (default origin/main) while the version stayed the same.
set -u
cd "$(dirname "$0")/.."
base=${1:-origin/main}
v() { python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d.get("version") or [p for p in d["plugins"] if p["name"]=="muster"][0].get("version",""))' "$1"; }
pv=$(v .claude-plugin/plugin.json); mv=$(v .claude-plugin/marketplace.json)
[ "$pv" = "$mv" ] || { echo "STOP: plugin.json says $pv, marketplace.json says $mv"; exit 1; }
old=$(git show "$base:.claude-plugin/plugin.json" 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)["version"])' 2>/dev/null)
if [ -n "$(git diff --name-only "$base" HEAD)" ] && [ "$pv" = "$old" ]; then
  echo "STOP: files changed since $base but the version is still $pv; raise it in plugin.json and marketplace.json"; exit 1
fi
echo "OK: version $pv (published: ${old:-none})"
