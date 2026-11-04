#!/usr/bin/env bash
# Runs setup's own steps headless (no Claude, no desktop app) on this computer, in a scratch home folder, and fails
# on the first step that does not work. Used by .github/workflows/setup-test.yml on Windows, Mac and Linux.
# Covers: finding Python, serve.py saving a choice, a project folder with a space and an awkward name, git init with
# the exclude, the crew files copied and kept out of history, git worktree add. Cannot cover: the desktop app's
# buttons, trust boxes and sidebar.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CLAUDE_PLUGIN_ROOT=$ROOT
SCRATCH=$(mktemp -d)
export HOME="$SCRATCH/home"; mkdir -p "$HOME"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_CONFIG_NOSYSTEM=1   # a computer with no git settings
step() { echo; echo "== $*"; }
fail() { echo "FAIL: $*"; exit 1; }

step "git is there"; git --version || fail "git missing"
step "find Python"
PY=$(sh "$ROOT/scripts/find-python.sh") || fail "no working Python 3"
echo "python command: $PY"

step "setup page: serve.py saves a choice"
PROJECT="Bob's \$5 Shop"
mkdir -p "$HOME/Muster"
$PY "$ROOT/setup/serve.py" "$HOME/Muster/.setup-choices.json" > "$SCRATCH/serve.out" 2>&1 &
SERVE_PID=$!
URL=""
for _ in $(seq 1 50); do URL=$(grep -o 'http://[^ ]*' "$SCRATCH/serve.out" | head -1 || true); [ -n "$URL" ] && break; sleep 0.2; done
[ -n "$URL" ] || fail "serve.py printed no address: $(cat "$SCRATCH/serve.out")"
echo "page at $URL"
curl -fsS "$URL" > "$SCRATCH/page.html" || fail "page did not load"
grep -q "Muster setup" "$SCRATCH/page.html" || fail "page has no title"
curl -fsS -o /dev/null "${URL}fonts/dm-sans.woff2" || fail "font did not load"
TOKEN=$(grep -o 'X-Muster-Token":"[^"]*' "$SCRATCH/page.html" | cut -d'"' -f3)
[ -n "$TOKEN" ] || fail "no one-time key in the page"
BODY=$($PY -c 'import json,sys;print(json.dumps({"project":sys.argv[1],"vision":"A shop. é “quotes”","crew":["Manager","Builder A","Designer","Inspector"],"asks_first":["Spending money","Keys or passwords","Deleting anything"]}))' "$PROJECT")
curl -fsS -X POST "${URL}save" -H "Content-Type: application/json" -H "X-Muster-Token: $TOKEN" --data-binary "$BODY" | grep -q saved || fail "save refused"
wait "$SERVE_PID" || fail "serve.py did not stop cleanly after saving"
[ -s "$HOME/Muster/.setup-choices.json" ] || fail "choices file missing"
$PY -c 'import json,sys;d=json.load(open(sys.argv[1],encoding="utf-8"));assert d["project"]==sys.argv[2],d' "$HOME/Muster/.setup-choices.json" "$PROJECT" || fail "saved project name differs"
# a wrong key must be refused
step "serve.py refuses a wrong key"
$PY "$ROOT/setup/serve.py" "$SCRATCH/x.json" > "$SCRATCH/serve2.out" 2>&1 &
P2=$!
U2=""; for _ in $(seq 1 50); do U2=$(grep -o 'http://[^ ]*' "$SCRATCH/serve2.out" | head -1 || true); [ -n "$U2" ] && break; sleep 0.2; done
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${U2}save" -H "Content-Type: application/json" -H "X-Muster-Token: wrong" --data-binary "$BODY" || true)
kill "$P2" 2>/dev/null || true
[ "$CODE" = 403 ] || fail "wrong key got HTTP $CODE, not 403"

step "project folder, awkward name"
FOLDER="$HOME/Muster/$PROJECT"
mkdir -p "$FOLDER/muster"
mv "$HOME/Muster/.setup-choices.json" "$FOLDER/muster/setup-choices.json"

step "version history with the crew's folder kept out"
cd "$FOLDER"
git init -q
echo '/muster/' >> .git/info/exclude
printf '.env\n.env.*\n*.pem\n*.key\nnode_modules/\n.DS_Store\n.claude/\n' > .gitignore
git add -A
git -c user.name="Muster" -c user.email="muster@localhost" commit -q -m "First version" || fail "first save failed with no git name set"

step "crew files copied from templates"
cd muster
for f in CREW DECISIONS-LOG BOARD OWNERS-LIST REPORT START-NOTE RULES-PAGE CLAUDE; do
  [ -f "$CLAUDE_PLUGIN_ROOT/templates/$f.md" ] || fail "template $f.md missing"
  cp -n "$CLAUDE_PLUGIN_ROOT/templates/$f.md" . || fail "copy $f"
done
: > BOARD-ARCHIVE.md; mkdir -p rules handovers; : > rules/.gitkeep; : > handovers/.gitkeep
cd ..
[ -z "$(git status --porcelain -- muster/)" ] || fail "muster/ shows in git status"
[ -z "$(git ls-files muster/)" ] || fail "muster/ is in the history"

step "a worker's own copy (git worktree add)"
git worktree add '.claude/worktrees/builder-a-001' -b 'muster/builder-a-001' >/dev/null 2>&1 || fail "worktree add"
[ -d .claude/worktrees/builder-a-001 ] || fail "no worktree folder"
[ -z "$(git status --porcelain)" ] || fail "worktree shows as a change (.claude/ not ignored)"
[ ! -e .claude/worktrees/builder-a-001/muster ] || fail "crew files leaked into the worker's copy"

echo; echo "ALL STEPS PASSED"
