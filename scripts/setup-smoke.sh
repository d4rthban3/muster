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
native() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else echo "$1"; fi; }   # Windows Python needs C:/ paths, not /tmp/
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
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${URL}save" -H "Content-Type: application/json" -H "X-Muster-Token: wrong" --data-binary "$BODY" || true)
[ "$CODE" = 403 ] || fail "wrong key got HTTP $CODE, not 403"
curl -fsS -X POST "${URL}save" -H "Content-Type: application/json" -H "X-Muster-Token: $TOKEN" --data-binary "$BODY" | grep -q saved || fail "save refused"
wait "$SERVE_PID" || fail "serve.py did not stop cleanly after saving"
[ -s "$HOME/Muster/.setup-choices.json" ] || fail "choices file missing"
$PY -c 'import json,sys;d=json.load(open(sys.argv[1],encoding="utf-8"));assert d["project"]==sys.argv[2],d' "$HOME/Muster/.setup-choices.json" "$PROJECT" || fail "saved project name differs"
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
for f in CREW DECISIONS-LOG BOARD OWNERS-LIST REPORT START-NOTE RULES-PAGE LOOK-BOOK CLAUDE; do
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

step "tests on disk are listed in CHECKS.md (scripts/check-tests.py)"
$PY "$ROOT/scripts/check-tests.py" "$(native "$FOLDER")" || fail "no test files should pass"
: > "$FOLDER/test_demo.py"
$PY "$ROOT/scripts/check-tests.py" "$(native "$FOLDER")" | tee "$SCRATCH/ct.out" || true
grep -q "1 test file(s) on disk, 1 missing" "$SCRATCH/ct.out" || fail "unlisted test file was not caught: $(cat "$SCRATCH/ct.out")"
echo "test_demo.py: demo | python -m pytest | not checked yet" > "$FOLDER/muster/CHECKS.md"
$PY "$ROOT/scripts/check-tests.py" "$(native "$FOLDER")" || fail "listed test file was refused"

step "board digest with no role name, and the Waiting on line"
printf '# Board\n\n## Entries\n### 2026-01-31 | READY | Builder A_X_001 -> Inspector_X_001 | demo\nStatus: open\n' > "$FOLDER/muster/BOARD.md"
OUT=$(cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py") || fail "digest with no role failed"
echo "$OUT" | grep -q "concern Manager " || fail "summary does not name the role: $OUT"
OUT2=$(cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" Inspector_X_001) || fail "digest failed"
echo "$OUT2" | grep -q "1 entries concern Inspector_X_001 " || fail "summary does not name Inspector_X_001: $OUT2"
(cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" Manager --write-waiting >/dev/null) || fail "--write-waiting failed"
head -3 "$FOLDER/muster/BOARD.md" | grep -q "^Waiting on: Inspector_X_001 (1)" || fail "no Waiting on line at the top of BOARD.md: $(head -4 "$FOLDER/muster/BOARD.md")"
[ "$(grep -c "^Waiting on:" "$FOLDER/muster/BOARD.md")" = 1 ] || fail "more than one Waiting on line"
(cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" Manager --write-waiting >/dev/null)
[ "$(grep -c "^Waiting on:" "$FOLDER/muster/BOARD.md")" = 1 ] || fail "second write added another line"
echo "$OUT" | grep -q "Waiting on: Inspector_X_001 (1)" || fail "no Waiting on line: $OUT"

step "a pretend order, READY and PASS on this project"
mkdir -p "$SCRATCH/msgs"
printf 'Job:     pretend job\n' > "$SCRATCH/msgs/order.txt"
printf 'READY: pretend job [ID Builder A-pretend job-1]\nWhat:  changed one line\nWhere: line of work builder/x, saved version abc1234; touches: none\nWhy:   the pretend order\nHow:   test command `echo ok`: 3/3 passed, 0 failed\nNeed:  nothing; ready for the inspector\n' > "$SCRATCH/msgs/ready.txt"
printf 'PASS: pretend job [ID Inspector-pretend job-1]\nWhat:  checked it\nWhere: builder/x; touches: none\nWhy:   the READY\nHow:   3/3 passed on my own run\nNeed:  nothing\n' > "$SCRATCH/msgs/pass.txt"
printf 'READY: pretend job\nWhat: x\n' > "$SCRATCH/msgs/bad.txt"
for m in ready pass; do $PY "$ROOT/scripts/check-report.py" "$(native "$SCRATCH/msgs/$m.txt")" | grep -q '^OK' || fail "$m report refused"; done
if $PY "$ROOT/scripts/check-report.py" "$(native "$SCRATCH/msgs/bad.txt")" >/dev/null; then fail "a malformed report was accepted"; fi
grep -q "pretend job" "$SCRATCH/msgs/order.txt" || fail "order lost its job name"
printf '# Board\n\n## Entries\n### 2026-01-31 | READY | Builder A_X_001 -> Inspector_X_001 | pretend job\nStatus: open\n### 2026-01-31 | PASS | Inspector_X_001 -> Builder A_X_001 | pretend job\nStatus: open\n' > "$FOLDER/muster/BOARD.md"
(cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" Inspector_X_001) | grep -q "entries concern Inspector_X_001" || fail "inspector does not see the READY"
(cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" "Builder A_X_001") | grep -q "entries concern Builder A_X_001" || fail "builder does not see the PASS"

step "muster-update brings crew files up to date and keeps the project's records"
printf 'old rules\n' > "$FOLDER/muster/CLAUDE.md"
printf '1. "my own words"\n' > "$FOLDER/muster/OWNERS-LIST.md"
rm -f "$FOLDER/muster/LOOK-BOOK.md"
FN=$(native "$FOLDER")
$PY "$ROOT/scripts/muster-update.py" "$FN" | grep -q "dry run" || fail "dry run did not say so"
[ "$(cat "$FOLDER/muster/CLAUDE.md")" = "old rules" ] || fail "dry run changed a file"
$PY "$ROOT/scripts/muster-update.py" "$FN" --apply > "$SCRATCH/upd.out" || fail "update failed"
cmp -s "$FOLDER/muster/CLAUDE.md" "$ROOT/templates/CLAUDE.md" || fail "CLAUDE.md not brought up to date"
ls "$FOLDER"/muster/superseded/CLAUDE.* >/dev/null 2>&1 || fail "old CLAUDE.md not kept in superseded/"
grep -q '"my own words"' "$FOLDER/muster/OWNERS-LIST.md" || fail "a record was overwritten"
[ -f "$FOLDER/muster/LOOK-BOOK.md" ] || fail "look book not added"
grep -q "Note for" "$SCRATCH/upd.out" || fail "no per-worker note printed: $(cat "$SCRATCH/upd.out")"
$PY "$ROOT/scripts/muster-update.py" "$FN" | grep -q "Already up to date" || fail "second run did not stop"

step "auto-update switch (scripts/enable-autoupdate.py) in a scratch settings folder"
AU="$SCRATCH/claude-config"; mkdir -p "$AU"
printf '{"theme":"dark","extraKnownMarketplaces":{"muster-kit":{"source":{"source":"github","repo":"d4rthban3/muster"}}}}' > "$AU/settings.json"
CLAUDE_CONFIG_DIR=$(native "$AU") $PY "$ROOT/scripts/enable-autoupdate.py" | grep -q "now on\|is on" || fail "auto-update switch not set"
$PY -c 'import json,sys;d=json.load(open(sys.argv[1]));e=d["extraKnownMarketplaces"]["muster-kit"];assert e["autoUpdate"] is True and d["theme"]=="dark" and e["source"]["repo"]=="d4rthban3/muster"' "$(native "$AU/settings.json")" || fail "settings not kept or switch missing"
[ -f "$AU/settings.json.muster-backup" ] || fail "no backup kept"
printf '{}' > "$AU/settings.json"
if CLAUDE_CONFIG_DIR=$(native "$AU") $PY "$ROOT/scripts/enable-autoupdate.py" >/dev/null; then fail "wrote a switch for an undeclared marketplace"; fi

step "scripts/record-choice.py writes a choice under its list item"
printf '# List\n\n## Open\n1. "first"\n   Kind: order\n\n2. "second"\n   Kind: question\n\n## Closed\n' > "$FOLDER/muster/OWNERS-LIST.md"
$PY "$ROOT/scripts/record-choice.py" "$FN" 1 --question "Which one?" --option "A. red" --option "B. blue" --picked "B. blue" --said "blue please" >/dev/null || fail "record-choice failed"
sed -n 1,12p "$FOLDER/muster/OWNERS-LIST.md" | tr '\n' '~' | grep -q 'Kind: order~   Choice ([0-9-]*): Which one?~     Options: A. red | B. blue~     Picked: B. blue~     He said: blue please~~2\. "second"' || fail "choice not under item 1: $(cat "$FOLDER/muster/OWNERS-LIST.md")"
if $PY "$ROOT/scripts/record-choice.py" "$FN" 9 --question q --option "A. x" --picked "A. x" >/dev/null 2>&1; then fail "a missing item was accepted"; fi
if $PY "$ROOT/scripts/record-choice.py" "$FN" 2 --question q --option "A. x" --picked "C. nope" >/dev/null 2>&1; then fail "a picked text outside the options was accepted"; fi

echo; echo "ALL STEPS PASSED"
