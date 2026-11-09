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
BIN = os.environ.get("MUSTER_CHECKS_BIN")  # run the same cases against the ready-built Rust copy
SUB = {"rules-check.py": "rules", "board-stop.py": "board-stop", "talk-check.py": "talk"}
ENV = dict((k, v) for k, v in os.environ.items() if k != "MUSTER_PROFILE")
ENV["MUSTER_MESSAGE_FORM"] = "text"  # these cases are the older text shapes
T = tempfile.mkdtemp()
PROJ = os.path.join(T, "proj")
CK = os.path.join(PROJ, ".muster-checks")
BOARD_REL = "Claude Code/handoff/BOARD.md"
os.makedirs(CK)
os.makedirs(os.path.join(PROJ, os.path.dirname(BOARD_REL)))
def put_checks(dest):
    """The hooks the test runs: the Python files, or one copy of the Rust program."""
    if BIN:
        shutil.copyfile(BIN, os.path.join(dest, "muster-checks" + (".exe" if BIN.endswith(".exe") else "")))
        os.chmod(os.path.join(dest, os.path.basename(BIN)), 0o755)
    for f in ("hooks/rules-check.py", "hooks/board-stop.py", "hooks/talk-check.py"):
        shutil.copyfile(os.path.join(ROOT, f), os.path.join(dest, os.path.basename(f)))


def cmd_for(dest, script):
    return [os.path.join(dest, os.path.basename(BIN)), SUB[script]] if BIN else [PY, os.path.join(dest, script)]


put_checks(CK)
prof = json.load(open(os.path.join(ROOT, "profiles", "pinr.json")))
prof["board"] = BOARD_REL
json.dump(prof, open(os.path.join(CK, "profile.json"), "w"))
NOPROF = os.path.join(T, "plain")
os.makedirs(NOPROF)
put_checks(NOPROF)


def tr(first, extra=()):
    p = os.path.join(T, "t%d.jsonl" % len(os.listdir(T)))
    with open(p, "w") as f:
        f.write(json.dumps({"type": "user", "message": {"content": first}}) + "\n")
        for e in extra:
            f.write(json.dumps(e) + "\n")
    return p


def use(name, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


PLAINPROJ = os.path.join(T, "plainproj")
os.makedirs(PLAINPROJ)


def run(script, ev, plain=False, cwd=None, **kw):
    d = NOPROF if plain else CK
    r = subprocess.run(cmd_for(d, script), input=json.dumps(dict(hook_event_name=ev, cwd=cwd or (PLAINPROJ if plain else PROJ), **kw)),
                       capture_output=True, text=True, env=ENV)
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
# the plugin's own copy stands down where .muster-checks is installed; the board path is joined to the folder holding it
add("6 the plugin's talk-check stands down in a project with its own copy", run("talk-check.py", "Stop", plain=True, cwd=PROJ, last_assistant_message=bare, transcript_path=tr("You are Builder A_Muster_003")), False)
add("6 the plugin's rules-check stands down too", run("rules-check.py", "PreToolUse", plain=True, cwd=PROJ, tool_name="SendMessage", tool_input={"to": "x", "message": "noted"}, transcript_path=tr("You are Builder A_Muster_003")), False)
add("6 ...and from a sub-folder of that project", run("rules-check.py", "PreToolUse", plain=True, cwd=os.path.join(PROJ, "sub"), tool_name="SendMessage", tool_input={"to": "x", "message": "noted"}, transcript_path=tr("You are Builder A_Muster_003")), False)
add("6 the installed copy itself still works", run("rules-check.py", "PreToolUse", tool_name="SendMessage", tool_input={"to": "x", "message": "noted"}, transcript_path=tr("You are Builder A_Muster_003")), True)
add("6 without .muster-checks the plugin's own copy still works", run("rules-check.py", "PreToolUse", plain=True, tool_name="SendMessage", tool_input={"to": "x", "message": "noted"}, transcript_path=tr("You are Builder A_Muster_003")), True)
# the shipped profile's real board path: a folder holding .muster-checks, the board beside it under PINR-claudecode-handoff/
REAL = os.path.join(T, "pinrlike", "Claude Code")
os.makedirs(os.path.join(REAL, ".muster-checks"))
put_checks(os.path.join(REAL, ".muster-checks"))
shutil.copyfile(os.path.join(ROOT, "profiles", "pinr.json"), os.path.join(REAL, ".muster-checks", "profile.json"))
rb = os.path.join(REAL, json.load(open(os.path.join(ROOT, "profiles", "pinr.json")))["board"])
os.makedirs(os.path.dirname(rb))
open(rb, "w").write("2026-11-08 | LIVE | Look Header_PINR_002 -> Manager | Paused: yes | x\n")
real = lambda said: subprocess.run(cmd_for(os.path.join(REAL, ".muster-checks"), "board-stop.py"), input=json.dumps({"hook_event_name": "Stop", "cwd": REAL, "last_assistant_message": said, "transcript_path": mgr}), capture_output=True, text=True, env=ENV).stdout.strip()
add("6 the shipped profile's board path is found from the folder holding .muster-checks", real("Fine."), True)
# gaps: social replies of several words, and PINR's own manager-only paths
add("7 'noted, thanks' is refused in a PINR chat", send("noted, thanks", site), True)
add("7 'Thanks - got it' is refused too", send("Thanks - got it", site), True)
W = lambda path, t: run("rules-check.py", "PreToolUse", tool_name="Write", tool_input={"file_path": path}, transcript_path=t)
C = "/work/PINRroot/Claude Code"
for rel in ("Founder/FOUNDER-LIST.md", "PINR-claudecode-handoff/pinr-claude-code-starter-v2/DECISIONS-LOG.md", "manager/rules/Site_001.md", "CLAUDE.md"):
    add("7 a PINR worker cannot write %s" % rel, W(C + "/" + rel, site), True)
    add("7 the PINR manager can write %s" % rel, W(C + "/" + rel, mgr), False)
add("7 the engine's own CLAUDE.md is not on the list", W(C + "/PINR-claudecode-handoff/pinr-claude-code-starter-v2/CLAUDE.md", site), False)
add("7 a worker's ordinary file is not on the list", W(C + "/pinr-live/src/a.js", site), False)
add("7 without the profile PINR's paths are not protected", run("rules-check.py", "PreToolUse", plain=True, tool_name="Write", tool_input={"file_path": C + "/CLAUDE.md"}, transcript_path=tr("You are Builder A_Muster_003")), False)
# the manager test: only a chat's own name makes it the manager
card = "**READY \u00b7 x**\n- a\n- b"
ins = tr("Your starting note: report to Manager_PINR_002. Job: Look Inspector_PINR_001, reads the look work.")
add("8 a PINR worker whose note says to report to Manager_PINR_002 is not the manager", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=ins), False)
add("8 ...even when the manager is named first and its own name comes after 'You are'", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=tr("Manager_PINR_002 started this chat. You are Look Inspector_PINR_001.")), False)
add("8 the PINR manager by 'Job:' is the manager", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=tr("Job: Manager_PINR_002, the founder's go-between. Workers: Site_PINR_002")), True)
add("8 the PINR manager by 'You are' is the manager", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=tr("You are Manager_PINR_002. Look Inspector_PINR_001 reports to you.")), True)
# real starting-note shapes (made-up names and ids)
WT = "<system-reminder>\nYou are operating in a git worktree.\nWorktree path: /w/x\n</system-reminder>\n\nBackground (from the session that started this one):\nPINR is a project; its manager is Manager_PINR_002 and all reports go to Manager_PINR_002.\n\nTask:\n"
add("8 a renewed PINR worker: 'You are operating in a git worktree', then 'You are Site_PINR_004' is a worker", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=tr(WT + "You are Site_PINR_004. Report to Manager_PINR_002.")), False)
add("8 ...and by a Job line with a two-word name", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=tr(WT + "Job:   Look Inspector_PINR_002, reads the look work. Reports go to Manager_PINR_002.")), False)
add("8 ...and PINRai_teacher_003", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=tr(WT + "You are PINRai_teacher_003.")), False)
add("8 the renewed PINR manager behind the same worktree lines is the manager", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=tr(WT + "You are Manager_PINR_003.")), True)
add("8 a Muster note 'You are one of the Muster crew ... Manager_Muster_001 gives every order' is a worker", run("rules-check.py", "Stop", plain=True, last_assistant_message=card, transcript_path=tr("Background: You are one of the Muster crew. Manager_Muster_001 gives every order. Builder A_Muster_001 builds. Task: read your rules page.")), False)
add("8 setup's manager note (Job: go-between, agents/manager.md) is the manager", run("rules-check.py", "Stop", plain=True, last_assistant_message=card, transcript_path=tr("Task:\nJob:       the owner's go-between and record keeper for this project\nOwns: muster/\nFirst: read agents/manager.md")), True)
add("8 a note naming only agents/builder.md is a worker even if it mentions the manager", run("rules-check.py", "Stop", plain=True, last_assistant_message=card, transcript_path=tr("Read agents/builder.md. Send reports to Manager_Muster_002.")), False)
# shell writes into PINR's manager-only files
B = lambda cmd, t, **k: run("rules-check.py", "PreToolUse", tool_name="Bash", tool_input={"command": cmd}, transcript_path=t, **k)
P1 = '"%s/Founder/FOUNDER-LIST.md"' % C
P2 = '"%s/manager/rules/Site_001.md"' % C
for what, cmd in (("a redirect", "echo x > " + P1), ("an append", "echo x >> " + P1), ("tee", "echo x | tee -a " + P1),
                  ("sed -i", "sed -i '' s/a/b/ " + P1), ("cp", "cp /tmp/a.md " + P2), ("mv", "mv /tmp/a.md " + P2),
                  ("a redirect after other commands", "ls && echo x 2>&1 > " + P2), ("a relative path", "cd '%s' && echo x >> CLAUDE.md" % C)):
    add("9 a worker's %s into a PINR manager-only file is denied" % what, B(cmd, site, cwd=C if "relative" in what else None), True)
add("9 the PINR manager may write them by shell", B("echo x >> " + P1, mgr), False)
add("9 a worker's ordinary shell write is allowed", B("echo x > /tmp/notes.txt && cp a.js b.js", site), False)
add("9 reading a protected file is allowed", B("cat " + P1 + " | head", site), False)
add("9 copying a protected file out is allowed", B("cp " + P1 + " /tmp/copy.md", site), False)
add("9 without the profile a shell write to the same path is not guarded", B("echo x >> " + P1, tr("You are Builder A_Muster_003"), plain=True), False)
# a PINR start note whose Job line names no crew name and only mentions the manager: never the manager
NOJOB = WT + "Job:       build the evidence web page (decision 438)\nOwns:      pinr-live/src/web/\nNot yours: the engine; report to Manager_PINR_002\nOpen:      the web page\n"
add("8 a Job line with no crew name that mentions Manager_PINR_002 is a worker", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=tr(NOJOB)), False)
add("8 ...and such a worker cannot write PINR's manager-only paths", run("rules-check.py", "PreToolUse", tool_name="Write", tool_input={"file_path": "/w/Claude Code/CLAUDE.md"}, transcript_path=tr(NOJOB)), True)
add("8 ...and cannot shell-write them either", run("rules-check.py", "PreToolUse", tool_name="Bash", tool_input={"command": "echo x >> '/w/Claude Code/CLAUDE.md'"}, transcript_path=tr(NOJOB)), True)
# a chat after its first summary: the first message is the summary
SUM = "This session is being continued from a previous conversation that ran out of context.\n\nSummary: ... You are operating in a git worktree ... "
add("8 a summarized manager ('I am **Manager_PINR_001**') is still the manager", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=tr(SUM + "I am **Manager_PINR_001**, the founder's go-between. Workers report to me.")), True)
add("8 a summarized worker ('I am Site_PINR_003', manager named after) is still a worker", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=tr(SUM + "I am Site_PINR_003 and report to **Manager_PINR_002**.")), False)
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
