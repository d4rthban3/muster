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
T = tempfile.mkdtemp()


def tr(first, extra=()):
    p = os.path.join(T, "t%d.jsonl" % len(os.listdir(T)))
    with open(p, "w") as f:
        f.write(json.dumps({"type": "user", "message": {"content": first}}) + "\n")
        for e in extra:
            f.write(json.dumps(e) + "\n")
    return p


def use(name, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


def run(ev, **kw):
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(dict(hook_event_name=ev, cwd=T, **kw)), capture_output=True, text=True)
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
    ("a free-form message is refused", send("hey, can you look at this?", b), True),
    ("a READY with no test count is refused", send(good.replace("3/3 passed", "fine"), b), True),
    ("an order that quotes his words goes through", send(order, m), False),
    ("an order without his words quoted is refused", send(order.replace('"do it now"', "do it now"), m), True),
    ("an ID sent twice is refused", send(good, tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", message=good)])), True),
    ("a PASS copy to the manager as a message is refused", send(good.replace("READY", "PASS").replace("Usage: n", "") .replace("\n\n", "\n").strip(), b, "Manager_Muster_002"), True),
    ("the owner's own chat is never touched", send("noted", owner), False),
    ("a worker cannot write the owner's list", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/p/muster/OWNERS-LIST.md"}, transcript_path=b), True),
    ("the manager can write the owner's list", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/p/muster/OWNERS-LIST.md"}, transcript_path=m), False),
    ("nobody commits muster/", run("PreToolUse", tool_name="Bash", tool_input={"command": "git add muster/BOARD.md"}, transcript_path=m), True),
    ("an ordinary command goes through", run("PreToolUse", tool_name="Bash", tool_input={"command": "git status"}, transcript_path=b), False),
    ("a manager reply that is not a question is blocked", run("Stop", last_assistant_message="All done, nice.", transcript_path=m), True),
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
bad = 0
for name, out, should_block in cases:
    ok = bool(out) == should_block
    bad += not ok
    print(("ok   " if ok else "MISS ") + name)
print("%d of %d passed" % (len(cases) - bad, len(cases)))
sys.exit(1 if bad else 0)
