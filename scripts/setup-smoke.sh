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
printf '/muster/\n/.muster-paused\n' >> .git/info/exclude
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

step "a paused chat reaches the owner through the board"
printf '# Board\n\n## Entries\n### 2026-01-31 | NEED | Builder A_X_001 -> Manager | demo\nStatus: open\nPaused: yes\n' > "$FOLDER/muster/BOARD.md"
OUT3=$(cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" Manager --write-waiting) || fail "digest of a paused entry failed"
echo "$OUT3" | grep -q "^OWNER QUESTIONS" || fail "no OWNER QUESTIONS block for a paused NEED: $OUT3"
head -3 "$FOLDER/muster/BOARD.md" | grep -q "^Waiting on: waiting for you: type in Builder A_X_001" || fail "Waiting on line does not name the paused chat: $(head -4 "$FOLDER/muster/BOARD.md")"

step "the manager's Stop hook blocks on an unmentioned paused chat, and stays silent for everyone else"
mkdir -p "$SCRATCH/tr"
printf '{"type":"user","message":{"role":"user","content":"First: read the plugin folder/agents/manager.md and follow it. You are Manager_X_001."}}\n' > "$SCRATCH/tr/manager.jsonl"
printf '{"type":"queue-operation"}\n{"type":"user","message":{"role":"user","content":"please fix the header art on my page"}}\n' > "$SCRATCH/tr/owner.jsonl"
hook() { (cd "$FOLDER" && printf '{"cwd":"%s","transcript_path":"%s","stop_hook_active":%s,"last_assistant_message":"%s"}' "$(native "$FOLDER")" "$(native "$SCRATCH")/tr/$1.jsonl" "$2" "$3" | sh "$ROOT/hooks/board-stop.sh"); }
printf '# Board\n\n## Entries\n### 2026-01-31 | NEED | Builder A_X_001 -> Manager | demo\nStatus: open\nPaused: yes\n' > "$FOLDER/muster/BOARD.md"
hook manager false "all done" | grep -q '"decision": "block"' || fail "Stop hook did not block the manager on a paused chat it never named"
hook owner false "all done" | grep -q . && fail "Stop hook spoke in the owner's own chat in the main folder"
hook manager false "Builder A_X_001 is waiting for you" | grep -q . && fail "Stop hook blocked although the paused chat was named"
hook manager true "all done" | grep -q . && fail "Stop hook blocked while already continuing (it could loop)"
printf '# Board\n\n## Entries\n### 2026-01-31 | NEED | Builder A_X_001 -> Manager | demo\nStatus: done\n' > "$FOLDER/muster/BOARD.md"
hook manager false "all done" | grep -q . && fail "Stop hook spoke on a clean board"
printf '### 2026-01-31 | NEED | Builder A_X_001 -> Manager | demo\nStatus: open\n' >> "$FOLDER/muster/BOARD.md"
(cd "$FOLDER" && printf '{"cwd":"%s/.claude/worktrees/b","transcript_path":"%s","last_assistant_message":""}' "$(native "$FOLDER")" "$(native "$SCRATCH")/tr/manager.jsonl" | sh "$ROOT/hooks/board-stop.sh" | grep -q .) && fail "Stop hook ran in a worker copy"
$PY -c "import json;json.load(open('$(native "$ROOT")/hooks/hooks.json'))" || fail "hooks/hooks.json is not valid JSON"

step "a manager never picks for the owner: decide.py needs his click or words, and the Stop hook catches 'I am recording it'"
FN=$(native "$FOLDER")
printf '# List\n\n## Open\n1. "which colour"\n   Kind: question\n   Choice (2026-01-01): Which?\n     Options: A. red | B. blue\n     Picked: B. blue\n     He said: go with blue please\n\n2. "no click yet"\n   Kind: question\n\n## Closed\n' > "$FOLDER/muster/OWNERS-LIST.md"
printf '# Decisions log\n\n### D-001 · 2026-01-01 · first\nDecision: x\n' > "$FOLDER/muster/DECISIONS-LOG.md"
$PY "$ROOT/scripts/decide.py" "$FN" --item 1 --title "Colour" --decision "blue" --why "he picked" --picked "B. blue" >/dev/null || fail "decide.py refused a decision that rests on a recorded click"
grep -q "^### D-002 · [0-9-]* · Colour" "$FOLDER/muster/DECISIONS-LOG.md" || fail "decide.py did not number D-002: $(cat "$FOLDER/muster/DECISIONS-LOG.md")"
$PY "$ROOT/scripts/decide.py" "$FN" --item 1 --title "Said" --decision "blue" --why "w" --said "go with blue please" --chose "blue" >/dev/null || fail "decide.py refused his own recorded words"
if $PY "$ROOT/scripts/decide.py" "$FN" --item 2 --title "Guess" --decision "red" --why "w" --picked "A. red" >/dev/null 2>&1; then fail "decide.py took a pick that was never clicked"; fi
if $PY "$ROOT/scripts/decide.py" "$FN" --item 2 --title "Guess" --decision "red" --why "w" --said "it seems he wants red" >/dev/null 2>&1; then fail "decide.py took words that are not under the item"; fi
printf '# List\n\n## Open\n3. "make the header blue or maybe green, whatever looks better"\n   Kind: question\n   Did: manager thinks blue fits what he wants\n\n## Closed\n' > "$FOLDER/muster/OWNERS-LIST.md"
if $PY "$ROOT/scripts/decide.py" "$FN" --item 3 --title "Mgr" --decision "blue" --why "w" --said "manager thinks blue fits" --chose "blue" >/dev/null 2>&1; then fail "decide.py took the manager's own line as his words"; fi
if $PY "$ROOT/scripts/decide.py" "$FN" --item 3 --title "Vague" --decision "blue" --why "w" --said "whatever looks better" >/dev/null 2>&1; then fail "decide.py took words that do not name the choice"; fi
if $PY "$ROOT/scripts/decide.py" "$FN" --item 3 --title "Vague" --decision "blue" --why "w" --said "whatever looks better" --chose "blue" >/dev/null 2>&1; then fail "decide.py took words that do not contain the option name"; fi
if $PY "$ROOT/scripts/decide.py" "$FN" --item 3 --title "Piece" --decision "blue" --why "w" --said "make the header blue" --chose "blue" >/dev/null 2>&1; then fail "decide.py took a piece cut out of his line"; fi
if $PY "$ROOT/scripts/decide.py" "$FN" --item 3 --title "Open" --decision "blue" --why "w" --said "make the header blue or maybe green, whatever looks better" --chose "blue" >/dev/null 2>&1; then fail "decide.py took his blue-or-green line as a pick of blue"; fi
printf '# List\n\n## Open\n5. "use blue for the header"\n   Kind: question\n   Choice (2026-01-01): Which?\n     He said: pick green or blue, either\n\n6. "use green for the header"\n   Kind: question\n\n## Closed\n' > "$FOLDER/muster/OWNERS-LIST.md"
if $PY "$ROOT/scripts/decide.py" "$FN" --item 5 --title "Names" --decision "blue" --why "w" --said "use blue for the header" --chose "blue" --others "header" >/dev/null 2>&1; then fail "decide.py ignored a second option named in his words"; fi
if $PY "$ROOT/scripts/decide.py" "$FN" --item 5 --title "Hedge" --decision "blue" --why "w" --said "pick green or blue, either" --chose "blue" >/dev/null 2>&1; then fail "decide.py took a hedged He said line"; fi
$PY "$ROOT/scripts/decide.py" "$FN" --item 5 --title "Ok" --decision "blue" --why "w" --said "use blue for the header" --chose "blue" --others "green" >/dev/null || fail "decide.py refused his whole clear line"
if $PY "$ROOT/scripts/decide.py" "$FN" --item 1 --title "Nothing" --decision "red" --why "w" >/dev/null 2>&1; then fail "decide.py took a decision with no proof"; fi
[ "$(grep -c '^### D-' "$FOLDER/muster/DECISIONS-LOG.md")" = 4 ] || fail "decisions log changed by a refused call"
printf '# Board\n\n## Entries\n' > "$FOLDER/muster/BOARD.md"
cp "$SCRATCH/tr/manager.jsonl" "$SCRATCH/tr/mgr-card.jsonl"
printf '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"AskUserQuestion","input":{}}]}}\n' >> "$SCRATCH/tr/mgr-card.jsonl"
hook manager false "So C fits what you want, and I am recording it." | grep -q '"decision": "block"' || fail "Stop hook did not catch a manager choosing for the owner"
hook mgr-card false "So C fits what you want, and I am recording it." | grep -q . && fail "Stop hook blocked although a choice card was answered this turn"
hook manager false "You picked B, so I am recording it." | grep -q . && fail "Stop hook blocked although the message says he picked"
hook manager false "You said you want it calm, so C fits what you want, I am recording it." | grep -q '"decision": "block"' || fail "Stop hook let through 'you said ... I am recording it'"
hook manager true "I am recording it." | grep -q . && fail "Stop hook blocked while already continuing"

step "a paused chat that resumed reads clear; one that did not still blocks; the marker file works"
printf '# Board\n\n## Entries\n### 2026-01-31 | DONE | Builder A_X_001 -> Manager | demo\nStatus: open\nPaused: yes\n' > "$FOLDER/muster/BOARD.md"
hook manager false "all done" | grep -q '"decision": "block"' || fail "paused with no later line must still block"
printf '### 2026-01-31 | DONE | Builder A_X_001 -> Manager | next job\nStatus: open\n' >> "$FOLDER/muster/BOARD.md"
hook manager false "all done" | grep -q . && fail "a later entry from the same chat did not clear the paused line (hook)"
OUT4=$(cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" Manager)
echo "$OUT4" | grep -q "waiting for you" && fail "digest still names a resumed chat paused: $OUT4"
printf '# Board\n\n## Entries\n### 2026-01-31 | NEED | Builder A_X_001 -> Manager | demo\nStatus: open\nPaused: yes\nPaused: no\n' > "$FOLDER/muster/BOARD.md"
hook manager false "all done" | grep -q '"decision": "block"' || fail "a NEED still waiting must block even when resumed"
printf '# Board\n\n## Entries\n### 2026-01-31 | READY | Builder A_X_001 -> Inspector_X_001 | demo\nStatus: done\nPaused: yes\nPaused: no\n' > "$FOLDER/muster/BOARD.md"
hook manager false "all done" | grep -q . && fail "Paused: no did not clear the paused line (hook)"
printf '# Board\n\n## Entries\n### 2026-01-31 | READY | Builder A_X_001 -> Inspector_X_001 | demo\nStatus: open\nPaused: yes\n' > "$FOLDER/muster/BOARD.md"
OUT5=$(cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" Manager)
echo "$OUT5" | grep -q "waiting for you: type in Builder A_X_001" || fail "digest missed a paused entry addressed to someone else: $OUT5"
printf '# Board\n\n## Entries\n' > "$FOLDER/muster/BOARD.md"
mkdir -p "$FOLDER/.claude/worktrees/builder-b-001"; printf 'Builder B_X_001\n' > "$FOLDER/.claude/worktrees/builder-b-001/.muster-paused"
hook manager false "all done" | grep -q '"decision": "block"' || fail "the .muster-paused marker file was not read"
rm -f "$FOLDER/.claude/worktrees/builder-b-001/.muster-paused"
hook manager false "all done" | grep -q . && fail "hook spoke after the marker file was deleted"

step "Muster for Cursor: cursor/setup.py builds the crew, the rules and the Stop check, with no Claude Code"
CU="$SCRATCH/cursor"; mkdir -p "$CU"
$PY "$ROOT/cursor/setup.py" "$(native "$CU")/Bob Shop" --name "Bob Shop" --vision "a small shop site" > "$CU/setup.out" 2>&1 || { cat "$CU/setup.out"; fail "cursor/setup.py failed"; }
CM="$CU/Bob Shop"
for f in muster-core muster-manager muster-builder muster-designer muster-inspector; do [ -f "$CM/.cursor/rules/$f.mdc" ] || fail "missing Cursor rule $f.mdc"; done
grep -q "^alwaysApply: true" "$CM/.cursor/rules/muster-core.mdc" || fail "the core rule is not always on"
grep -q "{{MAIN}}" "$CM/.cursor/rules/muster-core.mdc" && fail "the core rule kept its {{MAIN}} placeholder"
[ -f "$CU/Bob Shop_copies/builder-a-001/.cursor/rules/muster-builder.mdc" ] || fail "a worker copy has no Muster rules"
[ -f "$CM/muster/start-notes/Builder A_Bob Shop_001.md" ] || fail "no starting note for the builder"
[ -z "$(git -C "$CM" status --porcelain)" ] || fail "setup left files that are not kept out of the history: $(git -C "$CM" status --porcelain)"
$PY -c "import json,sys;json.load(open(sys.argv[1]))" "$(native "$CM")/.cursor/hooks.json" || fail ".cursor/hooks.json is not valid JSON"
(cd "$CM" && $PY muster/tools/board_digest.py Manager >/dev/null) || fail "the board digest does not run from muster/tools"
printf '# Board\n\n## Entries\n### 2026-01-31 | NEED | Builder A_Bob Shop_001 -> Manager | demo\nStatus: open\n' > "$CM/muster/BOARD.md"
printf 'You are Manager_Bob Shop_001' > "$CU/mgr.txt"; printf 'please fix my header' > "$CU/owner.txt"
cstop() { (cd "$CM" && printf '{"workspace_roots":["%s"],"transcript_path":"%s","loop_count":%s}' "$(native "$CM")" "$(native "$CU")/$1" "$2" | $PY muster/tools/cursor-stop.py); }
cstop owner.txt 0 | grep -q followup_message && fail "the Cursor stop check spoke in a chat that is not the manager's"
cstop mgr.txt 1 | grep -q followup_message && fail "the Cursor stop check ran as a follow-up (it could loop)"
cstop mgr.txt 0 | grep -q followup_message || fail "the Cursor stop check did not tell the manager about an open NEED"
cstop mgr.txt 0 | grep -q followup_message && fail "the Cursor stop check flagged the same item twice"

step "second founder computer: --join on a project that already has muster/ changes nothing in it"
snap() { (cd "$CM" && find muster .git/config -type f -print0 | sort -z | xargs -0 cat | cksum); }
BEFORE_SNAP=$(snap)
$PY "$ROOT/cursor/setup.py" "$(native "$CM")" --name "Bob Shop" --join --computer laptop2 --other desk1 --copies clone --copies-dir "$(native "$CU")/clones" > "$CU/join.out" 2>&1 || { cat "$CU/join.out"; fail "cursor/setup.py --join failed"; }
[ "$(snap)" = "$BEFORE_SNAP" ] || fail "--join changed something inside muster/ or .git/config"
WS="$CU/laptop2 Workspace"
for f in CHANGES.md START-HERE.md git-as.sh tools/board_digest.py; do [ -f "$WS/$f" ] || fail "--join did not make $f in the workspace"; done
[ -e "$CU/desk1 Workspace" ] && fail "--join wrote the other computer's workspace folder"
[ -f "$CM/.cursor/rules/muster-laptop2-core.mdc" ] || fail "--join did not write this computer's Cursor rules"
grep -q "Never override desk1" "$CM/.cursor/rules/muster-laptop2-core.mdc" || fail "the two-computer lines are missing from the rules"
[ -z "$(git -C "$CM" status --porcelain)" ] || fail "--join left files the shared project would commit: $(git -C "$CM" status --porcelain)"
sh "$WS/git-as.sh" -C "$CU/clones/builder-a-laptop2" commit -q --allow-empty -m t && [ "$(git -C "$CU/clones/builder-a-laptop2" log -1 --format=%an)" = laptop2 ] || fail "git-as.sh did not commit as laptop2"
git -C "$CU/clones/builder-a-laptop2" rev-parse --abbrev-ref HEAD | grep -q '^laptop2/' || fail "the clone is not on a laptop2/ branch"
$PY "$ROOT/cursor/setup.py" "$(native "$CU")/nothing here" --name X --join --computer laptop2 --other desk1 >/dev/null 2>&1 && fail "--join accepted a folder with no muster/"
grep -q "^## 9c. Two founder computers" "$ROOT/templates/CLAUDE.md" || fail "the two-computer rules are missing from the core rules"

step "a pretend order, READY and PASS on this project"
mkdir -p "$SCRATCH/msgs"
printf 'Job:     pretend job\n' > "$SCRATCH/msgs/order.txt"
printf 'READY: pretend job [ID Builder A-pretend job-1]\nWhat:  changed one line\nWhere: line of work builder/x, saved version abc1234; touches: none\nWhy:   the pretend order\nHow:   test command `echo ok`: 3/3 passed, 0 failed\nNeed:  nothing; ready for the inspector\nUsage: session $0.10 at list price; week 12%% used; read at 10:00\n' > "$SCRATCH/msgs/ready.txt"
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
printf '{"theme":"dark","extraKnownMarketplaces":{"muster-kit":{"source":{"source":"github","repo":"desk1/muster"}}}}' > "$AU/settings.json"
CLAUDE_CONFIG_DIR=$(native "$AU") $PY "$ROOT/scripts/enable-autoupdate.py" | grep -q "now on\|is on" || fail "auto-update switch not set"
$PY -c 'import json,sys;d=json.load(open(sys.argv[1]));e=d["extraKnownMarketplaces"]["muster-kit"];assert e["autoUpdate"] is True and d["theme"]=="dark" and e["source"]["repo"]=="desk1/muster"' "$(native "$AU/settings.json")" || fail "settings not kept or switch missing"
[ -f "$AU/settings.json.muster-backup" ] || fail "no backup kept"
printf '{}' > "$AU/settings.json"
if CLAUDE_CONFIG_DIR=$(native "$AU") $PY "$ROOT/scripts/enable-autoupdate.py" >/dev/null; then fail "wrote a switch for an undeclared marketplace"; fi

step "scripts/live-check.sh proves served content (version, and a page line) and refuses what is not served"
# the published version can change between reading it and checking it (right after a push): read it again and retry
proved=""
for _try in 1 2 3 4; do
  LV=$(curl -fsS https://raw.githubusercontent.com/d4rthban3/muster/main/.claude-plugin/plugin.json | grep -o '"version": *"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
  if LIVE_CHECK_TRIES=2 bash "$ROOT/scripts/live-check.sh" "$LV" | grep -q "LIVE PROVEN"; then proved=1; break; fi
  sleep 10
done
[ -n "$proved" ] || fail "live check did not prove the published version $LV"
if LIVE_CHECK_TRIES=1 bash "$ROOT/scripts/live-check.sh" 0.0.1 >/dev/null; then fail "live check accepted a wrong version"; fi
if LIVE_CHECK_TRIES=1 bash "$ROOT/scripts/live-check.sh" "$LV" docs/index.html "a line that is certainly not on the page 9f3k" >/dev/null; then fail "live check accepted a missing page line"; fi

step "scripts/ship.sh on a scratch repository (dry run, then a real push to a scratch remote)"
SH="$SCRATCH/ship"; mkdir -p "$SH/remote.git" "$SH/work"
git init -q --bare "$SH/remote.git"
cd "$SH/work"; git init -q -b main; git remote add origin "$SH/remote.git"
mkdir -p .claude-plugin/releases scripts
cp "$ROOT/scripts/ship.sh" "$ROOT/scripts/find-python.sh" "$ROOT/scripts/version-check.sh" "$ROOT/scripts/scan-leaks.sh" scripts/
printf '{\n  "name": "muster",\n  "version": "1.2.3"\n}\n' > .claude-plugin/plugin.json
printf '{\n  "name": "muster-kit",\n  "plugins": [\n    {\n      "name": "muster",\n      "version": "1.2.3"\n    }\n  ]\n}\n' > .claude-plugin/marketplace.json
printf '# Changelog\n\nEach version names who is affected.\n\n## 1.2.3\nold\n' > CHANGELOG.md
git add -A; git -c user.name=t -c user.email=t@localhost commit -q -m base; git push -q origin main
git checkout -q -b builder/demo; echo hi > file.txt; git add -A; git -c user.name=t -c user.email=t@localhost commit -q -m "change"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@localhost GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@localhost
BEFORE=$(git rev-parse HEAD)
bash scripts/ship.sh "demo change" --roles Builder --dry-run | tee "$SH/dry.out" | tail -2
grep -q "SHIP DRY RUN OK: would push 1.2.4" "$SH/dry.out" || fail "ship dry run did not say 1.2.4: $(cat "$SH/dry.out")"
[ "$(git -C "$SH/remote.git" rev-parse main)" = "$(git rev-parse origin/main)" ] || fail "the dry run pushed"
[ "$(git rev-parse HEAD)" = "$BEFORE" ] || fail "the dry run left a commit on the branch"
[ -z "$(git status --porcelain --untracked-files=no)" ] || fail "the dry run left changes"
bash scripts/ship.sh "second try" --roles Builder --dry-run >"$SH/dry2.out" 2>&1 || { cat "$SH/dry2.out"; fail "second dry run failed"; }; [ "$(git rev-parse HEAD)" = "$BEFORE" ] || fail "a second dry run changed the branch"
bash scripts/ship.sh "demo change" --roles Builder --no-wait | tail -2 | tee "$SH/real.out"
grep -q "SHIPPED 1.2.4" "$SH/real.out" || fail "ship did not finish: $(cat "$SH/real.out")"
git -C "$SH/remote.git" show main:.claude-plugin/plugin.json | grep -q '"1.2.4"' || fail "main on the remote lacks 1.2.4"
git -C "$SH/remote.git" show main:.claude-plugin/releases/1.2.4.json | grep -q "demo change" || fail "no release file on the remote"
git -C "$SH/remote.git" show main:CHANGELOG.md | grep -q "^## 1.2.4" || fail "no changelog entry on the remote"
git -C "$SH/remote.git" for-each-ref --format='%(refname)' | grep -q "ship/" && fail "the temporary ship branch was left behind"
git checkout -q -b builder/demo2 origin/main; echo two > two.txt
printf '{\n  "name": "muster",\n  "version": "1.2.5"\n}\n' > .claude-plugin/plugin.json
printf '{\n  "name": "muster-kit",\n  "plugins": [\n    {\n      "name": "muster",\n      "version": "1.2.5"\n    }\n  ]\n}\n' > .claude-plugin/marketplace.json
printf '{"version":"1.2.5","note":"my own note"}\n' > .claude-plugin/releases/1.2.5.json
$PY - <<'PY'
c = open("CHANGELOG.md").read(); i = c.index("\n## ") + 1
open("CHANGELOG.md", "w").write(c[:i] + "## 1.2.5\nAffects: Builder.\nmy own note\n\n" + c[i:])
PY
git add -A; git commit -q -m "change two"
bash scripts/ship.sh "a different note" --no-wait > "$SH/keep.out" 2>&1; grep -q "SHIPPED 1.2.5" "$SH/keep.out" || { cat "$SH/keep.out"; fail "ship refused a branch that already has its version"; }
[ "$(grep -c '^## 1.2.5' CHANGELOG.md)" = 1 ] || fail "the changelog entry was doubled"
grep -q "my own note" .claude-plugin/releases/1.2.5.json || fail "the branch's own release file was overwritten"
git checkout -q origin/main 2>/dev/null; git checkout -q -b builder/other origin/main; echo o > other.txt; git add -A; git commit -q -m "other piece"
git checkout -q -b builder/batch origin/main; echo b > batch.txt; git add -A; git commit -q -m "batch piece"
bash scripts/ship.sh "batch" --with builder/other --dry-run > "$SH/batch.out" 2>&1 || { cat "$SH/batch.out"; fail "batch dry run failed"; }
grep -q "batch: merged builder/other" "$SH/batch.out" && grep -q "other.txt" "$SH/batch.out" && grep -q "batch.txt" "$SH/batch.out" || fail "batch did not carry both pieces: $(cat "$SH/batch.out")"
if bash scripts/ship.sh "batch" --with builder/nope --dry-run >/dev/null 2>&1; then fail "ship accepted a --with branch that does not exist"; fi
cd "$FOLDER"
step "the renewal hook speaks only in a crew chat, never in the owner's own chat"
mkdir -p "$SCRATCH/tr" "$SCRATCH/plain"
printf '{"type":"user","message":{"role":"user","content":"First: read the plugin folder/agents/builder.md. You are Builder A_X_001."}}\n' > "$SCRATCH/tr/builder.jsonl"
printf '{"type":"user","message":{"role":"user","content":"First: read the plugin folder/agents/manager.md. You are Manager_X_001."}}\n' > "$SCRATCH/tr/manager.jsonl"
printf '{"type":"user","message":{"role":"user","content":"please fix the header art on my page"}}\n' > "$SCRATCH/tr/owner.jsonl"
renew() { (cd "$2" && printf '{"transcript_path":"%s"}' "$(native "$SCRATCH")/tr/$1.jsonl" | sh "$ROOT/hooks/renew-after-summary.sh"); }
printf '{"type":"user","message":{"role":"user","content":"Your five-line starting note. Job: build. Not yours: ask Manager_Shop_001 when unsure. First: read /p/agents/builder.md. Manager_Shop_001 gives every order."}}\n' > "$SCRATCH/tr/worker2.jsonl"
printf '{"type":"user","message":{"role":"user","content":"You are Inspector_Shop_001. Manager_Shop_001 gives every order. First: read /p/agents/inspector.md"}}\n' > "$SCRATCH/tr/inspector.jsonl"
printf '{"type":"user","message":{"role":"user","content":"You are Builder A_Shop_001. Ask Manager_Shop_001 when unsure."}}\n' > "$SCRATCH/tr/worker3.jsonl"
renew worker2 "$FOLDER" | grep -q "DONE: renewal" || fail "a worker whose note names the manager and a builder role file got the manager wording"
renew inspector "$FOLDER" | grep -q "DONE: renewal" || fail "an inspector whose note names the manager got the manager wording"
renew worker3 "$FOLDER" | grep -q "DONE: renewal" || fail "a worker with no role file whose note names the manager got the manager wording"
renew builder "$SCRATCH/plain" | grep -q . && fail "renewal hook spoke outside a crew project"
renew owner "$FOLDER" | grep -q . && fail "renewal hook spoke in the owner's own chat in the main folder"
renew builder "$FOLDER" | grep -q "DONE: renewal" || fail "renewal hook was silent for a worker"
mkdir -p "$FOLDER/.claude/worktrees/w1"
renew builder "$FOLDER/.claude/worktrees/w1" | grep -q "DONE: renewal" || fail "renewal hook was silent in a worker copy"
renew builder "$FOLDER" | grep -q "how to talk to the owner" || fail "the talking block did not come back after a summary"
renew owner "$FOLDER" | grep -q "how to talk to the owner" && fail "the talking block was added to the owner's own chat"
renew manager "$FOLDER" | grep -q "fresh manager chat" || fail "renewal hook did not give the manager its own wording"
renew manager "$FOLDER" | grep -q "DONE: renewal" && fail "the manager was told to send DONE: renewal to itself"

step "the talking check flags a bare path or version code once, and only in a crew chat"
talk() { (cd "$FOLDER" && printf '{"stop_hook_active":%s,"transcript_path":"%s","last_assistant_message":"%s"}' "$2" "$(native "$SCRATCH")/tr/$1.jsonl" "$3" | sh "$ROOT/hooks/talk-check.sh"); }
talk builder false "Fixed scripts/ship.sh now." | grep -q '"decision": "block"' || fail "a bare path was not flagged"
talk builder false "Saved version 8f6f1d9 is ready." | grep -q '"decision": "block"' || fail "a saved-version code was not flagged"
talk builder true "Fixed scripts/ship.sh now." | grep -q . && fail "the talking check blocked twice in a row"
talk builder false "Fixed [the script](scripts/ship.sh); 22 of 22 passed." | grep -q . && fail "a linked file was flagged"
talk owner false "Fixed scripts/ship.sh now." | grep -q . && fail "the talking check spoke in the owner's own chat"
step "scripts/record-choice.py writes a choice under its list item"
printf '# List\n\n## Open\n1. "first"\n   Kind: order\n\n2. "second"\n   Kind: question\n\n## Closed\n' > "$FOLDER/muster/OWNERS-LIST.md"
$PY "$ROOT/scripts/record-choice.py" "$FN" 1 --question "Which one?" --option "A. red" --option "B. blue" --picked "B. blue" --said "blue please" >/dev/null || fail "record-choice failed"
sed -n 1,12p "$FOLDER/muster/OWNERS-LIST.md" | tr '\n' '~' | grep -q 'Kind: order~   Choice ([0-9-]*): Which one?~     Options: A. red | B. blue~     Picked: B. blue~     He said: blue please~~2\. "second"' || fail "choice not under item 1: $(cat "$FOLDER/muster/OWNERS-LIST.md")"
printf '# List\n\nExample:\n```\n7. made-up example\n   Kind: x\n```\n\n## Open\n7. "real seven"\n   Kind: order\n\n## Closed\n' > "$FOLDER/muster/OWNERS-LIST.md"
$PY "$ROOT/scripts/record-choice.py" "$FN" 7 --question "Q?" --option "A. a" --picked "A. a" >/dev/null || fail "record-choice failed on the fenced list"
tr '\n' '~' < "$FOLDER/muster/OWNERS-LIST.md" | grep -q '7\. "real seven"~   Kind: order~   Choice' || fail "choice not under the real item 7"
tr '\n' '~' < "$FOLDER/muster/OWNERS-LIST.md" | grep -q 'made-up example~   Kind: x~```' || fail "the made-up example was changed"
if $PY "$ROOT/scripts/record-choice.py" "$FN" 9 --question q --option "A. x" --picked "A. x" >/dev/null 2>&1; then fail "a missing item was accepted"; fi
if $PY "$ROOT/scripts/record-choice.py" "$FN" 2 --question q --option "A. x" --picked "C. nope" >/dev/null 2>&1; then fail "a picked text outside the options was accepted"; fi

step "usage meter: status line saves usage, usage.py reads it, pauses near the limit, settings kept"
UM="$SCRATCH/um"; mkdir -p "$UM"; export_cfg=$(native "$UM")
printf '{"theme":"dark"}' > "$UM/settings.json"
CLAUDE_CONFIG_DIR=$export_cfg $PY "$ROOT/scripts/enable-usage-meter.py" "$PY" | grep -q "is on" || fail "usage meter not turned on"
$PY -c 'import json,sys;d=json.load(open(sys.argv[1]));assert d["theme"]=="dark" and d["statusLine"]["type"]=="command"' "$(native "$UM/settings.json")" || fail "settings not kept or no statusLine"
[ -f "$UM/muster-usage/statusline.py" ] || fail "status line script not copied"
echo '{"session_id":"s1","cost":{"total_cost_usd":0.31},"rate_limits":{"seven_day":{"used_percentage":41.2,"resets_at":1738857600}}}' | CLAUDE_CONFIG_DIR=$export_cfg $PY "$UM/muster-usage/statusline.py" | grep -q "week 41%" || fail "status line did not print the week"
rc=0; CLAUDE_CONFIG_DIR=$export_cfg $PY "$ROOT/scripts/usage.py" > "$SCRATCH/u1.out" || rc=$?
grep -q "Usage: session \$0.31 at list price; week 41% used" "$SCRATCH/u1.out" && [ $rc = 0 ] || fail "usage.py wrong: $(cat "$SCRATCH/u1.out") rc=$rc"
echo '{"session_id":"s2","rate_limits":{"seven_day":{"used_percentage":95}}}' | CLAUDE_CONFIG_DIR=$export_cfg $PY "$UM/muster-usage/statusline.py" >/dev/null
rc=0; CLAUDE_CONFIG_DIR=$export_cfg $PY "$ROOT/scripts/usage.py" >/dev/null || rc=$?; [ $rc = 3 ] || fail "usage.py did not exit 3 at 95%"
echo '{"session_id":"s3"}' | CLAUDE_CONFIG_DIR=$export_cfg $PY "$UM/muster-usage/statusline.py" >/dev/null
CLAUDE_CONFIG_DIR=$export_cfg $PY "$ROOT/scripts/usage.py" | grep -q "week limit not readable" || fail "usage.py invented a weekly number"
printf '{"statusLine":{"type":"command","command":"mine"}}' > "$UM/settings.json"
rc=0; CLAUDE_CONFIG_DIR=$export_cfg $PY "$ROOT/scripts/enable-usage-meter.py" "$PY" >/dev/null || rc=$?; [ $rc = 4 ] || fail "replaced someone's own status line"
grep -q '"mine"' "$UM/settings.json" || fail "own status line changed"
printf 'READY: x [ID Builder A-x-1]\nWhat: a\nWhere: b; touches: none\nWhy: c\nHow: 3/3 passed\nNeed: d\n' > "$SCRATCH/msgs/nousage.txt"
if $PY "$ROOT/scripts/check-report.py" "$(native "$SCRATCH/msgs/nousage.txt")" >/dev/null; then fail "a READY without a Usage line was accepted"; fi

echo; echo "ALL STEPS PASSED"
