#!/usr/bin/env python3
"""Self-test for the project profile (profiles/pinr.json): the five things a project like PINR needs from the coded checks,
and that Muster's own behaviour does not change without a profile. Prints 'N of M passed'; exit 1 on any miss.
Writes only in a temporary folder. Standard library only."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
T = tempfile.mkdtemp()
PROJ = os.path.join(T, "proj")
CK = os.path.join(PROJ, ".muster-checks")
BOARD_REL = "Claude Code/handoff/BOARD.md"
os.makedirs(CK)
os.makedirs(os.path.join(PROJ, os.path.dirname(BOARD_REL)))
for f in ("hooks/rules-check.py", "hooks/board-stop.py", "hooks/talk-check.py"):
    shutil.copyfile(os.path.join(ROOT, f), os.path.join(CK, os.path.basename(f)))
prof = json.load(open(os.path.join(ROOT, "profiles", "pinr.json")))
prof["board"] = BOARD_REL
json.dump(prof, open(os.path.join(CK, "profile.json"), "w"))
NOPROF = os.path.join(T, "plain")
os.makedirs(NOPROF)
for f in ("hooks/rules-check.py", "hooks/board-stop.py", "hooks/talk-check.py"):
    shutil.copyfile(os.path.join(ROOT, f), os.path.join(NOPROF, os.path.basename(f)))


def tr(first, extra=()):
    p = os.path.join(T, "t%d.jsonl" % len(os.listdir(T)))
    with open(p, "w") as f:
        f.write(json.dumps({"type": "user", "message": {"content": first}}) + "\n")
        for e in extra:
            f.write(json.dumps(e) + "\n")
    return p


def use(name, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


def run(script, ev, plain=False, **kw):
    d = NOPROF if plain else CK
    r = subprocess.run([PY, os.path.join(d, script)], input=json.dumps(dict(hook_event_name=ev, cwd=PROJ, **kw)),
                       capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != "MUSTER_PROFILE"})
    return r.stdout.strip()


site = tr("You are Site_PINR_002. Job: Site_PINR_002, builds the site.")
teacher = tr("You are PINRai_teacher_001.")
mgr = tr("You are Manager_PINR_002. Job: Manager_PINR_002.")
mgr_note = tr("Job: Site_PINR_002: builds. Reports go to Manager_PINR_002.")
pinr_report = "READY: card fix\nWhat: a\nWhere: main abc; touches: none\nWhy: c\nHow: 3/3 passed\nNeed: nothing"
send = lambda msg, t, **k: run("rules-check.py", "PreToolUse", tool_name="SendMessage", tool_input={"to": "Manager", "message": msg}, transcript_path=t, **k)
board = os.path.join(PROJ, BOARD_REL)


def write_board(*lines):
    open(board, "w").write("# PINR handoff board\n\n## Entries (newest first)\n\n" + "\n".join(lines) + "\n")


cases = []
add = lambda name, out, blocked: cases.append((name, out, blocked))
# 1 chat names
add("1 a PINR report from Site_PINR_002 is checked, and passes", send(pinr_report, site), False)
add("1 the same chat's bad report is refused", send("READY: card fix\nWhat: only one line", site), True)
add("1 PINRai_teacher_001 is a crew chat too", send("NEED: x\nWhat: only one line", teacher), True)
add("1 the owner's own chat is untouched", send("hello team", tr("hi there")), False)
add("1 without the profile Site_PINR_002 is not a crew chat (Muster unchanged)", send("NEED: x\nWhat: only one line", site, plain=True), False)
# 2 report shape
add("2 no ID and no Usage line is fine for PINR", send(pinr_report, site), False)
add("2 a five-line report is still refused", send(pinr_report.replace("Why: c\n", ""), site), True)
add("2 a READY with no test count is still refused", send(pinr_report.replace("3/3 passed", "fine"), site), True)
add("2 Where without touches is still refused", send(pinr_report.replace("; touches: none", ""), site), True)
add("2 Muster's own shape still needs the ID without the profile", send(pinr_report, tr("You are Builder A_Muster_003"), plain=True), True)
add("2 PINR has no order shape: a plain order goes through", send("Please build the card fix. Own the cards only.", mgr), False)
# 3 recorder
asked = [use("AskUserQuestion", questions=[])]
add("3 an answered card with no recording blocks the PINR manager", run("rules-check.py", "Stop", last_assistant_message="ok", transcript_path=tr("You are Manager_PINR_002", asked)), True)
add("3 decide.py recording passes", run("rules-check.py", "Stop", last_assistant_message="ok", transcript_path=tr("You are Manager_PINR_002", asked + [use("Bash", command="python3 manager/decide.py --title t --picked A")])), False)
add("3 record-choice.py does not count under the PINR profile", run("rules-check.py", "Stop", last_assistant_message="ok", transcript_path=tr("You are Manager_PINR_002", asked + [use("Bash", command="python3 scripts/record-choice.py p 3")])), True)
add("3 Muster itself still wants record-choice.py", run("rules-check.py", "Stop", plain=True, last_assistant_message="ok", transcript_path=tr("You are Manager_Muster_002", asked + [use("Bash", command="python3 manager/decide.py --title t")])), True)
add("3 the PINR manager is the manager: a non-question is blocked", run("rules-check.py", "Stop", last_assistant_message="All done, nice.", transcript_path=mgr), True)
add("3 a PINR worker whose note names the manager is not the manager", run("rules-check.py", "Stop", last_assistant_message="**READY · x**\n- a\n- b", transcript_path=mgr_note), False)
# 4 board path (lines style)
write_board("2026-11-08 | NEED | Site_PINR_002 -> Manager | token wording", "2026-11-08 | LIVE | Look Header_PINR_002 -> Manager | Paused: yes | fix live")  # file order: oldest first
bs = lambda said, t=mgr, **k: run("board-stop.py", "Stop", last_assistant_message=said, transcript_path=t, **k)
add("4 a chat whose last line says Paused: yes reaches the manager", bs("Fine."), True)
add("4 naming that chat clears it", bs("Look Header_PINR_002 is waiting for you: type in Look Header_PINR_002."), False)
add("4 an old NEED line is not nagged (no closing mark exists)", (write_board("2026-11-08 | NEED | Site_PINR_002 -> Manager | x") or bs("Fine.")), False)
add("4 a later line from the same chat clears a pause", (write_board("2026-11-08 | LIVE | Look Header_PINR_002 -> Manager | Paused: yes | fix", "2026-11-08 | DONE | Look Header_PINR_002 -> Manager | next thing") or bs("Fine.")), False)
add("4 a pause followed by a later line (no Paused word) from the same chat is cleared, a later 'Paused: no' too", (write_board("2026-11-07 | LIVE | Manager_PINR_002 -> Site | Paused: yes | x", "2026-11-08 | NEED | Look Header_PINR_002 -> Manager | Paused: yes | y", "2026-11-08 | RESUMED | Look Header_PINR_002 -> Manager | Paused: no | y", "2026-11-09 | DONE | Manager_PINR_002 -> Site | ok") or bs("Fine.")), False)
add("4 a pause that is a chat's latest line still counts when others wrote after it", (write_board("2026-11-08 | LIVE | Look Header_PINR_002 -> Manager | Paused: yes | x", "2026-11-09 | DONE | Site_PINR_002 -> Manager | later") or bs("Fine.")), True)
add("4 a worker chat is never nagged", (write_board("2026-11-08 | LIVE | Site_PINR_002 -> Manager | Paused: yes | x") or bs("Fine.", t=site)), False)
add("4 no board at the path is silent", (os.remove(board) or bs("Fine.")), False)
# 5 no second talk check
bare = "See hooks/rules-check.py for it."
add("5 talk-check is off under the PINR profile", run("talk-check.py", "Stop", last_assistant_message=bare, transcript_path=site), False)
add("5 talk-check still works without the profile", run("talk-check.py", "Stop", plain=True, last_assistant_message=bare, transcript_path=tr("You are Builder A_Muster_003")), True)
# install-checks and check-report
IC = os.path.join(T, "ic")
os.makedirs(IC)
ic = lambda *a: subprocess.run([PY, os.path.join(ROOT, "scripts", "install-checks.py"), *a], capture_output=True, text=True)
dry = ic(IC, "--profile", "pinr", "--dry-run")
add("install-checks --dry-run writes nothing", "" if dry.returncode == 0 and os.listdir(IC) == [] and "DRY RUN" in dry.stdout and "profile" in dry.stdout else "BAD " + dry.stdout + dry.stderr, False)
ic(IC, "--profile", "pinr")
ic(IC, "--profile", "pinr")
st = json.load(open(os.path.join(IC, ".claude", "settings.json")))
add("install-checks --profile copies profile.json, and twice is safe", "" if os.path.isfile(os.path.join(IC, ".muster-checks", "profile.json")) and len(st["hooks"]["Stop"]) == 1 else "BAD", False)
add("install-checks refuses an unknown profile", "" if ic(IC, "--profile", "nope").returncode == 1 else "BAD", False)
ic(IC)
add("install-checks without a profile removes the old profile", "" if not os.path.exists(os.path.join(IC, ".muster-checks", "profile.json")) else "BAD", False)
rf = os.path.join(T, "r.txt")
open(rf, "w").write(pinr_report)
cr = lambda *a: subprocess.run([PY, os.path.join(ROOT, "scripts", "check-report.py"), *a], capture_output=True, text=True).returncode
add("check-report --profile pinr accepts a PINR report", "" if cr(rf, "--profile", "pinr") == 0 else "BAD", False)
add("check-report without a profile still wants the ID", "" if cr(rf) == 1 else "BAD", False)

bad = 0
for name, out, should_block in cases:
    ok = bool(out) == should_block
    bad += not ok
    print(("ok   " if ok else "MISS ") + name + ("" if ok else "  -> " + out[:200]))
print("%d of %d passed" % (len(cases) - bad, len(cases)))
shutil.rmtree(T, ignore_errors=True)
sys.exit(1 if bad else 0)
