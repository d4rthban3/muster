#!/usr/bin/env python3
"""Self-test for hooks/rules-check.py: feeds it pretend hook events and checks it blocks what the rules forbid and
stays silent on what they allow. Prints 'N of M passed'; exit 1 on any miss. Standard library only."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "..", "hooks", "rules-check.py")
BIN = os.environ.get("MUSTER_CHECKS_BIN")  # run the same cases against the ready-built Rust copy
RUN_ENV = dict(os.environ, MUSTER_MESSAGE_FORM="text")  # these cases are the older text shapes
T = tempfile.mkdtemp()


def tr(first, extra=()):
    p = os.path.join(T, "t%d.jsonl" % len(os.listdir(T)))
    with open(p, "w") as f:
        f.write(json.dumps({"type": "user", "message": {"content": first}}) + "\n")
        for e in extra:
            f.write(json.dumps(e) + "\n")
    return p


def use(name, _id=None, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": _id, "name": name, "input": inp}]}}


def res(tid, text="sent", err=False):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "is_error": err, "content": text}]}}


def said(text):
    return {"type": "user", "message": {"content": text}}


def run(ev, **kw):
    r = subprocess.run([BIN, "rules"] if BIN else [sys.executable, HOOK], input=json.dumps(dict(hook_event_name=ev, cwd=T, **kw)), capture_output=True, text=True, env=RUN_ENV)
    return r.stdout.strip()


b = tr("You are Builder A_Muster_002, agents/builder.md")
m = tr("You are Manager_Muster_002")
owner = tr("hello there")
good = "READY: x [ID builder-x-1]\nWhat: a\nWhere: b; touches: none\nWhy: c\nHow: 3/3 passed\nNeed: nothing\nUsage: n"
order = "To: B\nJob: j\nOwner's words: \"do it now\"\nOwns: a\nOut: b\nDone: c"
send = lambda msg, t, to="x": run("PreToolUse", tool_name="SendMessage", tool_input={"to": to, "message": msg}, transcript_path=t)
cases = [
    ("a good READY goes through", send(good, b), False),
    ("a reply of 'noted' is refused", send("noted", b), True),
    ("'noted, thanks' is refused", send("noted, thanks", b), True),
    ("'Got it. Thanks and will do!' is refused", send("Got it. Thanks and will do!", b), True),
    ("a real message that starts with 'ok' is not called social", "BAD" if "no 'noted'" in send("ok, I will start the build now and report when the test passes", b) else "", False),
    ("a free-form message is refused", send("hey, can you look at this?", b), True),
    ("a READY with no test count is refused", send(good.replace("3/3 passed", "fine"), b), True),
    ("an order that quotes his words goes through", send(order, m), False),
    ("an order without his words quoted is refused", send(order.replace('"do it now"', "do it now"), m), True),
    ("an ID sent twice is refused", send(good, tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good), res("s1")])), True),
    ("a sibling send in the same turn (no result yet) does not use up the ID", send(good, tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good)])), False),
    ("the call's own copy in the transcript does not use up its ID", send(good, tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good)])), False),
    ("a refused send does not use up its ID", send(good, tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good), res("s1", "Muster rule: this report is wrong", True)])), False),
    ("a send that failed in the app does not use up its ID", send(good, tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good), res("s1", "could not deliver", True)])), False),
    ("two parallel sends with different IDs both go through", send(good.replace("x-1", "x-2").replace("builder-x-1", "builder-x-2"), tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good), use("SendMessage", "s2", message=good.replace("builder-x-1", "builder-x-2"))])), False),
    ("a PASS copy to the manager as a message is refused", send(good.replace("READY", "PASS").replace("Usage: n", "") .replace("\n\n", "\n").strip(), b, "Manager_Muster_002"), True),
    ("the owner's own chat is never touched", send("noted", owner), False),
    ("a worker cannot write the owner's list", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/p/muster/OWNERS-LIST.md"}, transcript_path=b), True),
    ("the manager can write the owner's list", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/p/muster/OWNERS-LIST.md"}, transcript_path=m), False),
    ("nobody commits muster/", run("PreToolUse", tool_name="Bash", tool_input={"command": "git add muster/BOARD.md"}, transcript_path=m), True),
    ("pushing a muster/ branch goes through", run("PreToolUse", tool_name="Bash", tool_input={"command": "git push -u origin muster/builder-a-002-code"}, transcript_path=b), False),
    ("a commit message naming muster/ goes through", run("PreToolUse", tool_name="Bash", tool_input={"command": "git commit -m \"see muster/BOARD.md\""}, transcript_path=b), False),
    ("a worker whose note only names the manager is not the manager", run("Stop", last_assistant_message="**READY \u00b7 x**\n- a\n- b", transcript_path=tr("Job: Builder A_Muster_002: builds. Reports go to Manager_Muster_002 (agents/builder.md)")), False),
    ("a worker told 'report to Manager_Muster_002' before its own name is still a worker", run("Stop", last_assistant_message="**READY \u00b7 x**\n- a\n- b", transcript_path=tr("Report to Manager_Muster_002 when done. You are Builder A_Muster_003, builds.")), False),
    ("the manager named by 'You are' is the manager", run("Stop", last_assistant_message="**READY \u00b7 x**\n- a\n- b", transcript_path=tr("Welcome. You are Manager_Muster_003, the go-between. Builders: Builder A_Muster_003")), True),
    ("a summarized Muster manager ('I am **Manager_Muster_003**') is still the manager", run("Stop", last_assistant_message="**READY \u00b7 x**\n- a\n- b", transcript_path=tr("This session is being continued. Summary: I am **Manager_Muster_003**, the go-between.")), True),
    ("an accented project's manager is still the manager", run("Stop", last_assistant_message="All done, nice.", transcript_path=tr("You are Manager_P\u00e2tisserie_001")), True),
    ("an accented project's builder is a worker", run("Stop", last_assistant_message="**READY \u00b7 x**\n- a\n- b", transcript_path=tr("You are Builder A_P\u00e2tisserie_001. Report to Manager_P\u00e2tisserie_001.")), False),
    ("...and cannot write the owner's list", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/p/muster/OWNERS-LIST.md"}, transcript_path=tr("Job: Builder A_Muster_002: builds. Reports go to Manager_Muster_002")), True),
    ("an ordinary command goes through", run("PreToolUse", tool_name="Bash", tool_input={"command": "git status"}, transcript_path=b), False),
    ("a manager reply that is not a question is blocked", run("Stop", last_assistant_message="All done, nice.", transcript_path=m), True),
    ("nothing waits and he typed a question: a plain answer passes", run("Stop", last_assistant_message="Yes, it is shipped.", transcript_path=tr("You are Manager_Muster_002", [said("well?")])), False),
    ("his question was answered earlier, then a plain statement: blocked", run("Stop", last_assistant_message="Yes, it is shipped.", transcript_path=tr("You are Manager_Muster_002", [said("well?"), said("ok thanks")])), True),
    ("his question, a reply, then a worker's READY starts a new turn: narration blocked", run("Stop", last_assistant_message="Builder A finished the READY and it passed.", transcript_path=tr("You are Manager_Muster_002", [said("well?"), use("Bash", "b1", command="ls"), res("b1", "x"), said("<cross-session-message from=\"b\">READY: x [ID b-1]</cross-session-message>")])), True),
    ("his question with tool calls in the same turn still counts", run("Stop", last_assistant_message="Yes, it is shipped.", transcript_path=tr("You are Manager_Muster_002", [said("well?"), use("Bash", "b1", command="ls"), res("b1", "x")])), False),
    ("a question mark from another chat is not his", run("Stop", last_assistant_message="Yes, it is shipped.", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"x\">is it done?</cross-session-message>")])), True),
    ("his question, then hook feedback inside his turn: the answer still passes", run("Stop", last_assistant_message="Yes, it is shipped.", transcript_path=tr("You are Manager_Muster_002", [said("well?"), said("Stop hook feedback: rewrite it"), said("<system-reminder>note</system-reminder>")])), False),
    ("his question, then an app event (task notification): narration blocked", run("Stop", last_assistant_message="The task finished.", transcript_path=tr("You are Manager_Muster_002", [said("well?"), said("<system-reminder>[SYSTEM NOTIFICATION] <task-notification>x</task-notification></system-reminder>")])), True),
    ("a question mark in hook feedback or a system note is not his", run("Stop", last_assistant_message="Yes, it is shipped.", transcript_path=tr("You are Manager_Muster_002", [said("[SYSTEM NOTIFICATION - NOT USER INPUT] ready?"), said("Stop hook feedback: really?")])), True),
    ("a manager question with buttons passes", run("Stop", last_assistant_message="Which one: A or B? Pick a button.", transcript_path=m), False),
    ("a manager idle line passes", run("Stop", last_assistant_message="The crew is idle. Here's what's next.", transcript_path=m), False),
    ("a manager waiting line passes", run("Stop", last_assistant_message="Builder A is waiting for you: type in Builder A_Muster_002.", transcript_path=m), False),
    ("an unrecorded choice answer blocks the manager", run("Stop", last_assistant_message="ok", transcript_path=tr("You are Manager_Muster_002", [use("AskUserQuestion", questions=[])])), True),
    ("a recorded choice answer passes", run("Stop", last_assistant_message="ok", transcript_path=tr("You are Manager_Muster_002", [use("AskUserQuestion", questions=[]), use("Bash", command="python3 scripts/record-choice.py p 3 --picked A")])), False),
    ("a worker card passes", run("Stop", last_assistant_message="**READY · x**\n- a\n- b", transcript_path=b), False),
    ("a worker reply that is not a card is blocked", run("Stop", last_assistant_message="Done.", transcript_path=b), True),
    ("a stop already continued is let through", run("Stop", last_assistant_message="Done.", stop_hook_active=True, transcript_path=b), False),
    ("the owner's own chat is silent at stop", run("Stop", last_assistant_message="Done.", transcript_path=owner), False),
]
# the message form of the lean rebuild (records): the same cases for the Python copy and the Rust copy, key checks in Rust only
REC = '{"v":1,"kind":"PASS","id":"inspector-x-1","job":"x","from":"inspector","to":"builder-a","sha":"abcdef1","need":"none"}'
def send_rec(msg, to="x", cwd=T):
    env = dict(os.environ); env.pop("MUSTER_MESSAGE_FORM", None)
    r = subprocess.run([BIN, "rules"] if BIN else [sys.executable, HOOK], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=cwd, tool_name="SendMessage", tool_input={"to": to, "message": msg}, transcript_path=b)), capture_output=True, text=True, env=env)
    return r.stdout.strip()
cases += [
    ("RECORDS: a data record goes through", send_rec(REC), False),
    ("RECORDS: a sentence is refused", send_rec("Please check my branch when you can."), True),
    ("RECORDS: the older six-line report is refused", send_rec(good), True),
    ("RECORDS: 'noted' is refused", send_rec("noted"), True),
]
RDY = '{"v":1,"kind":"READY","id":"builder-a-x-1","job":"x","from":"builder-a","to":"inspector","sha":"abcdef1","tests":{"passed":3,"failed":0},"touches":["hooks"],"need":"pass_or_fail","usage":{"week_pct":null}}'
if BIN:
    cases += [
        ("RECORDS: a sentence inside a field is refused", send_rec(REC.replace('"x"', '"please look"', 1)), True),
        ("RECORDS: an unknown key is refused", send_rec(REC.replace('"v":1,', '"v":1,"note":"hi",')), True),
        ("RECORDS: touches naming a real top-level folder goes through", send_rec(RDY, cwd=os.path.join(HERE, "..")), False),
        ("RECORDS: touches that spell a sentence one word per entry are refused", send_rec(RDY.replace('["hooks"]', '["path","uses","backslashes","on","windows"]'), cwd=os.path.join(HERE, "..")), True),
        ("RECORDS: touches naming nothing in the project are refused", send_rec(RDY.replace('["hooks"]', '["nothing-here"]'), cwd=os.path.join(HERE, "..")), True),
        ("RECORDS: a PASS copy for the manager as a message is refused", send_rec(REC, "Manager_Muster_003"), True),
    ]
# the weekly goal: an ORDER whose job is not on the owner's set list waits; setting it again changes it; no goal enforces nothing
GOALPY = os.path.join(HERE, "goal.py")
GD = os.path.join(T, "goalproj"); os.makedirs(GD)
ORD = '{"v":1,"kind":"ORDER","id":"manager-%s-1","job":"%s","from":"manager","to":"builder-a","owner_words":{"item":35},"owns":[],"out":[],"need":"none"}'
def goal(*a):
    return subprocess.run([sys.executable, GOALPY, *a, "--folder", GD], capture_output=True, text=True)
def order(job):
    return send_rec(ORD % (job, job), "builder-a", cwd=GD)
cases.append(("GOAL: with no goal set every order goes through", order("weekly-goal"), False))
goal("set", "--words", "finish muster", "--done", "the crew is live", "--list", "lean-rebuild,weekly-goal", "--parked", "site looks")
cases += [
    ("GOAL: an order on the set list goes through", order("weekly-goal"), False),
    ("GOAL: an order off the set list waits, and the reminder names his goal", "" if "finish muster" not in order("pinr-profile") else order("pinr-profile"), True),
]
goal("set", "--words", "ship the profile", "--done", "pinr is checked", "--list", "pinr-profile")
cases += [
    ("GOAL: after he changes the goal the new list rules", order("pinr-profile"), False),
    ("GOAL: ...and the old job now waits", order("weekly-goal"), True),
]
goal("clear")
cases.append(("GOAL: with the goal dropped every order goes through again", order("weekly-goal"), False))
r = goal("set", "--words", "x", "--list", "Not A Code")
cases.append(("GOAL: a set list entry that is not a code is refused", "" if r.returncode == 2 else "BAD", False))
goal("set", "--words", "finish muster", "--done", "live", "--list", "a-job")
cases.append(("GOAL: show prints his words", "" if "finish muster" in goal("show").stdout else "BAD", False))
cases.append(("GOAL: check says why a job waits", "" if goal("check", "other").returncode == 1 and "set list" in goal("check", "other").stdout else "BAD", False))
# helpers (item 36): a subagent is a side job; it never stands in for a worker, ships, pushes or messages
def helper(t, **inp):
    return run("PreToolUse", tool_name="Agent", tool_input=inp, transcript_path=t)
cases += [
    ("HELPERS: a plain side job goes through", helper(b, prompt="Find where usage.py is read and report the file names."), False),
    ("HELPERS: a builder starting a builder helper is refused", helper(b, subagent_type="muster:builder", prompt="Build it."), True),
    ("HELPERS: a builder starting an inspector helper is refused", helper(b, subagent_type="inspector", prompt="Check it."), True),
    ("HELPERS: the manager's fresh checker (inspector definition) goes through", helper(m, subagent_type="muster:inspector", prompt="Check this READY."), False),
    ("HELPERS: the manager starting a builder helper is refused", helper(m, subagent_type="builder", prompt="Build it."), True),
    ("HELPERS: a brief that asks it to ship is refused", helper(b, prompt="Then run bash scripts/ship.sh \"note\" to ship it."), True),
    ("HELPERS: a brief that asks it to push is refused", helper(b, prompt="Commit and git push the branch."), True),
    ("HELPERS: a brief that forbids shipping goes through", helper(b, prompt="Search the hooks folder. Never run git push or ship.sh."), False),
    ("HELPERS: the owner's own chat is silent", helper(owner, subagent_type="builder", prompt="x"), False),
]
# the board-post script: one six-line entry appended, nothing else; a wrong shape or a key-like value is refused
BP = os.path.join(HERE, "board-post.py")
BD = os.path.join(T, "boardproj"); os.makedirs(os.path.join(BD, "muster"))
open(os.path.join(BD, "muster", "BOARD.md"), "w").write("# Board\n")
def post(**kw):
    a = dict(**{"from": "Builder A_X_001", "to": "Manager_X_001", "word": "READY", "job": "a job", "what": "w", "where": "p; touches: none", "why": "y", "how": "3 of 3", "need": "n"}); a.update(kw)
    cmd = [sys.executable, BP, "--folder", BD] + [x for k, v in a.items() for x in ("--" + k, v)]
    return subprocess.run(cmd, capture_output=True, text=True)
r = post()
board = open(os.path.join(BD, "muster", "BOARD.md")).read()
cases += [
    ("BOARDPOST: a good entry is appended in the six-line shape", "" if r.returncode == 0 and "READY: a job" in board and "Status: open" in board and "Need:  n" in board else "BAD", False),
    ("BOARDPOST: a first word outside the six is refused", "" if post(word="HELLO").returncode == 2 else "BAD", False),
    ("BOARDPOST: a Where line without touches is refused", "" if post(where="p").returncode == 2 else "BAD", False),
    ("BOARDPOST: a line break inside a field is refused", "" if post(why="a\nb").returncode == 2 else "BAD", False),
    ("BOARDPOST: a key-like value is refused", "" if post(how="ghp_" + "a" * 20).returncode == 2 else "BAD", False),
    ("BOARDPOST: a refused entry leaves the board as it was", "" if open(os.path.join(BD, "muster", "BOARD.md")).read().count("###") == 1 else "BAD", False),
]
bad = 0
for name, out, should_block in cases:
    ok = bool(out) == should_block
    bad += not ok
    print(("ok   " if ok else "MISS ") + name)
print("%d of %d passed" % (len(cases) - bad, len(cases)))
sys.exit(1 if bad else 0)
