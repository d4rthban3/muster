#!/usr/bin/env bash
# Item 90: make Claude Code load Muster and its mod (muster-look) LIVE from the Muster folder, not from the versioned copy in its
# plugin cache. A marketplace added from a local directory is "read in place": its relative-path plugins load from the folder itself
# at every session start (and on /reload-plugins), whatever their version says (Claude Code docs, plugins/loading.md "In-place and
# copied plugins" and "Versions and updates"; `claude plugin list` then prints "Read from: <folder>").
#   plugin-live.sh [--path <Muster folder>] [--config-dir <dir>] [--dry-run] [--no-cli]   switch to live, keeping a backup
#   plugin-live.sh --undo [--config-dir <dir>]                                              put the newest backup back
# --path defaults to the main folder of the checkout this script is in. --config-dir defaults to $CLAUDE_CONFIG_DIR or ~/.claude.
# Changes only the user's settings.json (extraKnownMarketplaces entry) and the marketplace record; both are copied to
# <config-dir>/muster-live-backup-<time>/ first. If the switch does not verify, the backup is put back by itself.
set -u
export MSYS2_ARG_CONV_EXCL='*'
here=$(cd "$(dirname "$0")/.." && pwd)
path=""; cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"; dry=0; undo=0; nocli=0
while [ $# -gt 0 ]; do
  case "$1" in
    --path) path=$2; shift 2 ;; --config-dir) cfg=$2; shift 2 ;; --dry-run) dry=1; shift ;; --undo) undo=1; shift ;; --no-cli) nocli=1; shift ;;
    *) echo "unknown option $1"; exit 2 ;;
  esac
done
stop() { echo "STOP: $*"; exit 1; }
py=$(sh "$here/scripts/find-python.sh") || stop "no working Python 3"
if [ -z "$path" ]; then
  common=$(git -C "$here" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) && path=${common%/.git} || path=$here
fi
# on Windows (Git Bash) Python needs C:/ style paths, not /tmp style ones
if command -v cygpath >/dev/null 2>&1; then path=$(cygpath -m "$path" 2>/dev/null || echo "$path"); cfg=$(cygpath -m "$cfg" 2>/dev/null || echo "$cfg"); fi
settings="$cfg/settings.json"; known="$cfg/plugins/known_marketplaces.json"
restore() { # $1 = backup folder
  [ -f "$1/settings.json" ] && cp "$1/settings.json" "$settings"
  if [ -f "$1/known_marketplaces.json" ]; then cp "$1/known_marketplaces.json" "$known"; elif [ -f "$1/known_marketplaces.absent" ]; then rm -f "$known"; fi
}
if [ $undo = 1 ]; then
  b=$(ls -d "$cfg"/muster-live-backup-*/ 2>/dev/null | sort | tail -1); [ -n "$b" ] || stop "no backup found in $cfg"
  restore "${b%/}"; echo "PUT BACK the settings and marketplace record from ${b%/}"; exit 0
fi
[ -f "$path/.claude-plugin/marketplace.json" ] || stop "$path has no .claude-plugin/marketplace.json"
name=$($py -c 'import json,sys;print(json.load(open(sys.argv[1]))["name"])' "$path/.claude-plugin/marketplace.json") || stop "could not read the marketplace name"
echo "== the marketplace $name will be read in place from $path (settings: $settings)"
[ $dry = 1 ] && { echo "DRY RUN OK: nothing changed"; exit 0; }
mkdir -p "$cfg/plugins"
b="$cfg/muster-live-backup-$(date +%Y%m%d-%H%M%S)"; mkdir -p "$b"
[ -f "$settings" ] && cp "$settings" "$b/settings.json"
if [ -f "$known" ]; then cp "$known" "$b/known_marketplaces.json"; else : > "$b/known_marketplaces.absent"; fi
$py - "$settings" "$name" "$path" <<'PY' || { restore "$b"; stop "could not edit the settings (backup put back)"; }
import json, os, sys
p, name, path = sys.argv[1:4]
d = json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {}
d.setdefault("extraKnownMarketplaces", {})[name] = {"source": {"source": "directory", "path": path}}
open(p, "w", encoding="utf-8").write(json.dumps(d, indent=2) + "\n")
PY
if [ $nocli = 0 ]; then
  command -v claude >/dev/null 2>&1 || { restore "$b"; stop "the claude program was not found (backup put back)"; }
  CLAUDE_CONFIG_DIR="$cfg" claude plugin marketplace add "$path" >"$b/add.out" 2>&1 || { cat "$b/add.out"; restore "$b"; stop "claude could not add the marketplace (backup put back)"; }
  CLAUDE_CONFIG_DIR="$cfg" claude plugin list >"$b/list.out" 2>&1
  # compare the way Windows prints it too: slashes the same, no case, and only the last two folder names (C:\\Users\\RUNNER~1 vs runneradmin)
  tail2=$(printf '%s' "$path" | tr '\\' '/' | awk -F/ '{print $(NF-1) "/" $NF}')
  seen() { tr '\\' '/' | grep -qiF "$tail2"; }
  if grep -q "@$name" "$b/list.out"; then ok=0; grep "Read from:" "$b/list.out" | seen && ok=1
  else CLAUDE_CONFIG_DIR="$cfg" claude plugin marketplace list 2>&1 | seen && ok=1 || ok=0; fi
  [ $ok = 1 ] || { cat "$b/list.out"; restore "$b"; stop "the plugins do not read from $path (backup put back)"; }
  grep -q "failed to load" "$b/list.out" && { cat "$b/list.out"; restore "$b"; stop "a plugin failed to load (backup put back)"; }
fi
echo "LIVE: $name is read from $path. Backup: $b (undo: bash scripts/plugin-live.sh --undo)."
echo "A chat that is already running keeps what it loaded; it picks up a change to skills, agents and hooks with /reload-plugins, and any new chat loads the folder fresh."
