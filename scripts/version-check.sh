#!/usr/bin/env bash
# Before publishing: the version must go up whenever the plugin's files change, or "claude plugin update" will not
# pick the change up. Fails (exit 1) if the plugin and marketplace versions differ, or if anything changed since the
# published line (default origin/main) while the version stayed the same.
set -u
export MSYS2_ARG_CONV_EXCL='*'   # Git Bash on Windows must not rewrite 'origin/main:file' as a path list
cd "$(dirname "$0")/.."
base=${1:-origin/main}
git fetch -q origin 2>/dev/null || echo "note: could not fetch origin; the published version may be old"
v() { python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d.get("version") or [p for p in d["plugins"] if p["name"]=="muster"][0].get("version",""))' "$1"; }
pv=$(v .claude-plugin/plugin.json); mv=$(v .claude-plugin/marketplace.json)
[ "$pv" = "$mv" ] || { echo "STOP: plugin.json says $pv, marketplace.json says $mv"; exit 1; }
old=$(git show "$base:.claude-plugin/plugin.json" 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)["version"])' 2>/dev/null)
if [ -n "$(git diff --name-only "$base" HEAD)" ] && [ "$pv" = "$old" ]; then
  echo "STOP: files changed since $base but the version is still $pv; raise it in plugin.json and marketplace.json"; exit 1
fi
# item 118: every OTHER plugin in the marketplace (a mod such as muster-look) has its own version; files changed under its folder since the
# published line with its version unchanged would never reach anyone's "claude plugin update", so that stops here too (ship.sh bumps it).
python3 - "$base" <<'PY' || exit 1
import json, subprocess, sys
base = sys.argv[1]
def show(rev, path):
    r = subprocess.run(["git", "show", "%s:%s" % (rev, path)], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
mk = json.load(open(".claude-plugin/marketplace.json"))
bad = 0
for p in mk["plugins"]:
    src = p.get("source", "")
    if not src.startswith("./") or src.strip("./") == "":
        continue  # the plugin at the marketplace's own root is checked above
    folder = src[2:].rstrip("/")
    mf = folder + "/.claude-plugin/plugin.json"
    try:
        own = json.load(open(mf))["version"]
    except Exception:
        own = None
    if own is not None and own != p.get("version"):
        print("STOP: %s says %s in %s but %s in marketplace.json" % (p["name"], own, mf, p.get("version"))); bad = 1; continue
    changed = subprocess.run(["git", "diff", "--name-only", base, "HEAD", "--", folder], capture_output=True, text=True).stdout.split()
    old = (show(base, mf) or {}).get("version")
    if changed and old is not None and old == p.get("version"):
        print("STOP: %s changed (%d file(s) under %s) since %s but its version is still %s; raise it in %s and marketplace.json (ship.sh does it)" % (p["name"], len(changed), folder, base, old, mf)); bad = 1
sys.exit(bad)
PY
echo "OK: version $pv (published: ${old:-none})"
