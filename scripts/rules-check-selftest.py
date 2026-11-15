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


def big(n):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": "x"}], "usage": {"input_tokens": 5, "cache_read_input_tokens": n - 5000, "cache_creation_input_tokens": 4995}}}



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
    ("a PASS copy to the manager as a message goes through (item 65)", send(good.replace("READY", "PASS").replace("Usage: n", "") .replace("\n\n", "\n").strip(), b, "Manager_Muster_002"), False),
    ("the owner's own chat is never touched", send("noted", owner), False),
    ("a worker cannot write the owner's list", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/p/muster/OWNERS-LIST.md"}, transcript_path=b), True),
    ("the manager can write the owner's list", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/p/muster/OWNERS-LIST.md"}, transcript_path=m), False),
    ("nobody commits muster/", run("PreToolUse", tool_name="Bash", tool_input={"command": "git add muster/BOARD.md"}, transcript_path=m), True),
    ("pushing a muster/ branch goes through", run("PreToolUse", tool_name="Bash", tool_input={"command": "git push -u origin muster/builder-a-002-code"}, transcript_path=b), False),
    ("a commit message naming muster/ goes through", run("PreToolUse", tool_name="Bash", tool_input={"command": "git commit -m \"see muster/BOARD.md\""}, transcript_path=b), False),
    ("a worker whose note only names the manager is not the manager", run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", transcript_path=tr("Job: Builder A_Muster_002: builds. Reports go to Manager_Muster_002 (agents/builder.md)")), False),
    ("a worker told 'report to Manager_Muster_002' before its own name is still a worker", run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", transcript_path=tr("Report to Manager_Muster_002 when done. You are Builder A_Muster_003, builds.")), False),
    ("the manager named by 'You are' is the manager", run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", transcript_path=tr("Welcome. You are Manager_Muster_003, the go-between. Builders: Builder A_Muster_003")), True),
    ("a summarized Muster manager ('I am **Manager_Muster_003**') is still the manager", run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", transcript_path=tr("This session is being continued. Summary: I am **Manager_Muster_003**, the go-between.")), True),
    ("an accented project's manager is still the manager", run("Stop", last_assistant_message="All done, nice.", transcript_path=tr("You are Manager_P\u00e2tisserie_001")), True),
    ("an accented project's builder is a worker", run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", transcript_path=tr("You are Builder A_P\u00e2tisserie_001. Report to Manager_P\u00e2tisserie_001.")), False),
    ("...and cannot write the owner's list", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/p/muster/OWNERS-LIST.md"}, transcript_path=tr("Job: Builder A_Muster_002: builds. Reports go to Manager_Muster_002")), True),
    ("an ordinary command goes through", run("PreToolUse", tool_name="Bash", tool_input={"command": "git status"}, transcript_path=b), False),
    ("a manager reply that is not a question is blocked", run("Stop", last_assistant_message="All done, nice.", transcript_path=m), True),
    ("nothing waits and he typed a question: a plain answer passes", run("Stop", last_assistant_message="Yes, it is shipped.", transcript_path=tr("You are Manager_Muster_002", [said("well?")])), False),
    ("his question was answered earlier, then a plain statement: blocked", run("Stop", last_assistant_message="Yes, it is shipped.", transcript_path=tr("You are Manager_Muster_002", [said("well?"), said("ok thanks")])), True),
    ("his question, a reply, then a worker's READY starts a new turn: long narration blocked", run("Stop", last_assistant_message="Builder A finished the READY and it passed, so the inspector now has it and it will go live after the check. " * 4, transcript_path=tr("You are Manager_Muster_002", [said("well?"), use("Bash", "b1", command="ls"), res("b1", "x"), said("<cross-session-message from=\"b\">READY: x [ID b-1]</cross-session-message>")])), True),
    ("his question with tool calls in the same turn still counts", run("Stop", last_assistant_message="Yes, it is shipped.", transcript_path=tr("You are Manager_Muster_002", [said("well?"), use("Bash", "b1", command="ls"), res("b1", "x")])), False),
    ("a question mark from another chat is not his: a long answer still blocks", run("Stop", last_assistant_message="Yes, it is shipped and live on the site now, with the new version and every check green on all three systems. " * 4, transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"x\">is it done?</cross-session-message>")])), True),
    ("a short routine reply to another chat's message is not bounced (item 75)", run("Stop", last_assistant_message="Understood, I will look at it next.", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"x\">is it done?</cross-session-message>")])), False),
    ("item 75: a short reply after a worker's READY passes", run("Stop", last_assistant_message="Sending it to the inspector now.", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">READY: x [ID b-1]</cross-session-message>")])), False),
    ("item 97: PASS news to the owner after a worker's message is blocked", run("Stop", last_assistant_message="Inspector passed it: PASS on 0.3.80.", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">PASS: x [ID b-1]</cross-session-message>")])), True),
    ("item 97: LIVE and shipped news is blocked", run("Stop", last_assistant_message="LIVE PROVEN 0.3.80, shipped.", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">DONE: x [ID b-2]</cross-session-message>")])), True),
    ("item 97: progress news is blocked", run("Stop", last_assistant_message="Progress: the builder is rebuilding the programs.", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">x</cross-session-message>")])), True),
    ("item 97: a lettered question that mentions the ship passes", run("Stop", last_assistant_message="Ship 0.3.80 now?\n\n***A.*** yes, ship it (my pick)\n\n***B.*** hold it", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">PASS: x [ID b-3]</cross-session-message>")])), False),
    ("item 103: 'is waiting for you: type in' is refused (the manager carries his approval)", run("Stop", last_assistant_message="Builder A is waiting for you: type in Builder A_Muster_002 (shipped work needs your yes).", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">x</cross-session-message>")])), True),
    ("item 97: an empty reply after a worker's message is not asked for text", run("Stop", last_assistant_message="", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">PASS: x [ID b-4]</cross-session-message>")])), False),
    ("item 97: his own question may be answered with the news he asked for", run("Stop", last_assistant_message="It is shipped: 0.3.80 is live.", transcript_path=tr("You are Manager_Muster_002", [said("is it shipped yet?")])), False),
    ("item 97: the same report to the same chat unchanged is refused", run("PreToolUse", tool_name="SendMessage", tool_input={"to": "Inspector_Muster_002", "message": good.replace("x-1", "x-2")}, transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", to="Inspector_Muster_002", message=good), res("s1")])), True),
    ("item 97: the same report to the manager as a copy goes through", run("PreToolUse", tool_name="SendMessage", tool_input={"to": "Manager_Muster_002", "message": good.replace("x-1", "x-2")}, transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", to="Inspector_Muster_002", message=good), res("s1")])), False),
    ("item 97: a changed report to the same chat goes through", run("PreToolUse", tool_name="SendMessage", tool_input={"to": "Inspector_Muster_002", "message": good.replace("x-1", "x-2").replace("a\n", "a changed\n", 1)}, transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", to="Inspector_Muster_002", message=good), res("s1")])), False),
    ('item 99: a worker over 300000 tokens is told to renew by size', run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [big(350000)])), True),
    ('item 99: ...even with no text at all', run("Stop", last_assistant_message="", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [big(350000)])), True),
    ('item 99: a worker under the line is silent', run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [big(150000)])), False),
    ('item 99: said once per chat (the told note is in the transcript)', run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [big(350000), {"type": "user", "message": {"content": "Stop hook feedback:\nMuster rule: Muster renewal by size: this chat now carries 350000 tokens"}}])), False),
    ('item 99: a manager over the line is told to hand over', run("Stop", last_assistant_message="Which first?\n\n***A.*** a\n\n***B.*** b", transcript_path=tr("You are Manager_Muster_002", [big(350000)])), True),
    ('item 99: a stop already continuing because of a hook is not blocked again', run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", stop_hook_active=True, transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [big(350000)])), False),
    ("item 99: the owner's own chat is never told", run("Stop", last_assistant_message="hi", transcript_path=tr("hello", [big(900000)])), False),
    ("item 75: a short reply to HIS typed statement still blocks", run("Stop", last_assistant_message="All done, nice and good.", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">x</cross-session-message>"), said("ok thanks")])), True),
    ("his question, then hook feedback inside his turn: the answer still passes", run("Stop", last_assistant_message="Yes, it is shipped.", transcript_path=tr("You are Manager_Muster_002", [said("well?"), said("Stop hook feedback: rewrite it"), said("<system-reminder>note</system-reminder>")])), False),
    ("his question, then an app event (task notification): long narration blocked", run("Stop", last_assistant_message="The task finished and the result was written to the file and then checked against every one of the notes. " * 4, transcript_path=tr("You are Manager_Muster_002", [said("well?"), said("<system-reminder>[SYSTEM NOTIFICATION] <task-notification>x</task-notification></system-reminder>")])), True),
    ("a question mark in hook feedback or a system note is not his (long reply)", run("Stop", last_assistant_message="Yes, it is shipped and live on the site now, with the new version and every check green on all three systems. " * 4, transcript_path=tr("You are Manager_Muster_002", [said("[SYSTEM NOTIFICATION - NOT USER INPUT] ready?"), said("<system-reminder>really?")])), True),
    ("a manager question as lettered lines passes", run("Stop", last_assistant_message="Which one?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=m), False),
    ("a manager idle line passes", run("Stop", last_assistant_message="The crew is idle. Here's what's next.", transcript_path=m), False),
    ("item 103: a manager waiting line is refused", run("Stop", last_assistant_message="Builder A is waiting for you: type in Builder A_Muster_002.", transcript_path=m), True),
    ("item 103: 'type it in the chat' is refused", run("Stop", last_assistant_message="Please type it in the Builder A chat.", transcript_path=m), True),
    ("an unrecorded choice answer blocks the manager", run("Stop", last_assistant_message="ok", transcript_path=tr("You are Manager_Muster_002", [use("AskUserQuestion", questions=[])])), True),
    ("a recorded choice answer passes", run("Stop", last_assistant_message="ok", transcript_path=tr("You are Manager_Muster_002", [use("AskUserQuestion", questions=[]), use("Bash", command="python3 scripts/record-choice.py p 3 --picked A")])), False),
    ("a worker card passes", run("Stop", last_assistant_message="**WORKING · x**\n- a\n- b", transcript_path=b), False),
    ("REPORT: a READY card with no message to the manager is blocked (item 65)", run("Stop", last_assistant_message="**READY · x**\n- a\n- b", transcript_path=b), True),
    ("REPORT: a READY card sent only to the inspector is blocked", run("Stop", last_assistant_message="**READY · x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [said("go"), use("SendMessage", "s1", to="Inspector_Muster_002", message="m")])), True),
    ("REPORT: a READY card after a message to the manager passes", run("Stop", last_assistant_message="**READY · x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [said("go"), use("SendMessage", "s1", to="Manager_Muster_002", message="m")])), False),
    ("REPORT: a READY card after the app's send_message to the manager passes", run("Stop", last_assistant_message="**READY · x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [said("go"), use("mcp__ccd_session_mgmt__send_message", "s1", session_id="Manager_Muster_002", message="m")])), False),
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
        ("RECORDS: an unknown key is refused", send_rec(REC.replace('"v":1,', '"v":1,"memo":"hi",')), True),
        ("RECORDS: touches naming a real top-level folder goes through", send_rec(RDY, cwd=os.path.join(HERE, "..")), False),
        ("RECORDS: touches that spell a sentence one word per entry are refused", send_rec(RDY.replace('["hooks"]', '["path","uses","backslashes","on","windows"]'), cwd=os.path.join(HERE, "..")), True),
        ("RECORDS: touches naming nothing in the project are refused", send_rec(RDY.replace('["hooks"]', '["nothing-here"]'), cwd=os.path.join(HERE, "..")), True),
        ("RECORDS: a PASS copy for the manager as a message goes through (item 65)", send_rec(REC, "Manager_Muster_003"), False),
    ]
# the weekly goal: an ORDER whose job is not on the owner's set list waits; setting it again changes it; no goal enforces nothing
GOALPY = os.path.join(HERE, "goal.py")
GD = os.path.join(T, "goalproj"); os.makedirs(GD)
ORD = '{"v":1,"kind":"ORDER","id":"manager-%s-1","job":"%s","from":"manager","to":"builder-a","owner_words":{"item":35},"owns":[],"out":[],"action":"start","need":"none"}'
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
cases += [
    ("ACTION: an ORDER without an action is refused", send_rec(ORD.replace(',"action":"start"', '') % ("a-job", "a-job"), "builder-a", cwd=GD), True),
    ("ACTION: an ORDER with an action outside ship, hold, start is refused", send_rec((ORD % ("a-job", "a-job")).replace("start", "go"), "builder-a", cwd=GD), True),
    ("ACTION: ship, hold and start go through", "" if all(not send_rec((ORD % ("a-job", "a-job")).replace("start", a).replace("a-job-1", "a-job-%d" % i), "builder-a", cwd=GD) for i, a in enumerate(["ship", "hold", "start"], 5)) else "BAD", False),
]
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
# a note (item 52): one plain line, 400 characters at most, no secrets
def with_note(n):
    return REC.replace('"v":1,', '"v":1,"note":%s,' % json.dumps(n), 1)
cases += [
    ("NOTE: a plain note goes through", send_rec(with_note("Handover done: archive the old chats.")), False),
    ("NOTE: a note over 400 characters is refused", send_rec(with_note("x" * 401)), True),
    ("NOTE: a note holding a token is refused", send_rec(with_note("use token = abc123")), True),
    ("NOTE: a note with a line break is refused", send_rec(with_note("a\nb")), True),
]
# the manager's stop check (item 53): wrong blocks fixed, the shape check kept
MG = "You are Manager_Muster_002"
asked = lambda tid, ans, err=False: [use("AskUserQuestion", tid, questions=[]), res(tid, ans, err)]
cases += [
    ("STOP: a short pointer to the board passes", run("Stop", last_assistant_message="The news is on the board.", transcript_path=tr(MG)), False),
    ("STOP: a long report that mentions the board still blocks", run("Stop", last_assistant_message="I fixed all the things and then shipped them to main and it is all on the board now. " * 6, transcript_path=tr(MG)), True),
    ("STOP: a code block alone is not a pass", run("Stop", last_assistant_message="Here:\n```bash\ngit pull\n```", transcript_path=tr(MG)), True),
    ("STOP: a plain answer to a question he asked passes", run("Stop", last_assistant_message="Because the test run timed out.", transcript_path=tr(MG, [said("why did the build fail?")])), False),
    ("STOP: a plain answer to words with no question mark passes", run("Stop", last_assistant_message="It stays in the plugin folder.", transcript_path=tr(MG, [said("tell me where the zip move ended up")])), False),
    ("STOP: a reply to a plain statement still blocks", run("Stop", last_assistant_message="All done, nice and good.", transcript_path=tr(MG, [said("ok thanks")])), True),
    ("STOP: a check bounces once per turn: after one bounce the next stop passes", run("Stop", last_assistant_message="All done, nice and good.", transcript_path=tr(MG, [said("ok thanks"), said("Stop hook feedback:\nto the owner the manager says only a question")])), False),
    ("STOP: ...and a new message starts a new turn that can bounce again", run("Stop", last_assistant_message="All done, nice and good.", transcript_path=tr(MG, [said("Stop hook feedback:\nx"), said("ok thanks")])), True),
    ("STOP: a long report to him still blocks", run("Stop", last_assistant_message="I fixed all the things and then shipped them to main and the live site now has the new version. " * 5, transcript_path=tr(MG)), True),
    ("STOP: a card he skipped needs no record", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, asked("q1", "The user doesn't want to proceed", True))), False),
    ("STOP: a skipped card does not excuse a bad reply", run("Stop", last_assistant_message="All done, nice and good.", transcript_path=tr(MG, asked("q1", "The user doesn't want to proceed", True))), True),
    ("STOP: an answered card still needs its record", run("Stop", last_assistant_message="ok", transcript_path=tr(MG, asked("q1", "Your questions have been answered: x"))), True),
    ("STOP: the refusal never names scripts/decide.py", "" if "decide.py" not in run("Stop", last_assistant_message="ok", transcript_path=tr(MG, asked("q1", "Your questions have been answered: x"))) else "BAD", False),
]
# the board stop check (item 59): an item the manager has routed is handled, so the same waiting line is not demanded again
BSH = os.path.join(HERE, "..", "hooks", "board-stop.py")
def bstop(board, said="Nothing else."):
    d = tempfile.mkdtemp(dir=T); os.makedirs(os.path.join(d, "muster"))
    open(os.path.join(d, "muster", "BOARD.md"), "w", encoding="utf-8").write("# Board\n" + board)
    env = dict(os.environ, MUSTER_ASSUME_MANAGER="1")
    r = subprocess.run([BIN, "board-stop"] if BIN else [sys.executable, BSH], input=json.dumps(dict(hook_event_name="Stop", cwd=d, last_assistant_message=said, transcript_path=tr(MG))), capture_output=True, text=True, env=env)
    return r.stdout.strip()
NEED = "\n### 2026-11-12 | NEED | Builder A_X_001 -> Manager_X_001 | a job\nStatus: open\nNEED: a job\n"
cases += [
    ("BOARD: an open NEED the manager has not routed is demanded", bstop(NEED), True),
    ("BOARD: ...and passes once the reply names it", bstop(NEED, "Relayed his answer to Builder A_X_001."), False),
    ("BOARD: a NEED with a routed Status line is handled", bstop(NEED.replace("Status: open", "Status: routed")), False),
    ("BOARD: a NEED the manager later answered on the same job is handled", bstop(NEED + "\n### 2026-11-12 | ORDER | Manager_X_001 -> Builder A_X_001 | a job\nStatus: open\nORDER: a job\n"), False),
    ("BOARD: a later manager entry on another job does not clear it", bstop(NEED + "\n### 2026-11-12 | ORDER | Manager_X_001 -> Builder A_X_001 | other job\nStatus: open\n"), True),
]
# show first (item 63): a question to him about how something looks comes after the pictures, shown in the same turn
def ask(t, **inp):
    return run("PreToolUse", tool_name="AskUserQuestion", tool_input=inp, transcript_path=t)
LQ = [{"question": "Which colour do you prefer for the header?", "options": [{"label": "A", "description": "x"}, {"label": "B", "description": "y"}]}]
LQP = [{"question": "Which colour do you prefer for the header?", "options": [{"label": "A", "description": "x", "preview": "<pic>"}, {"label": "B", "description": "y"}]}]
SHOT = use("SendUserFile", files=["/tmp/header.png"], status="normal", display="render")
cases += [
    # item 80, D-037: questions as lettered lines; his typed letter is the answer and must be recorded
    ("D-037: the refusal says to use lettered lines and keep working", "" if "lettered lines" in ask(tr(MG, [said("hi")]), questions=LQ) and "keep working" in ask(tr(MG, [said("hi")]), questions=LQ).lower() else "BAD", False),
    ("D-037: a question with buttons wording and no lettered lines blocks", run("Stop", last_assistant_message="Which one? Pick a button.", transcript_path=tr(MG, [said("hi")])), True),
    ("D-037: his typed letter after a lettered question needs the record", run("Stop", last_assistant_message="Good, going ahead.", transcript_path=tr(MG, [said("what next?"), {"type": "assistant", "message": {"content": [{"type": "text", "text": "Which one?\n\n***A.*** yes (my pick)\n\n***B.*** no"}]}}, said("a")])), True),
    ("D-037: ...a capital letter with a full stop counts too", run("Stop", last_assistant_message="Good, going ahead.", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "***A.*** x (my pick)\n\n***B.*** y"}]}}, said("B.")])), True),
    ("D-037: ...recorded with record-choice.py it passes", run("Stop", last_assistant_message="Good, going ahead.", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "***A.*** x (my pick)\n\n***B.*** y"}]}}, said("a"), use("Bash", command="python3 scripts/record-choice.py x 5 --question q --option 'A. x' --option 'B. y' --picked 'A. x'")])), False),
    ("D-037: a typed word that starts with a letter is not an answer", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "***A.*** x (my pick)\n\n***B.*** y"}]}}, said("a quick question first")])), False),
    ("D-037: a typed letter with no lettered question before it is not an answer", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "All done."}]}}, said("a")])), False),
    ("D-037: a letter inside another chat's message is not his answer", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "***A.*** x (my pick)\n\n***B.*** y"}]}}, said("<cross-session-message from=\"x\">a</cross-session-message>")])), False),
    # item 80 addition: the letters are bold and italic, ***A.***
    ("item 80: a bold-italic lettered question passes", run("Stop", last_assistant_message="Which?\n\n***A.*** red (my pick)\n\n***B.*** blue", transcript_path=tr(MG, [said("hi")])), False),
    ("item 80: a bold-only lettered question is flagged", run("Stop", last_assistant_message="Which?\n\n**A.** red\n\n**B.** blue", transcript_path=tr(MG, [said("hi")])), True),
    ("item 80: an italic-only or plain lettered question is flagged", run("Stop", last_assistant_message="Which?\n\n*A.* red\n\n*B.* blue", transcript_path=tr(MG, [said("hi")])), True),
    ("item 80: one wrong letter among right ones is flagged", run("Stop", last_assistant_message="Which?\n\n***A.*** red\n\n**B.** blue", transcript_path=tr(MG, [said("hi")])), True),
    ("item 80: the flag says bold and italic", "" if "bold and italic" in run("Stop", last_assistant_message="Which?\n\n**A.** red\n\n**B.** blue", transcript_path=tr(MG, [said("hi")])) else "BAD", False),
    ("item 80: his letter after a bold-italic question needs the record", run("Stop", last_assistant_message="Going ahead.", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "***A.*** x (my pick)\n\n***B.*** y"}]}}, said("b")])), True),
    ("item 80: ...and passes once recorded", run("Stop", last_assistant_message="Going ahead.", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "***A.*** x (my pick)\n\n***B.*** y"}]}}, said("b"), use("Bash", command="python3 scripts/record-choice.py x 5 --question q --option 'A. x' --option 'B. y' --picked 'B. y'")])), False),
    ("SHOWFIRST/D-037: a look question card is refused", ask(tr(MG, [said("hi")]), questions=LQ), True),
    ("D-037: a manager card with option previews is refused too", ask(tr(MG, [said("hi")]), questions=LQP), True),
    ("D-037: a manager card after pictures is refused too", ask(tr(MG, [said("hi"), SHOT]), questions=LQ), True),
    ("D-037: any manager card is refused (it locks the chat)", ask(tr(MG, [said("hi")]), questions=[{"question": "Ship it now?", "options": []}]), True),
    ("SHOWFIRST: a worker's card is not this check's business", ask(b, questions=LQ), False),
    ("SHOWFIRST: a look question in a reply with no pictures is blocked", run("Stop", last_assistant_message="Which colour do you prefer?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), True),
    ("SHOWFIRST: ...with pictures shown this turn it passes", run("Stop", last_assistant_message="Which colour do you prefer?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi"), SHOT])), False),
    ("SHOWFIRST (item 88): 'layout' in a list above a non-look question passes", run("Stop", last_assistant_message="Open items: burn layout, site cleanup.\n\nWhich do we push next?\n\n***A.*** the iPhone App Store path (my pick)\n\n***B.*** clear the open site questions", transcript_path=tr(MG, [said("hi")])), False),
    ("SHOWFIRST (item 88): a look word in a choice line only passes", run("Stop", last_assistant_message="Which do we push next?\n\n***A.*** fix the colour of the banner (my pick)\n\n***B.*** clear the open site questions", transcript_path=tr(MG, [said("hi")])), False),
    ("SHOWFIRST (item 88): no question, look words, passes", run("Stop", last_assistant_message="The crew is idle. The layout and colour work is done and shipped.", transcript_path=tr(MG, [said("hi")])), False),
    ("SHOWFIRST (item 88): a real look question still blocks", run("Stop", last_assistant_message="Open items: none.\n\nWhich colour do you prefer for the page?\n\n***A.*** blue (my pick)\n\n***B.*** green", transcript_path=tr(MG, [said("hi")])), True),
    ("PICK (item 100): a lettered question with no pick blocks", run("Stop", last_assistant_message="Ship it now?\n\n***A.*** yes\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), True),
    ("PICK: the same question with a marked pick passes", run("Stop", last_assistant_message="Ship it now?\n\n***A.*** yes *(my pick: it passed)*\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), False),
    ("PICK: a look question with its pick passes once the pictures were shown", run("Stop", last_assistant_message="Which colour do you prefer?\n\n***A.*** blue *(my pick: it reads best)*\n\n***B.*** green", transcript_path=tr(MG, [said("hi"), SHOT])), False),
    ("PICK: a look question without a pick blocks", run("Stop", last_assistant_message="Which colour do you prefer?\n\n***A.*** blue\n\n***B.*** green", transcript_path=tr(MG, [said("hi"), SHOT])), True),
    ("PICK: a reply with no lettered question is not this check's business", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, [said("hi")])), False),
    ("SHOWFIRST: a question that is not about looks passes", run("Stop", last_assistant_message="Ship it now?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), False),
    # item 91: two or more lettered choice lines are the question, with or without a question mark
    ("LETTERS: a lead-in ending in a colon plus lettered lines passes", run("Stop", last_assistant_message="Sentence 5 of 6, on what stays on the phone:\n\n***A.*** the list stays (my pick)\n\n***B.*** only the totals stay\n\n***C.*** nothing stays", transcript_path=tr(MG, [said("hi")])), False),
    ("LETTERS: two lettered lines with a question mark still pass", run("Stop", last_assistant_message="Keep it?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), False),
    ("LETTERS: one lone lettered line with no question still blocks", run("Stop", last_assistant_message="Here is the thing.\n\n***A.*** yes", transcript_path=tr(MG, [said("hi")])), True),
    ("LETTERS: filler with no lettered lines still blocks", run("Stop", last_assistant_message="On what stays on the phone:\nthe list stays.", transcript_path=tr(MG, [said("hi")])), True),
    # item 88: his question with no question mark is still a question; "looks" in a rules choice is not a look question
    ("ANSWER: his question (no question mark) then a plain two-line answer passes", run("Stop", last_assistant_message="Make up a new one for the keystore.\nIt is not your machine password.", transcript_path=tr(MG, [said("make up a keystore password or is that my machine password")])), False),
    ("ANSWER: a question with a question mark then a plain answer passes", run("Stop", last_assistant_message="Make up a new one for the keystore.\nIt is not your machine password.", transcript_path=tr(MG, [said("should i make up a keystore password?")])), False),
    ("ANSWER: the same plain reply with nothing asked by him is still blocked", run("Stop", last_assistant_message="Make up a new one for the keystore.\nIt is not your machine password.", transcript_path=tr(MG, [said("hi")])), True),
    ("ANSWER: a statement of his that is not a question still blocks a filler reply", run("Stop", last_assistant_message="Make up a new one for the keystore.\nIt is not your machine password.", transcript_path=tr(MG, [said("the build finished overnight")])), True),
    ("LOOKS: a rules choice that says 'looks right' passes without pictures", run("Stop", last_assistant_message="Which rule wording reads right?\n\n***A.*** the short one (my pick)\n\n***B.*** it looks right as written", transcript_path=tr(MG, [said("hi")])), False),
    ("LOOKS: 'look' about the crew's order, not a screen, passes", run("Stop", last_assistant_message="Should the manager look at the board first?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), False),
    ("LOOKS: a real visual choice (header on a page) still needs pictures", run("Stop", last_assistant_message="Should the header look bigger on the page?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), True),
    ("LOOKS: ...and passes once the pictures were shown", run("Stop", last_assistant_message="Should the header look bigger on the page?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi"), SHOT])), False),
]
# founder orders (item 76): a manager does not say it cannot do, or argue with, a task he typed
cases += [
    ("FOUNDER: a refusal of a task he typed is blocked", run("Stop", last_assistant_message="I can't do that from here, it would break the board.", transcript_path=tr(MG, [said("archive the old chats now")])), True),
    ("FOUNDER: an argument against his order is blocked", run("Stop", last_assistant_message="I would advise against that. Which one? Pick a letter.", transcript_path=tr(MG, [said("archive the old chats now")])), True),
    ("FOUNDER: doing it and asking one question passes", run("Stop", last_assistant_message="Which chats do you mean?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("archive the old chats now")])), False),
    ("FOUNDER: a refusal is blocked even after one bounce already (no once-per-turn pass)", run("Stop", last_assistant_message="I can't do that from here, it would break the board.", transcript_path=tr(MG, [said("archive the old chats now"), said("Stop hook feedback:\nx")])), True),
    ("FOUNDER: ...even when the stop hook is already active", run("Stop", last_assistant_message="I cannot do that.", stop_hook_active=True, transcript_path=tr(MG, [said("archive the old chats now")])), True),
    ("FOUNDER: one short question is the way through", run("Stop", last_assistant_message="I can't tell which chats: do you mean all of them?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("archive the old chats now")])), False),
    ("FOUNDER: reinterpreting his order is blocked", run("Stop", last_assistant_message="I took that to mean the PINR chats, so I archived those.", transcript_path=tr(MG, [said("archive the old chats now")])), True),
    ("FOUNDER: a worker's refusal in its own chat is not the manager's rule", run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- I can't ship it\n- b", transcript_path=b), False),
    ("FOUNDER: a refusal sentence after an app event (not his order) is not this check", run("Stop", last_assistant_message="The crew is idle. I can't start a chat for the inspector.", transcript_path=tr(MG, [said("<task-notification>x")])), False),
]
# the card title of a started chat is its final name (item 69)
def starts(title):
    return run("PreToolUse", tool_name="mcp__ccd_session__start_session", tool_input={"title": title, "prompt": "x"}, transcript_path=m)
cases += [
    ("TITLE: a title with a Start prefix is refused", starts("Start Engine_PINR_006"), True),
    ("TITLE: the worker's full name goes through", starts("Engine_PINR_006"), False),
    ("TITLE: an ordinary session title goes through", starts("Fix the login bug"), False),
]
# group check (item 79): a started chat must be filed into the group and read back
S = lambda **k: use("mcp__ccd_session__start_session", title="Engine_P_006", prompt="x", **k)
MV = use("mcp__ccd_sidebar__move_sessions", session_ids=["x"], group="P")
LS = use("mcp__ccd_session_mgmt__list_sessions", group="P")
cases += [
    ("GROUP: a start with no move and read-back is flagged", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, [said("start it"), S(initiation="user_asked")])), True),
    ("GROUP: a start and a move but no read-back is flagged", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, [said("start it"), S(initiation="user_asked"), MV])), True),
    ("GROUP: a start followed by the move and the read-back passes", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, [said("start it"), S(initiation="user_asked"), MV, LS])), False),
    ("GROUP: a read-back before the move does not count", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, [said("start it"), S(initiation="user_asked"), LS, MV])), True),
    ("GROUP: a card that only proposes a chat is not a start", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, [said("start it"), S(initiation="offer")])), False),
    ("GROUP: a refused step named with the drag line passes", run("Stop", last_assistant_message="The crew is idle. The app refused the move: drag Engine_P_006 into the group.", transcript_path=tr(MG, [said("start it"), S(initiation="user_asked")])), False),
    ("GROUP: a worker is not checked", run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [said("go"), S(initiation="user_asked")])), False),
]
bad = 0
for name, out, should_block in cases:
    ok = bool(out) == should_block
    bad += not ok
    print(("ok   " if ok else "MISS ") + name)
print("%d of %d passed" % (len(cases) - bad, len(cases)))
sys.exit(1 if bad else 0)
