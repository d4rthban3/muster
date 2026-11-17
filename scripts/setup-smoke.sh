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

step "setup's own questions are lettered lines, never a choice card or buttons (item 89, D-037)"
SETUP="$ROOT/commands/setup.md"
if grep -Eqi "AskUserQuestion|two buttons|each a button|as buttons|its own button|ask one question" "$SETUP"; then fail "commands/setup.md still asks a question as a choice card or buttons: $(grep -Ein 'AskUserQuestion|two buttons|each a button|as buttons|its own button|ask one question' "$SETUP" | head -3)"; fi
[ "$(tr '\n' ' ' < "$SETUP" | grep -o 'lettered question' | wc -l)" -ge 8 ] || fail "commands/setup.md has fewer lettered questions than its choices need"
grep -q '\*\*\*A\.\*\*\*' "$SETUP" || fail "commands/setup.md shows no bold-italic lettered choice"

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
for f in CREW DECISIONS-LOG BOARD OWNERS-LIST REPORT START-NOTE RULES-PAGE LOOK-BOOK CLAUDE PROTOCOL BUILDERS-LOG RISKS; do
  [ -f "$CLAUDE_PLUGIN_ROOT/templates/$f.md" ] || fail "template $f.md missing"
  cp -n "$CLAUDE_PLUGIN_ROOT/templates/$f.md" . || fail "copy $f"
done
: > BOARD-ARCHIVE.md; mkdir -p rules; : > rules/.gitkeep
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
rm "$FOLDER/muster/CHECKS.md"; echo "test_demo.py: demo | python -m pytest | not checked yet" > "$FOLDER/CHECKS.md"
$PY "$ROOT/scripts/check-tests.py" "$(native "$FOLDER")" || fail "test file listed in the top-level CHECKS.md was refused"
rm "$FOLDER/CHECKS.md"; echo "test_demo.py: demo | python -m pytest | not checked yet" > "$FOLDER/muster/CHECKS.md"

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
head -3 "$FOLDER/muster/BOARD.md" | grep -q "^Waiting on: relay his answer to Builder A_X_001" || fail "Waiting on line does not name the paused chat: $(head -4 "$FOLDER/muster/BOARD.md")"

step "an owner question is asked once: --mark-asked lists it apart, a changed entry or his answer brings it back (item 120)"
printf '# Board\n\n## Entries\n### 2026-01-31 | NEED | Builder A_X_001 -> Manager | demo\nStatus: open\nWhat: which first?\n### 2026-01-31 | NEED | Builder A_X_002 -> Manager | other\nStatus: open\n' > "$FOLDER/muster/BOARD.md"
DG() { (cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" Manager "$@"); }
DG | grep -q "^OWNER QUESTIONS" || fail "unmarked NEEDs are not listed as owner questions"
DG --mark-asked demo | grep -q "Marked 1 open entry" || fail "--mark-asked did not mark the one open entry"
grep -q "^Asked: " "$FOLDER/muster/BOARD.md" || fail "no Asked line written"
[ "$(grep -c "^Asked: " "$FOLDER/muster/BOARD.md")" = 1 ] || fail "the other job was marked too"
OUTA=$(DG); echo "$OUTA" | grep -q "^WAITING ON HIS ANSWER" || fail "no waiting-on-his-answer block: $OUTA"
echo "$OUTA" | sed -n '/^OWNER QUESTIONS/,/^$/p' | grep -q "demo" && fail "an asked question is still listed to ask again: $OUTA"
echo "$OUTA" | sed -n '/^OWNER QUESTIONS/,/^$/p' | grep -q "other" || fail "the unasked question vanished: $OUTA"
DG --mark-asked demo >/dev/null; [ "$(grep -c "^Asked: " "$FOLDER/muster/BOARD.md")" = 1 ] || fail "marking twice added a second Asked line"
BP=$(cygpath -m "$FOLDER/muster/BOARD.md" 2>/dev/null || echo "$FOLDER/muster/BOARD.md")
$PY -c "import sys;p=sys.argv[1];t=open(p).read();open(p,'w').write(t.replace('which first?','which first, or later?',1))" "$BP"
DG | sed -n '/^OWNER QUESTIONS/,/^$/p' | grep -q "demo" || fail "a changed question was not brought back"
DG --mark-asked demo >/dev/null
$PY -c "import sys;p=sys.argv[1];t=open(p).read();open(p,'w').write(t.replace('Status: open','Status: done',1))" "$BP"
DG | grep -q "WAITING ON HIS ANSWER" && fail "an answered (done) question is still listed as waiting"
DG --mark-asked nosuchjob | grep -q "NOT MARKED" || fail "marking an unknown job did not say so"

step "the manager's Stop hook blocks on an unmentioned paused chat, and stays silent for everyone else"
mkdir -p "$SCRATCH/tr"
printf '{"type":"user","message":{"role":"user","content":"First: read the plugin folder/agents/manager.md and follow it. You are Manager_X_001."}}\n' > "$SCRATCH/tr/manager.jsonl"
printf '{"type":"queue-operation"}\n{"type":"user","message":{"role":"user","content":"please fix the header art on my page"}}\n' > "$SCRATCH/tr/owner.jsonl"
hook() { (cd "$FOLDER" && printf '{"cwd":"%s","transcript_path":"%s","stop_hook_active":%s,"last_assistant_message":"%s"}' "$(native "$FOLDER")" "$(native "$SCRATCH")/tr/$1.jsonl" "$2" "$3" | sh "$ROOT/hooks/board-stop.sh"); }
printf '# Board\n\n## Entries\n### 2026-01-31 | NEED | Builder A_X_001 -> Manager | demo\nStatus: open\nPaused: yes\n' > "$FOLDER/muster/BOARD.md"
hook manager false "all done" | grep -q '"decision": "block"' || fail "Stop hook did not block the manager on a paused chat it never named"
hook owner false "all done" | grep -q . && fail "Stop hook spoke in the owner's own chat in the main folder"
hook manager false "Relayed his answer to Builder A_X_001" | grep -q . && fail "Stop hook blocked although the paused chat was named"
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
printf '# List\n\n## Open\n8. "which colour"\n   Kind: question\n   Choice (2026-01-01): Which?\n     Options: A. red | B. blue\n     Picked: B. blue\n     He said: b\n\n9. "no letter recorded"\n   Kind: question\n   Choice (2026-01-01): Which?\n     Options: A. red | B. blue\n     Picked: (no pick: he answered in his own words)\n     He said: surprise me\n\n## Closed\n' > "$FOLDER/muster/OWNERS-LIST.md"
$PY "$ROOT/scripts/decide.py" "$FN" --item 8 --title "Letter" --decision "blue" --why "he typed b" --said "b" >/dev/null || fail "decide.py refused his typed letter recorded under the item (item 80)"
grep -q "Chosen by: his typed letter (B. blue) (list item 8)" "$FOLDER/muster/DECISIONS-LOG.md" || fail "decide.py did not record the typed letter's option"
if $PY "$ROOT/scripts/decide.py" "$FN" --item 9 --title "Letter" --decision "blue" --why "w" --said "b" >/dev/null 2>&1; then fail "decide.py took a letter he never typed under the item"; fi
if $PY "$ROOT/scripts/decide.py" "$FN" --item 8 --title "Letter" --decision "red" --why "w" --said "a" >/dev/null 2>&1; then fail "decide.py took a different letter than the one he typed"; fi
if $PY "$ROOT/scripts/decide.py" "$FN" --item 8 --title "Letter" --decision "red" --why "w" --said "b" --chose "red" >/dev/null 2>&1; then fail "decide.py took a --chose that is not the letter's option"; fi
printf '# Board\n\n## Entries\n' > "$FOLDER/muster/BOARD.md"
cp "$SCRATCH/tr/manager.jsonl" "$SCRATCH/tr/mgr-card.jsonl"
printf '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"AskUserQuestion","input":{}}]}}\n' >> "$SCRATCH/tr/mgr-card.jsonl"
hook manager false "So C fits what you want, and I am recording it." | grep -q '"decision": "block"' || fail "Stop hook did not catch a manager choosing for the owner"
hook mgr-card false "So C fits what you want, and I am recording it." | grep -q . && fail "Stop hook blocked although a choice card was answered this turn"
cp "$SCRATCH/tr/manager.jsonl" "$SCRATCH/tr/mgr-letter.jsonl"
printf '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Which?\\n\\n***A.*** red\\n\\n***B.*** blue"}]}}\n{"type":"user","message":{"role":"user","content":"b"}}\n' >> "$SCRATCH/tr/mgr-letter.jsonl"
hook mgr-letter false "So B fits what you want, and I am recording it." | grep -q . && fail "Stop hook blocked although he typed a letter answer this turn (item 80)"
hook manager false "You picked B, so I am recording it." | grep -q . && fail "Stop hook blocked although the message says he picked"
hook manager false "You said you want it calm, so C fits what you want, I am recording it." | grep -q '"decision": "block"' || fail "Stop hook let through 'you said ... I am recording it'"
hook manager true "I am recording it." | grep -q . && fail "Stop hook blocked while already continuing"

step "a paused chat that resumed reads clear; one that did not still blocks; the marker file works"
printf '# Board\n\n## Entries\n### 2026-01-31 | DONE | Builder A_X_001 -> Manager | demo\nStatus: open\nPaused: yes\n' > "$FOLDER/muster/BOARD.md"
hook manager false "all done" | grep -q '"decision": "block"' || fail "paused with no later line must still block"
printf '### 2026-01-31 | DONE | Builder A_X_001 -> Manager | next job\nStatus: open\n' >> "$FOLDER/muster/BOARD.md"
hook manager false "all done" | grep -q . && fail "a later entry from the same chat did not clear the paused line (hook)"
OUT4=$(cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" Manager)
echo "$OUT4" | grep -q "relay his answer" && fail "digest still names a resumed chat paused: $OUT4"
printf '# Board\n\n## Entries\n### 2026-01-31 | NEED | Builder A_X_001 -> Manager | demo\nStatus: open\nPaused: yes\nPaused: no\n' > "$FOLDER/muster/BOARD.md"
hook manager false "all done" | grep -q '"decision": "block"' || fail "a NEED still waiting must block even when resumed"
printf '# Board\n\n## Entries\n### 2026-01-31 | READY | Builder A_X_001 -> Inspector_X_001 | demo\nStatus: done\nPaused: yes\nPaused: no\n' > "$FOLDER/muster/BOARD.md"
hook manager false "all done" | grep -q . && fail "Paused: no did not clear the paused line (hook)"
printf '# Board\n\n## Entries\n### 2026-01-31 | READY | Builder A_X_001 -> Inspector_X_001 | demo\nStatus: open\nPaused: yes\n' > "$FOLDER/muster/BOARD.md"
OUT5=$(cd "$FOLDER" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" Manager)
echo "$OUT5" | grep -q "relay his answer to Builder A_X_001" || fail "digest missed a paused entry addressed to someone else: $OUT5"
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
snap() { (cd "$CM" && find . -path ./.git/objects -prune -o -type f -print0 | sort -z | xargs -0 cksum | cksum); }
BEFORE_SNAP=$(snap)
# a dry run writes nothing at all, and says what it would read
$PY "$ROOT/cursor/setup.py" "$(native "$CM")" --name "Bob Shop" --join --computer laptop2 --other desk1 --dry-run > "$CU/dry.out" 2>&1 || { cat "$CU/dry.out"; fail "--join --dry-run failed"; }
grep -q "^DRY RUN" "$CU/dry.out" && grep -q "Would read (never write): board" "$CU/dry.out" || fail "the dry run did not say what it would read: $(cat "$CU/dry.out")"
[ ! -e "$CU/laptop2 Workspace" ] || fail "the dry run wrote the workspace"
[ "$(snap)" = "$BEFORE_SNAP" ] || fail "the dry run changed the project"
$PY "$ROOT/cursor/setup.py" "$(native "$CM")" --name "Bob Shop" --join --computer laptop2 --other desk1 --copies clone --copies-dir "$(native "$CU")/clones" > "$CU/join.out" 2>&1 || { cat "$CU/join.out"; fail "cursor/setup.py --join failed"; }
[ "$(snap)" = "$BEFORE_SNAP" ] || fail "--join changed something in the shared project (muster/, .cursor or .git)"
WS="$CU/laptop2 Workspace"
for f in CHANGES.md START-HERE.md git-as.sh tools/board_digest.py; do [ -f "$WS/$f" ] || fail "--join did not make $f in the workspace"; done
[ -e "$CU/desk1 Workspace" ] && fail "--join wrote the other computer's workspace folder"
[ -f "$WS/.cursor/rules/muster-laptop2-core.mdc" ] || fail "--join did not write this computer's Cursor rules in its workspace"
grep -q "Never override desk1" "$WS/.cursor/rules/muster-laptop2-core.mdc" || fail "the two-computer lines are missing from the rules"
grep -q "protocol page" "$WS/.cursor/rules/muster-laptop2-core.mdc" && grep -q "BUILDERS-LOG.md" "$WS/START-HERE.md" || fail "the protocol page and builders' log are not named for the second computer"
# a project with its own layout (board, rules and workspaces elsewhere), read-only
PL="$CU/pinrlike"; mkdir -p "$PL/Proj/handoff" "$PL/ws2" ; echo "# board" > "$PL/Proj/handoff/BOARD.md"; echo r1 > "$PL/Proj/CLAUDE.md"; echo r2 > "$PL/Proj/READ-FIRST.md"
PBEFORE=$(find "$PL" -type f | sort | xargs cksum | cksum)
$PY "$ROOT/cursor/setup.py" "$(native "$PL/Proj")" --name Pinr --join --computer laptop2 --other desk1 --board "$PL/Proj/handoff/BOARD.md" --rules "$PL/Proj/CLAUDE.md" --rules "$PL/Proj/READ-FIRST.md" --workspace "$PL/ws2" --other-workspace "$PL/otherws" --dry-run > "$CU/pdry.out" 2>&1 || { cat "$CU/pdry.out"; fail "--join --dry-run on another layout failed"; }
grep -q "READ-FIRST.md" "$CU/pdry.out" && grep -q "handoff.BOARD.md" "$CU/pdry.out" || fail "the other layout's board and rules were not used"
[ "$(find "$PL" -type f | sort | xargs cksum | cksum)" = "$PBEFORE" ] && [ ! -e "$PL/otherws" ] || fail "the dry run on another layout wrote something"
# the board step in the starting note reads the board the join was given, and writes nothing
grep -q -- '--board' "$WS/START-HERE.md" || fail "START-HERE does not pass --board to the board reader"
$PY "$WS/tools/board_digest.py" Builder --board "$PL/Proj/handoff/BOARD.md" > "$CU/bd.out" 2>&1 || true
grep -q "Read .*BOARD.md" "$CU/bd.out" && ! grep -q "NOT FOUND" "$CU/bd.out" || fail "the board reader did not read the given board: $(cat "$CU/bd.out")"
[ "$(find "$PL" -type f | sort | xargs cksum | cksum)" = "$PBEFORE" ] || fail "reading the given board wrote something"
[ -z "$(git -C "$CM" status --porcelain)" ] || fail "--join left files the shared project would commit: $(git -C "$CM" status --porcelain)"
sh "$WS/git-as.sh" -C "$CU/clones/builder-a-laptop2" commit -q --allow-empty -m t && [ "$(git -C "$CU/clones/builder-a-laptop2" log -1 --format=%an)" = laptop2 ] || fail "git-as.sh did not commit as laptop2"
git -C "$CU/clones/builder-a-laptop2" rev-parse --abbrev-ref HEAD | grep -q '^laptop2/' || fail "the clone is not on a laptop2/ branch"
$PY "$ROOT/cursor/setup.py" "$(native "$CU")/nothing here" --name X --join --computer laptop2 --other desk1 >/dev/null 2>&1 && fail "--join accepted a folder with no muster/"
grep -q "^## 9c. Two founder computers" "$ROOT/templates/CLAUDE.md" || fail "the two-computer rules are missing from the core rules"

step "an accented project name (D-011): folders, crew names, files, the board and the hooks read it back"
AC="Pâtisserie"; CP="$ROOT/scripts/crew-plan.py"
ACD="$SCRATCH/accent"; mkdir -p "$ACD"
$PY "$ROOT/cursor/setup.py" "$(native "$ACD")/$AC" --name "$AC" --vision "a café: crème brûlée" > "$ACD/setup.out" 2>&1 || { cat "$ACD/setup.out"; fail "setup with an accented project name failed"; }
AM="$ACD/$AC"
[ -d "$AM/muster" ] && [ -f "$AM/muster/start-notes/Builder A_${AC}_001.md" ] || fail "the accented project's crew folder or starting note is missing"
grep -q "$AC" "$AM/muster/start-notes/Builder A_${AC}_001.md" || fail "the starting note does not hold the accented name"
[ -f "$ACD/${AC}_copies/builder-a-001/.cursor/rules/muster-builder.mdc" ] || fail "the accented project's worker copy is missing"
[ -z "$(git -C "$AM" status --porcelain)" ] || fail "the accented project left files in its history: $(git -C "$AM" status --porcelain)"
[ "$($PY "$CP" copy-name "Builder A_${AC}_002")" = "builder-a-002" ] || fail "copy-name wrong for an accented project"
$PY "$CP" inspectors 4 --project "$AC" | grep -q "Inspector B_${AC}_001 <- Builder D" || fail "crew-plan lost the accented name"
printf '# Board\n\n## Entries\n### 2026-01-31 | NEED | Builder A_%s_001 -> Manager_%s_001 | Crème brûlée\nStatus: open\nWhat: the café menu\n' "$AC" "$AC" > "$AM/muster/BOARD.md"
$PY "$AM/muster/tools/board_digest.py" "Manager_${AC}_001" "$(native "$AM")" > "$ACD/digest.out" 2>&1 || { cat "$ACD/digest.out"; fail "the board digest failed on accented names"; }
grep -q "Crème brûlée" "$ACD/digest.out" && grep -q "1 entries concern" "$ACD/digest.out" || fail "the board did not read back the accented entry: $(cat "$ACD/digest.out")"
# the coded rules: the accented manager is the manager, the accented builder is not, and an accented report passes
jl() { $PY -c 'import json,sys;print(json.dumps({"type":"user","message":{"content":sys.argv[1]}}))' "$1"; }   # a one-message transcript
jl "You are Manager_${AC}_001" > "$ACD/mgr.txt"; jl "You are Builder A_${AC}_001, agents/builder.md. Report to Manager_${AC}_001." > "$ACD/bld.txt"
ac_stop() { printf '{"hook_event_name":"Stop","cwd":"%s","last_assistant_message":"All done, nice.","transcript_path":"%s"}' "$(native "$ACD")" "$(native "$ACD")/$1" | $PY "$ROOT/hooks/rules-check.py"; }
ac_stop mgr.txt | grep -q '"decision": "block"' || fail "the accented manager was not held to the manager's reply rule"
ac_stop bld.txt | grep -q '"decision": "block"' || fail "the accented builder's non-card reply was not caught"
REP='{\"v\":1,\"kind\":\"PASS\",\"id\":\"inspector-creme-brulee-1\",\"job\":\"creme-brulee\",\"from\":\"inspector\",\"to\":\"builder-a\",\"sha\":\"abcdef1\",\"need\":\"none\"}'
printf '{"hook_event_name":"PreToolUse","cwd":"%s","tool_name":"SendMessage","tool_input":{"to":"x","message":"%s"},"transcript_path":"%s"}' "$(native "$ACD")" "$REP" "$(native "$ACD")/bld.txt" | $PY "$ROOT/hooks/rules-check.py" | grep -q deny && fail "an accented project's correct record was refused"
cp "$ACD/mgr.txt" "$ACD/mgr2.txt"
(cd "$AM" && printf '{"cwd":"%s","last_assistant_message":"Fine.","transcript_path":"%s"}' "$(native "$AM")" "$(native "$ACD")/mgr2.txt" | $PY "$ROOT/hooks/board-stop.py") | grep -q "Builder A_P.*tisserie_001 (NEED)" || fail "board-stop did not recognise the accented manager"

step "a chat started on an older Muster picks up the newest installed check with no restart (scripts/find-binary.sh)"
FB="$SCRATCH/cache/muster-kit/muster"; mkdir -p "$FB/0.3.40/scripts" "$FB/0.3.40/.claude-plugin" "$FB/0.3.99/.claude-plugin"
cp "$ROOT/scripts/find-binary.sh" "$FB/0.3.40/scripts/"; : > "$FB/0.3.40/.claude-plugin/plugin.json"; : > "$FB/0.3.99/.claude-plugin/plugin.json"
case "$(uname -s)" in Darwin) FOS=macos;; Linux) FOS=linux;; *) FOS=windows;; esac
case "$(uname -m)" in arm64|aarch64) FARCH=arm64;; *) FARCH=x86_64;; esac; [ "$FOS" = windows ] && FARCH=x86_64
FEXE=muster-checks; [ "$FOS" = windows ] && FEXE=muster-checks.exe
[ -z "$(sh "$FB/0.3.40/scripts/find-binary.sh" "$FB/0.3.40" 2>/dev/null)" ] || fail "found a check where none is installed"
mkdir -p "$FB/0.3.99/bin/$FOS-$FARCH"; : > "$FB/0.3.99/bin/$FOS-$FARCH/$FEXE"
[ "$(sh "$FB/0.3.40/scripts/find-binary.sh" "$FB/0.3.40")" = "$FB/0.3.99/bin/$FOS-$FARCH/$FEXE" ] || fail "an older version did not pick up the newer check: $(sh "$FB/0.3.40/scripts/find-binary.sh" "$FB/0.3.40")"
mkdir -p "$FB/0.3.100/.claude-plugin" "$FB/0.3.100/bin/$FOS-$FARCH"; : > "$FB/0.3.100/.claude-plugin/plugin.json"; : > "$FB/0.3.100/bin/$FOS-$FARCH/$FEXE"
[ "$(sh "$FB/0.3.40/scripts/find-binary.sh" "$FB/0.3.40")" = "$FB/0.3.100/bin/$FOS-$FARCH/$FEXE" ] || fail "0.3.100 was not seen as newer than 0.3.99"
echo "an older chat now runs the 0.3.100 check"

step "the hook wrapper runs the ready-made program for this system (hooks/rules-check.sh -> bin/)"
WT="$SCRATCH/wrapper"; mkdir -p "$WT"
$PY -c 'import json,sys;print(json.dumps({"type":"user","message":{"content":"You are Builder A_Shop_001, agents/builder.md"}}))' > "$WT/t.jsonl"
WRAP_OUT=$(cd "$FOLDER" && printf '{"hook_event_name":"Stop","cwd":"%s","last_assistant_message":"Done.","transcript_path":"%s"}' "$(native "$FOLDER")" "$(native "$WT")/t.jsonl" | sh "$ROOT/hooks/rules-check.sh")
echo "$WRAP_OUT" | grep -q '"decision": "block"' || fail "the wrapper did not enforce the card rule: $WRAP_OUT"
BIN_USED=$(sh "$ROOT/scripts/find-binary.sh" "$ROOT" 2>/dev/null || true)
echo "program used: ${BIN_USED:-none for this system (the Python copy ran)}"
if [ -n "$BIN_USED" ]; then
  REC_OUT=$(cd "$FOLDER" && printf '{"hook_event_name":"PreToolUse","cwd":"%s","tool_name":"SendMessage","tool_input":{"to":"x","message":"hello there, please look"},"transcript_path":"%s"}' "$(native "$FOLDER")" "$(native "$WT")/t.jsonl" | sh "$ROOT/hooks/rules-check.sh")
  echo "$REC_OUT" | grep -q 'data record' || fail "the ready-made program let a sentence between chats through: $REC_OUT"
fi

step "scaling: inspector count, copy names, small or big, and the board archiving itself"
CP="$ROOT/scripts/crew-plan.py"
$PY "$CP" inspectors 3 --project Shop | grep -q "inspectors=1" || fail "3 builders must need 1 inspector"
$PY "$CP" inspectors 4 --project Shop | grep -q "inspectors=2" || fail "4 builders must need 2 inspectors"
$PY "$CP" inspectors 4 --project Shop | grep -q "Inspector B_Shop_001 <- Builder D" || fail "builder D must go to the second inspector"
$PY "$CP" inspectors 7 --project Shop | grep -q "inspectors=3" || fail "7 builders must need 3 inspectors"
[ "$($PY "$CP" copy-name "Builder A_Shop_002")" = "builder-a-002" ] || fail "copy-name wrong"
$PY "$CP" check-copy "Engine_PINR_003" ".claude/worktrees/build-inspector-003" >/dev/null 2>&1 && fail "a renewed chat was allowed into another role's copy"
$PY "$CP" check-copy "Builder A_Shop_002" ".claude/worktrees/builder-a-002" | grep -q "^OK" || fail "a correctly named copy was refused"
SZ="$SCRATCH/size"; mkdir -p "$SZ" && (cd "$SZ" && git init -q -b main && git config user.name t && git config user.email t@localhost && echo a > a.txt && git add -A && git commit -q -m one && echo b >> a.txt && git commit -q -am two && mkdir engine && echo x > engine/e.py && git add -A && git commit -q -m three)
$PY "$CP" size HEAD~2 HEAD~1 --repo "$(native "$SZ")" | grep -q "^SMALL" || fail "a one-line text change was not SMALL"
$PY "$CP" size HEAD~1 HEAD --repo "$(native "$SZ")" | grep -q "^BIG" || fail "an engine change was not BIG"
BA="$SCRATCH/archive"; mkdir -p "$BA/muster"
printf '# Board\n\nWaiting on: nobody\n\n## Entries\n### 2020-01-01 | DONE | A -> Manager | old done\nStatus: done\n\n### 2020-01-01 | NEED | A -> Manager | old open\nStatus: open\n\n### 2999-01-01 | DONE | A -> Manager | future done\nStatus: done\n' > "$BA/muster/BOARD.md"
(cd "$BA" && $PY "$ROOT/skills/board-digest/scripts/board_digest.py" Manager --write-waiting >/dev/null) || fail "digest with archiving failed"
grep -q "old done" "$BA/muster/BOARD-ARCHIVE.md" || fail "a finished old entry was not archived"
grep -q "old done" "$BA/muster/BOARD.md" && fail "the archived entry is still on the board"
grep -q "old open" "$BA/muster/BOARD.md" || fail "an OPEN entry was moved"
grep -q "future done" "$BA/muster/BOARD.md" || fail "an entry that is not a day old was moved"
printf '# Board\n- 2020-01-01 Builder A DONE [done] one thing\n- 2020-01-01 Builder B NEED [open] another\n- 2999-01-01 Builder A DONE [done] new\n' > "$BA/muster/BOARD.md"; : > "$BA/muster/BOARD-ARCHIVE.md"
(cd "$BA" && $PY "$ROOT/skills/board-digest/scripts/board_archive.py" --one-line >/dev/null) || fail "one-line archiving failed"
grep -q "one thing" "$BA/muster/BOARD-ARCHIVE.md" && ! grep -q "another" "$BA/muster/BOARD-ARCHIVE.md" && ! grep -q "new" "$BA/muster/BOARD-ARCHIVE.md" || fail "one-line archiving moved the wrong lines"

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
# ship-installs-plugins: a stand-in claude, so no test ever updates a real install; it records what it was asked and fails for muster-look
cat > "$SCRATCH/claude-stub.py" <<'STUB'
import os, sys
a = sys.argv[1:]
if a[:1] == ["--version"]: print("0.0-test")
elif a[:2] == ["plugin", "update"]:
    open(os.environ["STUB_LOG"], "a").write(a[2] + "\n")
    if a[2].startswith("muster-look"): print("not installed"); sys.exit(1)
    print("updated " + a[2])
elif a[:2] == ["plugin", "list"]: print("muster@muster-kit\n  Version: test")
STUB
export STUB_LOG="$SCRATCH/stub.log"; : > "$STUB_LOG"; export MUSTER_CLAUDE="$PY $(cygpath -m "$SCRATCH/claude-stub.py" 2>/dev/null || echo "$SCRATCH/claude-stub.py")"
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
grep -q "muster@muster-kit" "$STUB_LOG" && grep -q "muster-look@muster-kit" "$STUB_LOG" || fail "ship did not try to update both plugins"
$PY - "$STUB_LOG" <<'PYC' || fail "the plugin update did not run once per plugin after the first ship"
import sys; l = open(sys.argv[1]).read().split(); sys.exit(0 if l[:2] == ["muster@muster-kit", "muster-look@muster-kit"] else 1)
PYC
git -C "$SH/remote.git" show main:.claude-plugin/plugin.json | grep -q '"1.2.4"' || fail "main on the remote lacks 1.2.4"
git -C "$SH/remote.git" show main:.claude-plugin/releases/1.2.4.json | grep -q "demo change" || fail "no release file on the remote"
git -C "$SH/remote.git" show main:CHANGELOG.md | grep -q "^## 1.2.4" || fail "no changelog entry on the remote"
git -C "$SH/remote.git" for-each-ref --format='%(refname)' | grep -q "ship/" && fail "the temporary ship branch was left behind"
# with a crew board in the main folder, shipping needs an inspector PASS naming the exact saved version
mkdir -p muster; printf '# Board\n' > muster/BOARD.md
if bash scripts/ship.sh "no pass yet" --dry-run >"$SH/nopass.out" 2>&1; then fail "ship went ahead with no PASS on the board"; fi
grep -q "no inspector PASS on the board" "$SH/nopass.out" || fail "ship did not say the PASS was missing: $(cat "$SH/nopass.out")"
echo pass > pass.txt; git add pass.txt; git commit -q -m "a piece to pass"
printf '### 2026-11-08 | FAIL | Inspector -> Builder | demo\nWhat: stacked on the passed %s\n' "$(git rev-parse --short=7 HEAD)" >> muster/BOARD.md
if bash scripts/ship.sh "fail is not pass" --dry-run >"$SH/failpass.out" 2>&1; then fail "ship took the word 'passed' in a FAIL entry for a PASS"; fi
printf '### 2026-11-08 | PASS | Inspector -> Manager | demo\nWhat: PASS for %s\n' "$(git rev-parse --short=7 HEAD)" >> muster/BOARD.md
bash scripts/ship.sh "pass is there" --dry-run >"$SH/pass.out" 2>&1 || { cat "$SH/pass.out"; fail "ship refused a branch whose PASS is on the board"; }
rm -rf muster
git checkout -q -b builder/demo2 origin/main; echo two > two.txt
printf '{\n  "name": "muster",\n  "version": "1.2.5"\n}\n' > .claude-plugin/plugin.json
printf '{\n  "name": "muster-kit",\n  "plugins": [\n    {\n      "name": "muster",\n      "version": "1.2.5"\n    }\n  ]\n}\n' > .claude-plugin/marketplace.json
printf '{"version":"1.2.5","note":"my own note"}\n' > .claude-plugin/releases/1.2.5.json
$PY - <<'PY'
c = open("CHANGELOG.md").read(); i = c.index("\n## ") + 1
open("CHANGELOG.md", "w").write(c[:i] + "## 1.2.5\nAffects: Builder.\nmy own note\n\n" + c[i:])
PY
git add -A; git commit -q -m "change two"
mkdir -p muster; printf '# Builders log\n' > muster/BUILDERS-LOG.md
bash scripts/ship.sh "a different note" --no-wait > "$SH/keep.out" 2>&1; grep -q "SHIPPED 1.2.5" "$SH/keep.out" || { cat "$SH/keep.out"; fail "ship refused a branch that already has its version"; }
grep -q "| 1.2.5 | .*| a different note" muster/BUILDERS-LOG.md || fail "ship did not add its line to the builders' log: $(cat muster/BUILDERS-LOG.md)"
# item 90: after a ship the main folder (the checkout the branch's worktree belongs to) moves to the shipped version, fast-forward only
MF="$SH/mainfolder"; git clone -q -b main "$SH/remote.git" "$MF"
git -C "$MF" config user.name t; git -C "$MF" config user.email t@localhost
git -C "$MF" worktree add -q -b builder/live "$SH/wt-live" origin/main
( cd "$SH/wt-live"; mkdir -p scripts; cp "$ROOT/scripts/ship.sh" "$ROOT/scripts/find-python.sh" "$ROOT/scripts/version-check.sh" "$ROOT/scripts/scan-leaks.sh" scripts/; echo more > more.txt; git add -A; git commit -q -m "more"
  bash scripts/ship.sh "live folder" --roles Builder --no-wait > "$SH/mf.out" 2>&1; grep -q "main folder .* is now at 1.2.6" "$SH/mf.out" || { cat "$SH/mf.out"; fail "ship did not move the main folder"; } )
git -C "$MF" show HEAD:.claude-plugin/plugin.json | grep -q '"1.2.6"' || fail "the main folder is not at the shipped version"
# a main folder on another branch, or with work of its own, is said plainly and left alone
git -C "$MF" checkout -q -b elsewhere
( cd "$SH/wt-live"; git fetch -q origin; git reset -q --hard origin/main; echo again > again.txt; git add -A; git commit -q -m "again"
  bash scripts/ship.sh "second live" --roles Builder --no-wait > "$SH/mf2.out" 2>&1; grep -q "MAIN FOLDER NOT UPDATED: .* is on 'elsewhere'" "$SH/mf2.out" || { cat "$SH/mf2.out"; fail "ship did not say the main folder was on another branch"; }; grep -q "SHIPPED 1.2.7" "$SH/mf2.out" || fail "the ship itself was affected" )
[ "$(git -C "$MF" rev-parse --abbrev-ref HEAD)" = elsewhere ] || fail "ship moved a main folder that was on another branch"
git -C "$MF" checkout -q main; echo "mine" >> "$MF/.claude-plugin/plugin.json"
( cd "$SH/wt-live"; git fetch -q origin; git reset -q --hard origin/main; echo third > third.txt; git add -A; git commit -q -m "third"
  bash scripts/ship.sh "third live" --roles Builder --no-wait > "$SH/mf3.out" 2>&1; grep -q "MAIN FOLDER NOT UPDATED: .*fast-forwarded" "$SH/mf3.out" || { cat "$SH/mf3.out"; fail "ship did not say the main folder could not be fast-forwarded"; }; grep -q "SHIPPED 1.2.8" "$SH/mf3.out" || fail "the ship itself was affected" )
grep -q "^mine$" "$MF/.claude-plugin/plugin.json" || fail "ship overwrote work in the main folder"
# item 122, local first: GitHub refusing every push never holds back the owner's own folder; the next ship carries what is not pushed
git -C "$MF" checkout -q -- .claude-plugin/plugin.json; git -C "$MF" fetch -q origin; git -C "$MF" merge -q --ff-only origin/main
printf '#!/bin/sh\necho "GitHub is down" >&2\nexit 1\n' > "$SH/remote.git/hooks/pre-receive"; chmod +x "$SH/remote.git/hooks/pre-receive"
( cd "$SH/wt-live"; git fetch -q origin; git reset -q --hard origin/main; echo fourth > fourth.txt; git add -A; git commit -q -m "fourth"
  bash scripts/ship.sh "local first" --roles Builder --no-wait > "$SH/lf.out" 2>&1 || { cat "$SH/lf.out"; fail "ship failed because GitHub refused the push"; }
  grep -q "main folder .* is now at 1.2.9" "$SH/lf.out" || { cat "$SH/lf.out"; fail "the main folder did not get the release while GitHub refused"; }
  grep -q "PUBLISHING PENDING" "$SH/lf.out" || fail "ship did not say publishing is pending"
  grep -q "SHIPPED 1.2.9" "$SH/lf.out" || fail "ship did not finish locally" )
git -C "$MF" show HEAD:.claude-plugin/plugin.json | grep -q '"1.2.9"' || fail "the main folder is not at the locally shipped version"
git -C "$SH/remote.git" show main:.claude-plugin/plugin.json | grep -q '"1.2.8"' || fail "GitHub moved although it refused the push"
rm "$SH/remote.git/hooks/pre-receive"
( cd "$SH/wt-live"; git reset -q --hard main; echo fifth > fifth.txt; git add -A; git commit -q -m "fifth"
  bash scripts/ship.sh "carries it" --roles Builder --no-wait > "$SH/lf2.out" 2>&1 || { cat "$SH/lf2.out"; fail "the next ship failed"; }
  grep -q "SHIPPED 1.2.10" "$SH/lf2.out" || { cat "$SH/lf2.out"; fail "the next ship was not 1.2.10"; } )
git -C "$SH/remote.git" show main:.claude-plugin/releases/1.2.9.json >/dev/null 2>&1 || fail "the next ship did not carry the release GitHub had not got"
git -C "$SH/remote.git" show main:.claude-plugin/plugin.json | grep -q '"1.2.10"' || fail "GitHub did not get the next release"
# the owner's folder moved ahead of GitHub by hand (no landed marker): a branch built on it still ships, carrying those versions
printf '#!/bin/sh\nexit 1\n' > "$SH/remote.git/hooks/pre-receive"; chmod +x "$SH/remote.git/hooks/pre-receive"
( cd "$SH/wt-live"; git fetch -q origin; git reset -q --hard main; echo sixth > sixth.txt; git add -A; git commit -q -m "sixth"
  bash scripts/ship.sh "ahead" --roles Builder --no-wait > "$SH/ah.out" 2>&1; grep -q "SHIPPED 1.2.11" "$SH/ah.out" || { cat "$SH/ah.out"; fail "the ahead ship did not land locally"; } )
rm "$SH/remote.git/hooks/pre-receive"; git -C "$SH/wt-live" update-ref -d refs/muster/landed
( cd "$SH/wt-live"; git reset -q --hard main; echo seventh > seventh.txt; git add -A; git commit -q -m "seventh"
  bash scripts/ship.sh "built on the folder" --roles Builder --no-wait > "$SH/ah2.out" 2>&1 || { cat "$SH/ah2.out"; fail "a branch built on the owner's folder was refused"; }
  grep -q "SHIPPED 1.2.12" "$SH/ah2.out" || { cat "$SH/ah2.out"; fail "the version gate refused versions that run ahead of GitHub"; } )
git -C "$SH/remote.git" show main:.claude-plugin/releases/1.2.11.json >/dev/null 2>&1 || fail "the release GitHub had not got was not carried"
# publish only: the branch already IS the owner's folder (landed locally, GitHub refused): the next run sends it, no new version
printf '#!/bin/sh\nexit 1\n' > "$SH/remote.git/hooks/pre-receive"; chmod +x "$SH/remote.git/hooks/pre-receive"
( cd "$SH/wt-live"; git fetch -q origin; git reset -q --hard main; echo eighth > eighth.txt; git add -A; git commit -q -m "eighth"
  bash scripts/ship.sh "held back" --roles Builder --no-wait > "$SH/po1.out" 2>&1; grep -q "SHIPPED 1.2.13" "$SH/po1.out" || { cat "$SH/po1.out"; fail "the held-back ship did not land locally"; } )
rm "$SH/remote.git/hooks/pre-receive"
[ "$(git -C "$SH/wt-live" rev-parse HEAD)" = "$(git -C "$MF" rev-parse main)" ] || fail "the branch is not the owner's folder in the publish-only case"
( cd "$SH/wt-live"; bash scripts/ship.sh "held back" --roles Builder --no-wait > "$SH/po2.out" 2>&1 || { cat "$SH/po2.out"; fail "publish only stopped"; }
  grep -q "publish only" "$SH/po2.out" && grep -q "SHIPPED 1.2.13" "$SH/po2.out" || { cat "$SH/po2.out"; fail "publish only did not say so or changed the version"; } )
git -C "$SH/remote.git" show main:.claude-plugin/plugin.json | grep -q '"1.2.13"' || fail "publish only did not reach GitHub"
# publish only agrees with version-check: files changed after a version GitHub already holds need a version commit, not a silent stop later
( cd "$SH/wt-live"; git fetch -q origin; prev=$(git rev-parse HEAD); git reset -q --hard main; echo ninth > ninth.txt; git add -A; git commit -q -m "ninth, no version"
  git -C "$MF" merge -q --ff-only "$(git rev-parse HEAD)"
  if bash scripts/ship.sh "unversioned" --roles Builder --no-wait > "$SH/po3.out" 2>&1; then cat "$SH/po3.out"; fail "publish only shipped changes after a version GitHub already holds"; fi
  grep -q "a version commit is needed" "$SH/po3.out" || { cat "$SH/po3.out"; fail "publish only did not say a version commit is needed"; }
  git -C "$MF" reset -q --hard "$prev"; git reset -q --hard "$prev" )
rm -rf muster
[ "$(grep -c '^## 1.2.5' CHANGELOG.md)" = 1 ] || fail "the changelog entry was doubled"
grep -q "my own note" .claude-plugin/releases/1.2.5.json || fail "the branch's own release file was overwritten"
git checkout -q origin/main 2>/dev/null; git checkout -q -b builder/other origin/main; echo o > other.txt; git add -A; git commit -q -m "other piece"
git checkout -q -b builder/batch origin/main; echo b > batch.txt; git add -A; git commit -q -m "batch piece"
bash scripts/ship.sh "batch" --with builder/other --dry-run > "$SH/batch.out" 2>&1 || { cat "$SH/batch.out"; fail "batch dry run failed"; }
grep -q "batch: merged builder/other" "$SH/batch.out" && grep -q "other.txt" "$SH/batch.out" && grep -q "batch.txt" "$SH/batch.out" || fail "batch did not carry both pieces: $(cat "$SH/batch.out")"
if bash scripts/ship.sh "batch" --with builder/nope --dry-run >/dev/null 2>&1; then fail "ship accepted a --with branch that does not exist"; fi
cd "$FOLDER"
step "ci-retry.py reruns a free test that failed only because a job never got a machine, never a real failure (item 121)"
CR="$SCRATCH/ciretry"; mkdir -p "$CR/bin"
cat > "$CR/gh.py" <<'GH'
# a stand-in for gh: "run list" and "run view" print the canned JSON in CR_STATE; "run rerun" is recorded
import os, sys
st = os.environ["CR_STATE"]
k = " ".join(sys.argv[1:3])
if k == "run list": sys.stdout.write(open(st + "/list.json").read())
elif k == "run view": sys.stdout.write(open(st + "/view.json").read())
elif k == "run rerun": open(st + "/reruns.log", "a").write(" ".join(sys.argv[1:]) + "\n")
GH
CR=$(cygpath -m "$CR" 2>/dev/null || echo "$CR")
export CR_STATE="$CR" CI_RETRY_GH="$CR/gh.py"
cr() { $PY "$ROOT/scripts/ci-retry.py" "$@"; }
printf '[{"databaseId":77,"headSha":"abc","status":"completed","conclusion":"failure"}]' > "$CR/list.json"
printf '{"jobs":[{"name":"rust (macos)","conclusion":"cancelled","steps":[]},{"name":"checks","conclusion":"success","steps":[{"conclusion":"success"}]}]}' > "$CR/view.json"
cr b abc >"$CR/o1" 2>&1 || fail "a job that never got a machine was not rerun: $(cat "$CR/o1")"
grep -q "RERAN 77" "$CR/o1" || fail "ci-retry did not say it reran: $(cat "$CR/o1")"
grep -q "run rerun 77 --failed" "$CR/reruns.log" || fail "gh run rerun --failed was not called"
printf '{"jobs":[{"name":"shipped-copies","conclusion":"failure","steps":[{"conclusion":"success"},{"conclusion":"failure"}]},{"name":"rust (macos)","conclusion":"cancelled","steps":[]}]}' > "$CR/view.json"
rm -f "$CR/reruns.log"
if cr b abc >"$CR/o2" 2>&1; then fail "a real test failure was rerun"; fi
grep -q "a real failure" "$CR/o2" || fail "ci-retry did not call it a real failure: $(cat "$CR/o2")"
[ ! -f "$CR/reruns.log" ] || fail "gh run rerun ran for a real failure"
printf '{"jobs":[{"name":"rust (macos)","conclusion":"cancelled","steps":[]}]}' > "$CR/view.json"
if cr b abc --done 3 >"$CR/o3" 2>&1; then fail "ci-retry kept rerunning past the limit"; fi
if cr b zzz >"$CR/o4" 2>&1; then fail "ci-retry reran a run of another version"; fi
printf '[{"databaseId":77,"headSha":"abc","status":"completed","conclusion":"success"}]' > "$CR/list.json"
if cr b abc >"$CR/o5" 2>&1; then fail "ci-retry reran a run that passed"; fi
grep -q 'ci-retry.py' "$ROOT/scripts/ship.sh" || fail "ship.sh does not use ci-retry.py"
unset CR_STATE CI_RETRY_GH

step "validate-strict.py accepts only the one known Backdrop warning (strict-backdrop)"
VS="$SCRATCH/vs"; mkdir -p "$VS"
printf 'Validating hooks: x\n\n\xe2\x9a\xa0 Found 1 warning:\n\n  \xe2\x9d\xaf modules.../look/register.tsx: on ui.render{component=Backdrop}: no component is named Backdrop, so it never runs\n\n  \xe2\x9d\xaf info line\n\n\xe2\x9c\x98 Validation failed (--strict treats warnings as errors)\n' > "$VS/ok.txt"
$PY "$ROOT/scripts/validate-strict.py" --from "$VS/ok.txt" --rc 1 >/dev/null 2>&1 || fail "the known Backdrop warning alone was not accepted"
sed 's/component=Backdrop}: no component is named Backdrop/component=Pane}: no component is named Pane/' "$VS/ok.txt" > "$VS/other.txt"
if $PY "$ROOT/scripts/validate-strict.py" --from "$VS/other.txt" --rc 1 >/dev/null 2>&1; then fail "another warning was accepted"; fi
printf 'x\n\xe2\x9a\xa0 Found 2 warnings:\n\n  \xe2\x9d\xaf a: on ui.render{component=Backdrop}: no component is named Backdrop, so it never runs\n  \xe2\x9d\xaf b: something else\n\n\xe2\x9c\x98 Validation failed\n' > "$VS/two.txt"
if $PY "$ROOT/scripts/validate-strict.py" --from "$VS/two.txt" --rc 1 >/dev/null 2>&1; then fail "Backdrop plus another warning was accepted"; fi
printf '\xe2\x9c\x98 Found 1 error:\n  \xe2\x9d\xaf bad\n\xe2\x9c\x98 Validation failed\n' > "$VS/err.txt"
if $PY "$ROOT/scripts/validate-strict.py" --from "$VS/err.txt" --rc 1 >/dev/null 2>&1; then fail "an error was accepted"; fi
$PY "$ROOT/scripts/validate-strict.py" --from "$VS/err.txt" --rc 0 >/dev/null 2>&1 || fail "a passing validator was refused"
grep -q 'validate-strict.py' "$ROOT/.github/workflows/setup-test.yml" || fail "CI does not use validate-strict.py"
grep -q 'validate-strict.py' "$ROOT/scripts/ship.sh" || fail "ship.sh does not use validate-strict.py"

step "a second plugin (a mod) whose files changed but whose version did not: version-check refuses, ship.sh raises it (item 118)"
MV="$SCRATCH/modver"; mkdir -p "$MV/remote.git" "$MV/work"
git init -q --bare "$MV/remote.git"
cd "$MV/work"; git init -q -b main; git remote add origin "$MV/remote.git"
mkdir -p .claude-plugin/releases scripts mods/look/.claude-plugin
cp "$ROOT/scripts/ship.sh" "$ROOT/scripts/find-python.sh" "$ROOT/scripts/version-check.sh" "$ROOT/scripts/scan-leaks.sh" scripts/
printf '{\n  "name": "muster",\n  "version": "1.2.3"\n}\n' > .claude-plugin/plugin.json
printf '{\n  "name": "look",\n  "version": "0.5.0"\n}\n' > mods/look/.claude-plugin/plugin.json
printf '{\n  "name": "muster-kit",\n  "plugins": [\n    {\n      "name": "muster",\n      "version": "1.2.3",\n      "source": "./"\n    },\n    {\n      "name": "look",\n      "version": "0.5.0",\n      "source": "./mods/look"\n    }\n  ]\n}\n' > .claude-plugin/marketplace.json
printf '# Changelog\n\nEach version names who is affected.\n\n## 1.2.3\nold\n' > CHANGELOG.md
echo one > mods/look/a.txt
git add -A; git -c user.name=t -c user.email=t@localhost commit -q -m base; git push -q origin main
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@localhost GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@localhost
git checkout -q -b builder/mod; echo two > mods/look/a.txt; git add -A; git commit -q -m "mod change"
# Muster's own version raised by hand, the mod's forgotten
$PY - <<'PY'
import re
for f in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
    t = open(f).read(); open(f, "w").write(t.replace('"1.2.3"', '"1.2.4"', 1))
PY
git add -A; git commit -q -m "bump muster only"
if bash scripts/version-check.sh origin/main >"$MV/vc.out" 2>&1; then fail "version-check let a changed mod keep its old version"; fi
grep -q "look changed" "$MV/vc.out" || fail "version-check did not name the mod: $(cat "$MV/vc.out")"
git reset -q --hard HEAD~1
bash scripts/ship.sh "mod change" --roles Builder --no-wait | tail -2 | tee "$MV/real.out"
grep -q "SHIPPED 1.2.4" "$MV/real.out" || fail "ship did not finish: $(cat "$MV/real.out")"
git -C "$MV/remote.git" show main:mods/look/.claude-plugin/plugin.json | grep -q '"0.5.1"' || fail "the mod's own version was not raised on the remote"
git -C "$MV/remote.git" show main:.claude-plugin/marketplace.json | grep -q '"0.5.1"' || fail "the marketplace entry for the mod was not raised"
git -C "$MV/remote.git" show main:.claude-plugin/marketplace.json | grep -q '"1.2.4"' || fail "Muster's own entry was not raised"
git fetch -q origin; git checkout -q -b builder/other origin/main; echo x > unrelated.txt; git add -A; git commit -q -m "no mod change"
bash scripts/ship.sh "no mod change" --roles Builder --no-wait | tail -1 | grep -q "SHIPPED 1.2.5" || fail "ship did not finish a change that leaves the mod alone"
git -C "$MV/remote.git" show main:mods/look/.claude-plugin/plugin.json | grep -q '"0.5.1"' || fail "an unchanged mod's version moved"
cd "$FOLDER"

step "the after-compaction hook speaks only in a crew chat, never in the owner's own chat"
mkdir -p "$SCRATCH/tr" "$SCRATCH/plain"
printf '{"type":"user","message":{"role":"user","content":"First: read the plugin folder/agents/builder.md. You are Builder A_X_001."}}\n' > "$SCRATCH/tr/builder.jsonl"
printf '{"type":"user","message":{"role":"user","content":"First: read the plugin folder/agents/manager.md. You are Manager_X_001."}}\n' > "$SCRATCH/tr/manager.jsonl"
printf '{"type":"user","message":{"role":"user","content":"please fix the header art on my page"}}\n' > "$SCRATCH/tr/owner.jsonl"
renew() { (cd "$2" && printf '{"transcript_path":"%s"}' "$(native "$SCRATCH")/tr/$1.jsonl" | sh "$ROOT/hooks/renew-after-summary.sh"); }
printf '{"type":"user","message":{"role":"user","content":"Your five-line starting note. Job: build. Not yours: ask Manager_Shop_001 when unsure. First: read /p/agents/builder.md. Manager_Shop_001 gives every order."}}\n' > "$SCRATCH/tr/worker2.jsonl"
printf '{"type":"user","message":{"role":"user","content":"You are Inspector_Shop_001. Manager_Shop_001 gives every order. First: read /p/agents/inspector.md"}}\n' > "$SCRATCH/tr/inspector.jsonl"
printf '{"type":"user","message":{"role":"user","content":"You are Builder A_Shop_001. Ask Manager_Shop_001 when unsure."}}\n' > "$SCRATCH/tr/worker3.jsonl"
renew worker2 "$FOLDER" | grep -q "compacted in place" || fail "a worker whose note names the manager and a builder role file got the manager wording"
renew inspector "$FOLDER" | grep -q "compacted in place" || fail "an inspector whose note names the manager got the manager wording"
renew worker3 "$FOLDER" | grep -q "compacted in place" || fail "a worker with no role file whose note names the manager got the manager wording"
renew builder "$SCRATCH/plain" | grep -q . && fail "renewal hook spoke outside a crew project"
renew owner "$FOLDER" | grep -q . && fail "renewal hook spoke in the owner's own chat in the main folder"
renew builder "$FOLDER" | grep -q "compacted in place" || fail "renewal hook was silent for a worker"
mkdir -p "$FOLDER/.claude/worktrees/w1"
renew builder "$FOLDER/.claude/worktrees/w1" | grep -q "compacted in place" || fail "renewal hook was silent in a worker copy"
renew builder "$FOLDER" | grep -q "how to talk to the owner" || fail "the talking block did not come back after a summary"
renew owner "$FOLDER" | grep -q "how to talk to the owner" && fail "the talking block was added to the owner's own chat"
renew manager "$FOLDER" | grep -q "compacted in place" || fail "renewal hook did not give the manager its own wording"
renew manager "$FOLDER" | grep -q "DONE: renewal" && fail "a compacted chat was told to renew"

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

step "rules as code: hooks/rules-check.py blocks what the rules forbid and stays silent on the rest"
$PY "$ROOT/scripts/rules-check-selftest.py" > "$SCRATCH/rules.out" || fail "rules-check self-test missed a case: $(grep MISS "$SCRATCH/rules.out")"
tail -1 "$SCRATCH/rules.out"
step "idle crew: scripts/idle-check.py refuses a silent stop while an idle chat has an open item"
$PY "$ROOT/scripts/idle-check-selftest.py" > "$SCRATCH/idle.out" || fail "idle-check self-test missed a case: $(grep FAIL "$SCRATCH/idle.out")"
tail -1 "$SCRATCH/idle.out"
step "worker queue: scripts/worker-queue-check.py refuses an idle stop while open work is addressed to the worker"
$PY "$ROOT/scripts/worker-queue-check-selftest.py" > "$SCRATCH/wq.out" || fail "worker-queue self-test missed a case: $(grep FAIL "$SCRATCH/wq.out")"
tail -1 "$SCRATCH/wq.out"
step "scripts/check-edition.py flags a board entry a hook would have stopped"
CE="$SCRATCH/ce"; mkdir -p "$CE/muster"
printf '### 2026-11-08 | READY | Builder -> Inspector | demo\nStatus: open\nWhat: a\nWhere: b; touches: none\nWhy: c\nHow: 3/3 passed\nNeed: nothing\n' > "$CE/muster/BOARD.md"
$PY "$ROOT/scripts/check-edition.py" "$CE" >/dev/null || fail "check-edition flagged a good entry"
printf '### 2026-11-08 | READY | Builder -> Inspector | bad\nWhat: a\nWhere: b\n' >> "$CE/muster/BOARD.md"
if $PY "$ROOT/scripts/check-edition.py" "$CE" >"$CE/out" 2>&1; then fail "check-edition passed a broken entry"; fi
grep -q "bad: no 'Why:' line" "$CE/out" || fail "check-edition did not name the missing line: $(cat "$CE/out")"
step "a project profile (PINR): its chat names, report shape, recorder, board path, no second talk check; Muster unchanged without it"
PS=$($PY "$ROOT/scripts/profile-selftest.py") || { echo "$PS"; fail "the profile self-test has a miss"; }
echo "$PS" | tail -1

step "scripts/install-checks.py installs the coded rules in a project without the plugin, twice safely, and removes them"
IC="$SCRATCH/ic"; mkdir -p "$IC/.claude"; echo '{"permissions":{"allow":["Bash(ls)"]}}' > "$IC/.claude/settings.json"
$PY "$ROOT/scripts/install-checks.py" "$IC" >/dev/null && $PY "$ROOT/scripts/install-checks.py" "$IC" >/dev/null || fail "install-checks failed"
$PY -c "import json,sys;d=json.load(open(sys.argv[1]+'/.claude/settings.json'));assert len(d['hooks']['Stop'])==1 and len(d['hooks']['PreToolUse'])==1 and d['permissions']['allow']==['Bash(ls)']" "$IC" || fail "install-checks doubled or lost settings"
[ -f "$IC/.muster-checks/rules-check.py" ] || fail "install-checks copied no rules-check.py"
$PY "$ROOT/scripts/install-checks.py" "$IC" --remove >/dev/null; [ ! -d "$IC/.muster-checks" ] || fail "--remove left the copies"
step "scripts/plugin-live.sh switches Muster to load live from its folder, keeps a backup, and puts it back"
PL="$SCRATCH/plive"; mkdir -p "$PL/cfg/plugins" "$PL/muster/.claude-plugin"
printf '{"name":"muster-kit","owner":{"name":"t"},"plugins":[{"name":"muster","version":"1.0.0","source":"./"}]}\n' > "$PL/muster/.claude-plugin/marketplace.json"
printf '{"theme":"dark","extraKnownMarketplaces":{"muster-kit":{"source":{"source":"github","repo":"x/muster"},"autoUpdate":true},"other":{"source":{"source":"github","repo":"x/o"}}}}\n' > "$PL/cfg/settings.json"
printf '{"muster-kit":{"source":{"source":"github","repo":"x/muster"},"installLocation":"/x","lastUpdated":"2026-01-01T00:00:00.000Z"}}\n' > "$PL/cfg/plugins/known_marketplaces.json"
cp "$PL/cfg/settings.json" "$PL/settings.before"
bash "$ROOT/scripts/plugin-live.sh" --path "$PL/muster" --config-dir "$PL/cfg" --dry-run | grep -q "DRY RUN OK" || fail "plugin-live dry run did not say so"
cmp -s "$PL/cfg/settings.json" "$PL/settings.before" || fail "plugin-live dry run changed the settings"
bash "$ROOT/scripts/plugin-live.sh" --path "$PL/muster" --config-dir "$PL/cfg" --no-cli >"$PL/out.txt" 2>&1 || { cat "$PL/out.txt"; fail "plugin-live --no-cli failed"; }
PLM="$PL/muster"; command -v cygpath >/dev/null 2>&1 && PLM=$(cygpath -m "$PLM")
$PY - "$PL/cfg/settings.json" "$PLM" <<'PY' || fail "plugin-live did not write the directory source and keep the rest"
import json, sys
d = json.load(open(sys.argv[1]))
s = d["extraKnownMarketplaces"]["muster-kit"]["source"]
assert s == {"source": "directory", "path": sys.argv[2]}, s
assert d["theme"] == "dark" and d["extraKnownMarketplaces"]["other"]["source"]["repo"] == "x/o"
PY
ls -d "$PL"/cfg/muster-live-backup-*/ >/dev/null 2>&1 || fail "plugin-live kept no backup"
bash "$ROOT/scripts/plugin-live.sh" --config-dir "$PL/cfg" --undo >/dev/null || fail "plugin-live --undo failed"
cmp -s "$PL/cfg/settings.json" "$PL/settings.before" || fail "plugin-live --undo did not put the settings back"
if bash "$ROOT/scripts/plugin-live.sh" --path "$PL/nowhere" --config-dir "$PL/cfg" >/dev/null 2>&1; then fail "plugin-live accepted a folder with no marketplace"; fi
if command -v claude >/dev/null 2>&1; then
  # the real program: a scratch configuration with its own plugin list must say "Read from" the folder; a failed switch must put everything back
  mkdir -p "$PL/muster/skills/hello"; printf '{"name":"muster","version":"1.0.0"}\n' > "$PL/muster/.claude-plugin/plugin.json"
  printf '# hi\n' > "$PL/muster/skills/hello/SKILL.md"
  ( cd "$PL" && git init -q muster && git -C muster add -A && git -C muster -c user.name=t -c user.email=t@localhost commit -q -m x )
  bash "$ROOT/scripts/plugin-live.sh" --path "$PL/muster" --config-dir "$PL/cfg" >"$PL/real.out" 2>&1 || { cat "$PL/real.out"; fail "plugin-live with the real claude program failed"; }
  ( cd "$PL" && CLAUDE_CONFIG_DIR="$PL/cfg" claude plugin install muster@muster-kit >/dev/null 2>&1; CLAUDE_CONFIG_DIR="$PL/cfg" claude plugin list 2>&1 | grep 'Read from:' | tr '\\' '/' | grep -qiF 'plive/muster' ) || fail "the plugin does not read from the folder"
  # a chat started from any other folder (the manager's chat starts in the folder above the checkouts) reads it live too: the install is user-wide
  mkdir -p "$PL/home"
  ( cd "$PL/home" && CLAUDE_CONFIG_DIR="$PL/cfg" claude plugin list 2>&1 | grep 'Read from:' | tr '\\' '/' | grep -qiF 'plive/muster' ) || fail "a chat started from another folder does not read from the folder"
else
  echo "   (the claude program is not on this computer: the real-program part was skipped)"
fi

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
