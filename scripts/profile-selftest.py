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


def run(script, ev, plain=False, cwd=None, state=None, **kw):
    d = NOPROF if plain else CK
    env = dict(ENV, MUSTER_STATE_DIR=state or tempfile.mkdtemp(dir=T))  # a fresh memory of what the manager was told, unless a case shares one
    r = subprocess.run(cmd_for(d, script), input=json.dumps(dict(hook_event_name=ev, cwd=cwd or (PLAINPROJ if plain else PROJ), **kw)),
                       capture_output=True, text=True, env=env)
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
add("D-040: a PINR report from Site_PINR (no number) is checked, and its bad report refused", send("READY: card fix\nWhat: only one line", tr("You are Site_PINR, agents/builder.md")), True)
add("D-040: crew-plan names the copy of a chat with no number", "" if subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "crew-plan.py"), "copy-name", "Builder A_Shop"], capture_output=True, text=True).stdout.strip() == "builder-a" else "BAD", False)
_pq = os.path.join(T, "pq"); os.makedirs(os.path.join(_pq, "Founder"))
open(os.path.join(_pq, "Founder", "FOUNDER-LIST.md"), "w").write("## Open\n\n7. \"fix the menu\"\n   Choice (2026-11-08): which?\n     Picked: A\n\n8. \"why waiting\"\n")
def _qo(item, turn):
    t = tr("You are Manager_PINR_002, the go-between", turn)
    o = "To: Engine_PINR\nJob: menu\nOwner's words: \"fix the menu\" (item %d)\nOwns: a\nOut: b\nAccept: a\nDone: c" % item
    r = subprocess.run([BIN, "rules"] if BIN else [sys.executable, os.path.join(ROOT, "hooks", "rules-check.py")], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=_pq, tool_name="SendMessage", tool_input={"to": "Engine_PINR", "message": o}, transcript_path=t)), capture_output=True, text=True, env=dict(os.environ, MUSTER_PROFILE=os.path.join(ROOT, "profiles", "pinr.json")))
    return r.stdout
add("item 115: PINR's manager order in a turn his question started is refused", "" if "item 115" in _qo(8, [{"type": "user", "message": {"content": "why is engine waiting?"}}]) else "BAD", False)
add("item 115: ...and goes through when it cites a recorded choice", "" if "item 115" not in _qo(7, [{"type": "user", "message": {"content": "why is engine waiting?"}}]) else "BAD", False)
# item 117: blocking guards, from the project's own "guard" config; nothing is hard-coded to a project
_gd = os.path.join(T, "guard"); os.makedirs(_gd)
_gp = os.path.join(_gd, "profile.json")
_prot = os.path.join(_gd, "main")
os.makedirs(os.path.join(_prot, ".claude", "worktrees", "copy"))
json.dump({"name": "G", "crew_names": ["\\bBuilder A_G\\b"], "guard": {"protected_folders": [_prot], "public_repos": [{"name": "pub-view", "scanner": "bash scan.sh"}], "push_allowed": ["own"]}}, open(_gp, "w"))
for _d, _u in ((_prot, "https://github.com/acme/pub-view.git"), (os.path.join(_gd, "other"), "https://github.com/acme/leaky.git"), (os.path.join(_gd, "own"), "git@github.com:acme/own.git")):
    os.makedirs(_d, exist_ok=True)
    subprocess.run(["git", "init", "-q", _d], capture_output=True)
    subprocess.run(["git", "-C", _d, "remote", "add", "origin", _u], capture_output=True)
_gt = tr("You are Builder A_G, agents/builder.md")
def _g(tool, cwd=None, **inp):
    env = dict(ENV, MUSTER_PROFILE=_gp, MUSTER_GUARD_PUBLIC="pub-view,leaky,own")
    r = subprocess.run([BIN, "rules"] if BIN else [sys.executable, os.path.join(ROOT, "hooks", "rules-check.py")], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=cwd or _prot, tool_name=tool, tool_input=inp, transcript_path=_gt)), capture_output=True, text=True, env=env)
    return r.stdout
_blocked = lambda out, word: "item 117" in out and word in out
_K = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
_E = "STRIPE_API_" + "KEY=" + "abcd1234efgh5678"
for _n, _cmd, _cwd, _word, _want in [
    ("git reset in the protected main folder", "git reset --hard HEAD~1", None, "reset", True),
    ("git checkout . in the protected main folder", "git checkout .", None, "checkout", True),
    ("git stash in the protected main folder", "git stash", None, "stash", True),
    ("git -C into the protected folder from elsewhere", "git -C %s stash" % _prot.replace("\\", "/"), os.path.join(_gd, "other"), "stash", True),
    ("cd into the protected folder first", "cd %s && git reset" % _prot.replace("\\", "/"), os.path.join(_gd, "other"), "reset", True),
    ("git stash list is only a look", "git stash list", None, "stash", False),
    ("git status is fine", "git status", None, "status", False),
    ("git reset in a crew copy under the protected folder", "git reset --hard", os.path.join(_prot, ".claude", "worktrees", "copy"), "reset", False),
    ("git reset in an unprotected folder", "git reset --hard", os.path.join(_gd, "other"), "reset", False),
    ("git push to the named public repo, not through its scanner", "git push origin main", _prot, "scanner", True),
    ("the scanner command itself is not a push", "bash scan.sh", _prot, "scanner", False),
    ("git push to another public repo the project does not allow", "git push origin main", os.path.join(_gd, "other"), "leaky", True),
    ("git push to a public repo the project allows", "git push origin main", os.path.join(_gd, "own"), "own", False),
    ("a commit message with a key in it", "git commit -m 'add %s'" % _K, None, "commit message", True),
    ("a commit message with a placeholder", "git commit -m 'add key <your-key>'", None, "commit message", False),
]:
    _o = _g("Bash", _cwd, command=_cmd)
    add("item 117: " + _n + (" is refused" if _want else " goes through"), "" if _blocked(_o, _word) == _want else "BAD " + _o[:200], False)
_tf = os.path.join(_gd, "other", "conf.txt")
for _n, _tool, _inp, _word, _want in [
    ("a key written into a tracked file", "Write", dict(file_path=_tf, content="token " + _K), "tracked file", True),
    (".env-style secret lines written into a tracked file", "Write", dict(file_path=_tf, content=_E + "\n"), "tracked file", True),
    ("placeholder .env lines are fine", "Write", dict(file_path=_tf, content="STRIPE_API_KEY=<your-key>\nAPI_SECRET=changeme-please\n"), "tracked file", False),
    ("a .env.example may hold anything", "Write", dict(file_path=os.path.join(_gd, "other", ".env.example"), content=_E), "tracked file", False),
    ("a key sent in a message", "SendMessage", dict(to="x", message="the key is " + _K), "a message", True),
    ("an ordinary edit", "Edit", dict(file_path=_tf, new_string="hello"), "tracked file", False),
]:
    _o = _g(_tool, None, **_inp)
    add("item 117: " + _n + (" is refused" if _want else " goes through"), "" if _blocked(_o, _word) == _want else "BAD " + _o[:200], False)
open(os.path.join(_gd, "other", ".gitignore"), "w").write(".env\n")
add("item 117: ...once .gitignore names it", "" if not _blocked(_g("Write", None, file_path=os.path.join(_gd, "other", ".env"), content=_E), "tracked file") else "BAD", False)
add("item 117: with no guard in the profile nothing is refused", "" if "item 117" not in subprocess.run([sys.executable, os.path.join(ROOT, "hooks", "rules-check.py")], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=_prot, tool_name="Bash", tool_input=dict(command="git reset --hard"), transcript_path=_gt)), capture_output=True, text=True, env=dict(ENV)).stdout else "BAD", False)
# item 117, PINR-shaped end to end: the project keeps its guard in its OWN .muster-checks/profile.json, runs its own older installed
# rules-check.py (no guard code; the plugin's rules-check stands down there), and the chat is a crew chat named in that profile
import shutil
_pp = os.path.join(T, "pinrshape"); os.makedirs(os.path.join(_pp, ".muster-checks")); os.makedirs(os.path.join(_pp, "sub"))
open(os.path.join(_pp, ".muster-checks", "rules-check.py"), "w").write("# older installed copy, no guard\n")
json.dump({"name": "P", "crew_names": ["\\bManager_P_\\d{3}\\b"], "guard": {"protected_folders": [_pp], "public_repos": [{"name": "pub-view", "scanner": "bash scan.sh"}]}}, open(os.path.join(_pp, ".muster-checks", "profile.json"), "w"))
subprocess.run(["git", "init", "-q", _pp], capture_output=True)
_plug = os.path.join(T, "plug"); os.makedirs(os.path.join(_plug, "scripts"))   # a plugin copy with no ready-made program: the Python copy runs
shutil.copytree(os.path.join(ROOT, "hooks"), os.path.join(_plug, "hooks"))
for _f in ("find-binary.sh", "find-python.sh"):
    shutil.copy(os.path.join(ROOT, "scripts", _f), os.path.join(_plug, "scripts", _f))
_pt = tr("You are Manager_P_001, the go-between")
_penv = {k: v for k, v in ENV.items() if k != "MUSTER_PROFILE"}
def _pg(runner, cmd, cwd=None, trans=None, proj=None):
    ev = dict(hook_event_name="PreToolUse", cwd=cwd or _pp, tool_name="Bash", tool_input=dict(command=cmd), transcript_path=trans or _pt)
    r = subprocess.run(runner, input=json.dumps(ev), capture_output=True, text=True, env=dict(_penv, CLAUDE_PROJECT_DIR=proj or _pp, MUSTER_GUARD_PUBLIC="pub-view"))
    return r.stdout
_runners = [("python", ["sh", os.path.join(_plug, "hooks", "guard-check.sh")])] + ([("program", [BIN, "guard"])] if BIN else [])
for _rn, _rr in _runners:
    add("item 117 (project profile, %s): git -C into its main folder with reset is refused" % _rn, "" if _blocked(_pg(_rr, 'git -C "%s" reset --help' % _pp.replace("\\", "/"), cwd=os.path.join(T, "elsewhere")), "reset") else "BAD", False)
    add("item 117 (project profile, %s): git reset in its main folder is refused" % _rn, "" if _blocked(_pg(_rr, "git reset --hard"), "reset") else "BAD", False)
    add("item 117 (project profile, %s): ...from a sub-folder too" % _rn, "" if _blocked(_pg(_rr, "git stash", cwd=os.path.join(_pp, "sub"), proj=os.path.join(_pp, "sub")), "stash") else "BAD", False)
    add("item 117 (project profile, %s): git status goes through" % _rn, "" if not _pg(_rr, "git status") else "BAD", False)
    add("item 117 (project profile, %s): a chat that is not a crew chat is untouched" % _rn, "" if not _pg(_rr, "git reset --hard", trans=tr("hello there")) else "BAD", False)
add("item 117 (project profile): a project profile with no guard refuses nothing", (lambda: "" if not (json.dump({"name": "P", "crew_names": ["\\bManager_P_\\d{3}\\b"]}, open(os.path.join(_pp, ".muster-checks", "profile.json"), "w")) or _pg(_runners[0][1], "git reset --hard")) else "BAD")(), False)
# ...and the guard may sit in the profile a live stand-in points to (live.json -> <Muster folder>/<profile>), not only in the project's own file
_lm = os.path.join(T, "livemuster"); os.makedirs(os.path.join(_lm, "profiles"))
json.dump({"name": "P", "guard": {"protected_folders": [_pp]}}, open(os.path.join(_lm, "profiles", "g.json"), "w"))
json.dump({"muster": _lm, "profile": "profiles/g.json"}, open(os.path.join(_pp, ".muster-checks", "live.json"), "w"))
for _rn, _rr in _runners:
    add("item 117 (live.json profile, %s): a guard in the profile the stand-in points to is refused" % _rn, "" if _blocked(_pg(_rr, "git reset --hard"), "reset") else "BAD", False)
    add("item 117 (live.json profile, %s): ...and git status goes through" % _rn, "" if not _pg(_rr, "git status") else "BAD", False)
os.remove(os.path.join(_pp, ".muster-checks", "live.json"))
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
add("3 a PINR worker whose note names the manager is not the manager", run("rules-check.py", "Stop", last_assistant_message="**WORKING · x**\n- a\n- b", transcript_path=mgr_note), False)
# 4 board path (lines style)
write_board("2026-11-08 | NEED | Site_PINR_002 -> Manager | token wording", "2026-11-08 | LIVE | Look Header_PINR_002 -> Manager | Paused: yes | fix live")  # file order: oldest first
bs = lambda said, t=mgr, **k: run("board-stop.py", "Stop", last_assistant_message=said, transcript_path=t, **k)
add("4 a chat whose last line says Paused: yes reaches the manager", bs("Fine."), True)
add("4 naming that chat clears it", bs("Relayed his answer to Look Header_PINR_002."), False)
add("4 an old NEED line is not nagged (no closing mark exists)", (write_board("2026-11-08 | NEED | Site_PINR_002 -> Manager | x") or bs("Fine.")), False)
add("4 a later line from the same chat clears a pause", (write_board("2026-11-08 | LIVE | Look Header_PINR_002 -> Manager | Paused: yes | fix", "2026-11-08 | DONE | Look Header_PINR_002 -> Manager | next thing") or bs("Fine.")), False)
add("4 a pause followed by a later line (no Paused word) from the same chat is cleared, a later 'Paused: no' too", (write_board("2026-11-07 | LIVE | Manager_PINR_002 -> Site | Paused: yes | x", "2026-11-08 | NEED | Look Header_PINR_002 -> Manager | Paused: yes | y", "2026-11-08 | RESUMED | Look Header_PINR_002 -> Manager | Paused: no | y", "2026-11-09 | DONE | Manager_PINR_002 -> Site | ok") or bs("Fine.")), False)
add("4 a pause that is a chat's latest line still counts when others wrote after it", (write_board("2026-11-08 | LIVE | Look Header_PINR_002 -> Manager | Paused: yes | x", "2026-11-09 | DONE | Site_PINR_002 -> Manager | later") or bs("Fine.")), True)
# 81: the same open item is said once; a worker's next message does not make the manager say it again
ST = tempfile.mkdtemp(dir=T)
PA = "2026-11-08 | LIVE | Look Header_PINR_002 -> Manager | Paused: yes | x"
add("4b the first stop with a paused chat unmentioned blocks", (write_board(PA) or bs("Fine.", state=ST)), True)
add("4b the next stop (a worker's message started the turn) with the same pause passes silently", bs("Fine.", state=ST), False)
add("4b a changed line for that chat is said again", (write_board(PA + " changed") or bs("Fine.", state=ST)), True)
add("4b a different chat's pause is new", (write_board(PA + " changed", "2026-11-08 | LIVE | Site_PINR_002 -> Manager | Paused: yes | y") or bs("Fine.", state=ST)), True)
add("4b ...and then silent again for both", bs("Fine.", state=ST), False)
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
# item 93: the Muster folder runs its checks live from .muster-checks; a builder's linked worktree under it has no such copy, so the plugin's own checks must still run there
WT = os.path.join(PROJ, ".claude", "worktrees", "wt1")
os.makedirs(os.path.join(WT, "sub"))
open(os.path.join(WT, ".git"), "w").write("gitdir: /x/.git/worktrees/wt1\n")
add("6 item 93: the plugin's rules-check still runs inside a linked worktree under the project", run("rules-check.py", "PreToolUse", plain=True, cwd=WT, tool_name="SendMessage", tool_input={"to": "x", "message": "noted"}, transcript_path=tr("You are Builder A_Muster_003")), True)
add("6 item 93: ...and from a sub-folder of that worktree", run("rules-check.py", "PreToolUse", plain=True, cwd=os.path.join(WT, "sub"), tool_name="SendMessage", tool_input={"to": "x", "message": "noted"}, transcript_path=tr("You are Builder A_Muster_003")), True)
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
card = "**WORKING \u00b7 x**\n- a\n- b"
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
# item 78: "Job: You are Manager_PINR_006, ..." (the profile's crew pattern can swallow "You are " as part of one name)
JY = lambda who: tr("Job:       You are %s, the founder's go-between and record keeper.\nOwns:      manager/\n" % who)
add("8 'Job: You are Manager_PINR_006' is the manager", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=JY("Manager_PINR_006")), True)
add("8 ...and it may write the founder's list", W(C + "/Founder/FOUNDER-LIST.md", JY("Manager_PINR_006")), False)
add("8 'Job: You are Look Inspector_PINR_002' is a worker", run("rules-check.py", "Stop", last_assistant_message=card, transcript_path=JY("Look Inspector_PINR_002")), False)
add("8 ...and it cannot write the founder's list", W(C + "/Founder/FOUNDER-LIST.md", JY("Look Inspector_PINR_002")), True)
# item 80, D-037: no locking choice card for the manager, in PINR too; a worker's tools are not this check's business
AQ = lambda t: run("rules-check.py", "PreToolUse", tool_name="AskUserQuestion", tool_input={"questions": [{"question": "Ship it?", "options": []}]}, transcript_path=t)
add("10 a PINR manager's choice card is refused (lettered lines instead)", AQ(mgr), True)
add("10 a PINR worker's card is not this check's business", AQ(site), False)
add("10 a PINR manager's lettered question passes the Stop check", run("rules-check.py", "Stop", last_assistant_message="**ASK \u00b7 ship**\n\nShip it?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=mgr), False)
LET = tr("You are Manager_PINR_002", [{"type": "assistant", "message": {"content": [{"type": "text", "text": "***A.*** red (my pick)\n\n***B.*** blue"}]}}, {"type": "user", "message": {"content": "a"}}])
letout = run("rules-check.py", "Stop", last_assistant_message="Going ahead.", transcript_path=LET)
add("10 a typed letter in PINR must be recorded", letout, True)
add("10 ...with PINR's own recorder, naming no flag it lacks", "" if "decide.py" in letout and "--no-pick" not in letout else "BAD", False)
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
# item 87: every Stop block says the reply already reached the owner and must not be written again (Python and Rust sources, then live)
import re as _re
NR = "do not write it again"
def nr_sites(path, start, end):
    src = open(os.path.join(ROOT, path), encoding="utf-8").read()
    return [m.start() for m in _re.finditer(start, src)], [("NOREPEAT" in src[m.start():src.index(end, m.start())]) for m in _re.finditer(start, src)]
for path in ("hooks/rules-check.py", "hooks/board-stop.py", "hooks/talk-check.py", "scripts/idle-check.py", "scripts/worker-queue-check.py"):
    n, ok = nr_sites(path, r'"decision": "block"', "}))")
    add("87 every Stop block in %s (%d) carries the no-repeat line" % (path, len(n)), "" if n and all(ok) else "BAD %s" % ok, False)
for path in ("checks/src/common.rs", "checks/src/boardstop.rs", "checks/src/talk.rs"):
    n, ok = nr_sites(path, r'\("decision", "block"\.into\(\)\)', "]));")
    add("87 every Stop block in %s (%d) carries the no-repeat line" % (path, len(n)), "" if n and all(ok) else "BAD %s" % ok, False)
add("87 a live rules-check block says so", "" if NR in letout else "BAD", False)
add("87 a live board-stop block says so", "" if NR in (write_board("2026-11-08 | LIVE | Look Header_PINR_002 -> Manager | Paused: yes | fix") or bs("Fine.")) else "BAD", False)
add("87 a live talk-check block says so", "" if NR in run("talk-check.py", "Stop", plain=True, last_assistant_message=bare, transcript_path=tr("You are Builder A_Muster_003")) else "BAD", False)
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
# box-check-pinr: a re-install over an old PreToolUse matcher (no wrap_up) refreshes it in place and keeps the project's own hooks
IC2 = os.path.join(T, "ic2"); os.makedirs(os.path.join(IC2, ".claude"))
json.dump({"model": "x", "hooks": {"PreToolUse": [
    {"matcher": "SendMessage|Write|Edit|NotebookEdit|Bash", "hooks": [{"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/.muster-checks/rules-check.py"'}]},
    {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo mine"}]}]}}, open(os.path.join(IC2, ".claude", "settings.json"), "w"))
ic(IC2, "--profile", "pinr")
_st2 = json.load(open(os.path.join(IC2, ".claude", "settings.json")))
_pre = _st2["hooks"]["PreToolUse"]
_mine = [g for g in _pre if any("echo mine" in h["command"] for h in g["hooks"])]
_ours = [g for g in _pre if any("rules-check.py" in h["command"] for h in g["hooks"])]
add("box-check-pinr: a re-install over the old matcher adds wrap_up, once, and keeps the project's own hook and settings", "" if len(_ours) == 1 and "mcp__ccd_turn__wrap_up" in _ours[0]["matcher"] and len(_mine) == 1 and _st2.get("model") == "x" else "BAD " + json.dumps(_pre), False)
# item 86: install-checks --profile pinr puts Muster's PINR recorder in place of PINR's own, and decide.py takes a typed letter or line
RP = os.path.join(T, "rec")
os.makedirs(os.path.join(RP, "manager"))
os.makedirs(os.path.join(RP, "Founder"))
os.makedirs(os.path.join(RP, "PINR-claudecode-handoff", "pinr-claude-code-starter-v2"))
RLOG = os.path.join(RP, "PINR-claudecode-handoff", "pinr-claude-code-starter-v2", "DECISIONS-LOG.md")
open(RLOG, "w").write("# log\n\n**719. Old (founder, 2026-11-14: \"x\", to M's question q).** b\n")
open(os.path.join(RP, "Founder", "FOUNDER-LIST.md"), "w").write("## Open\n\n1. \"whatever muster manager tells you to do.\" (U031)\n   Kind: order\n\n2. \"red please\"\n   Kind: order\n")
OLD = "#!/usr/bin/env python3\n# PINR's own old recorder\n"
open(os.path.join(RP, "manager", "decide.py"), "w").write(OLD)
ic(RP, "--profile", "pinr")
ic(RP, "--profile", "pinr")
DP = os.path.join(RP, "manager", "decide.py")
add("item 86: install put the PINR recorder in place, kept PINR's own once", "" if "for PINR's layout" in open(DP).read() and open(os.path.join(RP, ".muster-checks", "recorder.before")).read() == OLD else "BAD", False)
dec = lambda *a: subprocess.run([PY, DP, "--title", "T", "--question", "Q?", *a], capture_output=True, text=True)
r = dec("--said", "b", "--chose", "B. blue")
add("item 86: his bare typed letter is recorded", "" if r.returncode == 0 and r.stdout.strip() == "720" else "BAD " + r.stderr, False)
r = dec("--said", "whatever muster manager tells you to do.", "--item", "1")
add("item 86: 'whatever muster manager tells you to do.' is recorded as a handover, proved on item 1", "" if r.returncode == 0 and r.stdout.strip() == "721" and "handed the choice to muster manager" in open(RLOG).read() else "BAD " + r.stderr, False)
add("item 86: ...but not under an item that does not quote it", "" if dec("--said", "whatever muster manager tells you to do.", "--item", "2").returncode == 1 else "BAD", False)
add("item 86: a hedged line is still refused", "" if dec("--said", "blue or green, whatever", "--chose", "blue").returncode == 1 else "BAD", False)
add("item 86: a line that does not name the choice is refused", "" if dec("--said", "make it nice", "--chose", "blue").returncode == 1 else "BAD", False)
add("item 86: a handover line that also hedges is refused", "" if dec("--said", "whatever muster manager tells you to do or maybe not").returncode == 1 else "BAD", False)
r = dec("--said", "make the header blue", "--chose", "blue")
add("item 86: a whole clear line naming the choice is recorded", "" if r.returncode == 0 else "BAD " + r.stderr, False)
import re
_rec = [l for l in open(RLOG).read().splitlines() if "Recorded as:" in l]
add("PINR rule 21: every recorded line says 'the founder', never he, him or his", "" if _rec and all("the founder" in l and not re.search(r"\b(he|him|his)\b", l.split("Recorded as:")[1], re.I) for l in _rec) else "BAD " + str(_rec[-2:]), False)
add("PINR rule 21: decide's own help text never says he, him or his", "" if not re.search(r"\b(he|him|his)\b", subprocess.run([PY, DP, "--help"], capture_output=True, text=True).stdout, re.I) else "BAD", False)
ic(RP)
add("item 86: removing the checks puts PINR's own recorder back", "" if open(DP).read() == OLD else "BAD", False)
# item 90: --live puts small stand-ins in the project that run the checks from the Muster folder, so a Muster change reaches it with no re-install
LM = os.path.join(T, "muster-live")
for d in ("hooks", "scripts", "profiles"):
    shutil.copytree(os.path.join(ROOT, d), os.path.join(LM, d))
LP = os.path.join(T, "liveproj")
os.makedirs(os.path.join(LP, "manager"))
os.makedirs(os.path.join(LP, "PINR-claudecode-handoff", "pinr-claude-code-starter-v2"))
os.makedirs(os.path.join(LP, "Founder"))
open(os.path.join(LP, "PINR-claudecode-handoff", "pinr-claude-code-starter-v2", "DECISIONS-LOG.md"), "w").write("# log\n\n**5. Old (founder, d: \"x\", to M's question q).** b\n")
open(os.path.join(LP, "manager", "decide.py"), "w").write(OLD)
icl = lambda *a: subprocess.run([PY, os.path.join(ROOT, "scripts", "install-checks.py"), *a], capture_output=True, text=True)
add("item 90: --live refuses a folder that is not a Muster folder", "" if icl(LP, "--profile", "pinr", "--live", os.path.join(T, "nope")).returncode == 1 else "BAD", False)
dl = icl(LP, "--profile", "pinr", "--live", LM, "--dry-run")
add("item 90: --live --dry-run writes nothing", "" if dl.returncode == 0 and not os.path.exists(os.path.join(LP, ".muster-checks")) and "stand-ins" in dl.stdout else "BAD " + dl.stdout, False)
il = icl(LP, "--profile", "pinr", "--live", LM)
icl(LP, "--profile", "pinr", "--live", LM)
LC = os.path.join(LP, ".muster-checks")
add("item 90: --live installs stand-ins, not copies, and live.json names the Muster folder", "" if il.returncode == 0 and "MUSTER-LIVE-STANDIN" in open(os.path.join(LC, "rules-check.py"), encoding="utf-8").read() and json.load(open(os.path.join(LC, "live.json")))["muster"] == LM else "BAD " + il.stdout + il.stderr, False)
add("item 90: the recorder is a stand-in too, PINR's own kept once", "" if "MUSTER-LIVE-STANDIN" in open(os.path.join(LP, "manager", "decide.py"), encoding="utf-8").read() and open(os.path.join(LC, "recorder.before")).read() == OLD else "BAD", False)
lstop = lambda said, tp: subprocess.run([PY, os.path.join(LC, "rules-check.py")], input=json.dumps(dict(hook_event_name="Stop", cwd=LP, last_assistant_message=said, transcript_path=tp)), capture_output=True, text=True, env=dict(ENV, CLAUDE_PROJECT_DIR=LP)).stdout.strip()
lpre = subprocess.run([PY, os.path.join(LC, "rules-check.py")], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=LP, tool_name="AskUserQuestion", tool_input={"questions": [{"question": "Ship it?", "options": []}]}, transcript_path=mgr)), capture_output=True, text=True, env=dict(ENV, CLAUDE_PROJECT_DIR=LP)).stdout
add("item 90: the stand-in applies PINR's profile (a PINR manager's choice card is refused)", "" if "Muster rule" in lpre else "BAD " + lpre[:200], False)
# change a check in the Muster folder: the project runs the new code with no re-install
rcp = os.path.join(LM, "hooks", "rules-check.py")
src = open(rcp, encoding="utf-8").read()
open(rcp, "w", encoding="utf-8", newline="").write(src.replace("def main():", "def main():\n    print('LIVE-CHANGE-SEEN'); return", 1) if "def main():" in src else src + "\nprint('LIVE-CHANGE-SEEN')\n")
seen = subprocess.run([PY, os.path.join(LC, "rules-check.py")], input="{}", capture_output=True, text=True, env=dict(ENV, CLAUDE_PROJECT_DIR=LP)).stdout
add("item 90: a change in the Muster folder reaches the project with no re-install", "" if "LIVE-CHANGE-SEEN" in seen else "BAD " + seen[:200], False)
open(rcp, "w", encoding="utf-8", newline="").write(src)
# the recorder stand-in records under the project's own log
rd = subprocess.run([PY, os.path.join(LP, "manager", "decide.py"), "--title", "T", "--question", "Q?", "--said", "b", "--chose", "B"], capture_output=True, text=True)
add("item 90: the recorder stand-in records in the project's own log", "" if rd.returncode == 0 and rd.stdout.strip() == "6" else "BAD " + rd.stdout + rd.stderr, False)
# a missing Muster folder is said plainly, never silently
shutil.move(LM, LM + ".gone")
miss = subprocess.run([PY, os.path.join(LC, "rules-check.py")], input="{}", capture_output=True, text=True, env=dict(ENV, CLAUDE_PROJECT_DIR=LP))
add("item 90: a missing Muster folder is said plainly by a hook and lets the turn go on", "" if miss.returncode == 0 and LM in json.loads(miss.stdout).get("systemMessage", "") and "decision" not in json.loads(miss.stdout) else "BAD " + miss.stdout, False)
missr = subprocess.run([PY, os.path.join(LP, "manager", "decide.py"), "--title", "T", "--question", "Q?", "--said", "b", "--chose", "B"], capture_output=True, text=True)
add("item 90: ...and a recorder stops with the same plain message", "" if missr.returncode == 1 and LM in missr.stderr else "BAD " + missr.stderr, False)
shutil.move(LM + ".gone", LM)
icl(LP)
add("item 90: install without --live puts plain copies back and removes live.json", "" if "MUSTER-LIVE-STANDIN" not in open(os.path.join(LC, "rules-check.py"), encoding="utf-8").read() and not os.path.exists(os.path.join(LC, "live.json")) else "BAD", False)
rf = os.path.join(T, "r.txt")
open(rf, "w").write(pinr_report)
cr = lambda *a: subprocess.run([PY, os.path.join(ROOT, "scripts", "check-report.py"), *a], capture_output=True, text=True).returncode
add("check-report --profile pinr accepts a PINR report", "" if cr(rf, "--profile", "pinr") == 0 else "BAD", False)
add("check-report without a profile still wants the ID", "" if cr(rf) == 1 else "BAD", False)

# item 99: renewal by size, and the summary hook's crew names come from the project's profile
def bigt(n): return {"type": "assistant", "message": {"content": [{"type": "text", "text": "x"}], "usage": {"input_tokens": 5, "cache_read_input_tokens": n - 5000, "cache_creation_input_tokens": 4995}}}
card99 = "**WORKING \u00b7 x**\n- a\n- b"
add("item 105: a PINR-named worker over 300000 tokens is not told to renew (it compacts in place)", run("rules-check.py", "Stop", cwd=PROJ, last_assistant_message=card99, transcript_path=tr("You are Site_PINR_002. Job: Site_PINR_002, builds the site.", [bigt(600000)])), False)
add("item 99: a PINR-named worker under the line is silent", run("rules-check.py", "Stop", cwd=PROJ, last_assistant_message=card99, transcript_path=tr("You are Site_PINR_002. Job: Site_PINR_002, builds the site.", [bigt(120000)])), False)
rs = lambda first, prof=True: subprocess.run([PY, os.path.join(ROOT, "hooks", "renew-after-summary.py")], input=json.dumps({"transcript_path": tr(first)}), capture_output=True, text=True,
                                            env=dict(ENV, **({"MUSTER_PROFILE": os.path.join(ROOT, "profiles", "pinr.json")} if prof else {}))).stdout
add("item 99: after a compaction a PINR-named chat is told it was compacted in place (crew names from the profile)", "" if "compacted in place" in rs("You are Site_PINR_002. Job: Site_PINR_002, builds the site.") else "BAD", False)
add("item 99: ...and PINR's manager gets the manager's note", "" if "compacted in place" in rs("You are Manager_PINR_008. Job: Manager_PINR_008.") else "BAD", False)
add("item 99: ...without the profile a PINR-named chat is not crew to the hook", "" if rs("You are Site_PINR_002. Job: Site_PINR_002, builds the site.", False) == "" else "BAD", False)
add("item 99: the owner's own chat is silent for the hook", "" if rs("hello there") == "" else "BAD", False)
# item 93: the Muster folder runs its own checks live; the plugin's own shell hooks stand down only for a check the folder really installed, and not inside a worktree
MP = os.path.join(T, "musterproj")
os.makedirs(os.path.join(MP, "muster")); open(os.path.join(MP, "muster", "CLAUDE.md"), "w").write("# rules\n")
os.makedirs(os.path.join(MP, ".muster-checks")); open(os.path.join(MP, ".muster-checks", "profile.json"), "w").write('{"message_form": "text"}')
MWT = os.path.join(MP, ".claude", "worktrees", "b1"); os.makedirs(MWT); open(os.path.join(MWT, ".git"), "w").write("gitdir: /x\n")
shsend = lambda cwd: subprocess.run(["sh", os.path.join(LM, "hooks", "rules-check.sh")], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=cwd, tool_name="SendMessage", tool_input={"to": "x", "message": "noted"}, transcript_path=tr("You are Builder A_Muster_003"))), capture_output=True, text=True, cwd=cwd, env=dict(ENV, MUSTER_MESSAGE_FORM="text")).stdout
add("item 93: a profile-only .muster-checks does not silence the plugin's shell hook", "" if "Muster rule" in shsend(MP) else "BAD", False)
imp = icl(MP, "--profile", "muster", "--live", LM)
add("item 93: the Muster profile installs live and the hook matcher covers cards, helpers and chat starts", "" if imp.returncode == 0 and all(w in open(os.path.join(MP, ".claude", "settings.json")).read() for w in ("AskUserQuestion", "mcp__ccd_session__start_session", "Agent")) else "BAD " + imp.stdout + imp.stderr, False)
add("item 93: with the live stand-in installed the plugin's shell hook stands down in the main folder", "" if shsend(MP) == "" else "BAD " + shsend(MP)[:100], False)
add("item 93: ...but not inside a builder's linked worktree under it", "" if "Muster rule" in shsend(MWT) else "BAD", False)
# item 94: a renewed manager is found live in the crew list the project's profile names; a worktree runs the main folder's live copy of a check
os.makedirs(os.path.join(PROJ, "manager"), exist_ok=True)
OLDM, NEWM, SITEM = "local_" + "x07-made-up", "local_" + "x08-made-up", "local_" + "x04-made-up"
open(os.path.join(PROJ, "manager", "CREW-SESSIONS.md"), "w").write("| Manager_PINR_007 | " + OLDM + " | old |\n| Manager_PINR_008 | " + NEWM + " | renewed 14 Nov |\n| Site_PINR_004 | " + SITEM + " | site |\n")
card94 = "**READY \u00b7 x**\n- a\n- b"
snd = lambda to: tr("You are PINRai_teacher_003.", [use("SendMessage", to=to, message="m")])
add("item 94: a report card after a message to the renewed manager's id passes", run("rules-check.py", "Stop", cwd=PROJ, last_assistant_message=card94, transcript_path=snd("" + NEWM + "")), False)
add("item 94: ...and by his name too", run("rules-check.py", "Stop", cwd=PROJ, last_assistant_message=card94, transcript_path=snd("Manager_PINR_008")), False)
add("item 94: a message to a site chat's id is not a message to the manager", run("rules-check.py", "Stop", cwd=PROJ, last_assistant_message=card94, transcript_path=snd("" + SITEM + "")), True)
# the installed hook command: from a worktree it runs the MAIN folder's copy, not the old one carried in the worktree
if shutil.which("git"):
    GM = os.path.join(T, "gitmain"); os.makedirs(os.path.join(GM, ".muster-checks"))
    gg = lambda *a, cwd=GM: subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=t", *a], cwd=cwd, capture_output=True, text=True)
    gg("init", "-q"); open(os.path.join(GM, "x"), "w").write("x"); gg("add", "x"); gg("commit", "-qm", "x")
    GW = os.path.join(T, "gitwt"); gg("worktree", "add", "-q", GW)
    os.makedirs(os.path.join(GW, ".muster-checks"), exist_ok=True)
    open(os.path.join(GM, ".muster-checks", "rules-check.py"), "w").write("print('LIVE-MAIN')\n")
    open(os.path.join(GW, ".muster-checks", "rules-check.py"), "w").write("print('OLD-IN-WORKTREE')\n")
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import importlib.util as _u
    _sp = _u.spec_from_file_location("ic94", os.path.join(ROOT, "scripts", "install-checks.py")); _ic = _u.module_from_spec(_sp); _sp.loader.exec_module(_ic)
    hk = lambda proj: subprocess.run(["sh", "-c", _ic.cmd("rules-check.py")], capture_output=True, text=True, cwd=proj, env=dict(ENV, CLAUDE_PROJECT_DIR=proj)).stdout.strip()
    add("item 94: a worktree's hook runs the main folder's live copy, not the old one in the worktree", "" if hk(GW) == "LIVE-MAIN" else "BAD " + hk(GW), False)
    add("item 94: the main folder's hook runs its own copy", "" if hk(GM) == "LIVE-MAIN" else "BAD " + hk(GM), False)
    os.makedirs(os.path.join(T, "nogit", ".muster-checks")); open(os.path.join(T, "nogit", ".muster-checks", "rules-check.py"), "w").write("print('OWN')\n")
    add("item 94: a folder that is not a git folder runs its own copy", "" if hk(os.path.join(T, "nogit")) == "OWN" else "BAD", False)

LCS = json.load(open(os.path.join(MP, ".claude", "settings.json"))).get("hooks", {}).get("SessionStart", [])
add("item 99: the install adds the summary hook (SessionStart, compact)", "" if any(g.get("matcher") == "compact" and "renew-after-summary.py" in json.dumps(g) for g in LCS) else "BAD", False)
add("item 99: with the live stand-in installed the plugin's summary hook stands down in the main folder, not in a worktree", "" if subprocess.run(["sh", os.path.join(LM, "hooks", "renew-after-summary.sh")], input="{}", capture_output=True, text=True, cwd=MP).stdout == "" else "BAD", False)

# item 105 (D-039): a crew chat about to compact in place leaves its job, branch, saved version and next step on the board
LPC = json.load(open(os.path.join(MP, ".claude", "settings.json"))).get("hooks", {}).get("PreCompact", [])
add("item 105: the install adds the PreCompact hook", "" if any("precompact-board.py" in json.dumps(g) for g in LPC) else "BAD", False)
_pc = os.path.join(T, "pcproj"); os.makedirs(os.path.join(_pc, "muster"))
open(os.path.join(_pc, "muster", "BOARD.md"), "w").write("# Board\n")
_job = {"type": "user", "message": {"content": '{"v":1,"kind":"ORDER","job":"approval-relay","note":"ship approval-relay next"}'}}
def _pre(first, extra=()):
    return subprocess.run([PY, os.path.join(ROOT, "hooks", "precompact-board.py")], input=json.dumps({"transcript_path": tr(first, list(extra)), "cwd": _pc}), capture_output=True, text=True,
                          env=dict(ENV, MUSTER_PROFILE=os.path.join(ROOT, "profiles", "pinr.json"))).returncode
_pre("You are Site_PINR_002. Job: Site_PINR_002, builds the site.", [_job])
_b = open(os.path.join(_pc, "muster", "BOARD.md")).read()
add("item 105: a crew chat's board entry names the chat, its job and its next step", "" if "Site_PINR_002 -> Manager | compaction" in _b and "approval-relay" in _b and "ship approval-relay next" in _b and "Status: done" in _b else "BAD", False)
_n = _b.count("compaction")
add("item 105: the owner's own chat leaves nothing on the board", "" if _pre("hello there") == 0 and open(os.path.join(_pc, "muster", "BOARD.md")).read().count("compaction") == _n else "BAD", False)
add("item 105: a chat with no board leaves nothing and never blocks", "" if subprocess.run([PY, os.path.join(ROOT, "hooks", "precompact-board.py")], input=json.dumps({"transcript_path": tr("You are Site_PINR_002. Job: Site_PINR_002, builds the site."), "cwd": os.path.join(T, "nope")}), capture_output=True, text=True, env=dict(ENV, MUSTER_PROFILE=os.path.join(ROOT, "profiles", "pinr.json"))).returncode == 0 else "BAD", False)

# item 102: crew-plan.py trim keeps unused tool servers out of a crew copy's first call
_wt = os.path.join(T, "wt-trim"); os.makedirs(_wt); open(os.path.join(_wt, ".git"), "w").write("gitdir: x\n")
_main = os.path.join(T, "main-trim"); os.makedirs(os.path.join(_main, ".git"))
def _trim(role, folder):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "crew-plan.py"), "trim", role, folder, "--profile", os.path.join(ROOT, "profiles", "muster.json")], capture_output=True, text=True)
    return r.returncode, r.stdout
_rc, _ = _trim("Builder A_Muster_002", _wt)
cases.append(("item 105: a crew copy compacts in place at 200000 tokens", "" if json.load(open(os.path.join(_wt, ".claude", "settings.local.json"))).get("autoCompactWindow") == 200000 else "x", False))
_wm = os.path.join(T, "wt-mgr"); os.makedirs(_wm); open(os.path.join(_wm, ".git"), "w").write("gitdir: x\n")
_trim("Manager_Muster_001", _wm)
cases.append(("item 113: a manager copy compacts in place at 250000 tokens", "" if json.load(open(os.path.join(_wm, ".claude", "settings.local.json"))).get("autoCompactWindow") == 250000 else "x", False))
_pm = os.path.join(T, "pin-main"); os.makedirs(os.path.join(_pm, ".claude")); open(os.path.join(_pm, ".claude", "settings.local.json"), "w").write('{"model": "x"}')
def _pin(role, folder, prof):
    return subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "crew-plan.py"), "pin-compact", role, folder, "--profile", os.path.join(ROOT, "profiles", prof)], capture_output=True, text=True)
_pin("Manager_PINR_001", _pm, "pinr.json"); _pj = json.load(open(os.path.join(_pm, ".claude", "settings.local.json")))
cases.append(("item 113: pin-compact sets a manager's main folder to 250000 and keeps its other settings", "" if _pj.get("autoCompactWindow") == 250000 and _pj.get("model") == "x" else "x", False))
_pw = os.path.join(T, "pin-worker"); os.makedirs(_pw); _pin("Builder A_PINR_003", _pw, "pinr.json")
cases.append(("item 113: pin-compact pins a worker folder to 200000", "" if json.load(open(os.path.join(_pw, ".claude", "settings.local.json"))).get("autoCompactWindow") == 200000 and "permissions" not in json.load(open(os.path.join(_pw, ".claude", "settings.local.json"))) else "x", False))
_deny = json.load(open(os.path.join(_wt, ".claude", "settings.local.json")))["permissions"]["deny"]
cases.append(("item 102: a builder copy leaves the browser, simulator and blockchain tools out", "" if _rc == 0 and "mcp__Claude_Browser" in _deny and "mcp__BlockchainQuery" in _deny else "x", False))
_wt2 = os.path.join(T, "wt-trim2"); os.makedirs(_wt2); open(os.path.join(_wt2, ".git"), "w").write("gitdir: x\n")
_trim("Designer_Muster_002", _wt2)
_deny2 = json.load(open(os.path.join(_wt2, ".claude", "settings.local.json")))["permissions"]["deny"]
cases.append(("item 102: a designer copy keeps the tools that show a page", "" if "mcp__Claude_Browser" not in _deny2 and "mcp__BlockchainQuery" in _deny2 else "x", False))
_rc3, _ = _trim("Manager_Muster_002", _main)
cases.append(("item 102: the main folder (the owner's own chats) is never trimmed", "" if _rc3 == 1 and not os.path.exists(os.path.join(_main, ".claude")) else "x", False))
_trim("Builder A_Muster_002", _wt)
_deny4 = json.load(open(os.path.join(_wt, ".claude", "settings.local.json")))["permissions"]["deny"]
cases.append(("item 102: running it twice does not repeat a name", "" if len(_deny4) == len(set(_deny4)) else "x", False))

bad = 0
for name, out, should_block in cases:
    ok = bool(out) == should_block
    bad += not ok
    print(("ok   " if ok else "MISS ") + name + ("" if ok else "  -> " + out[:200]))
print("%d of %d passed" % (len(cases) - bad, len(cases)))
shutil.rmtree(T, ignore_errors=True)
sys.exit(1 if bad else 0)
