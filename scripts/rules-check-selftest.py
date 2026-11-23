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
# right-hand 4: every call of a check below is kept (command, input, environment, answer) so the refused ones can be replayed under another profile
CALLS = []
_real_run = subprocess.run
def _kept_run(cmd, *a, **k):
    r = _real_run(cmd, *a, **k)
    if isinstance(cmd, list) and ((len(cmd) > 1 and cmd[0] == BIN and cmd[1] in ("rules", "board-stop")) or (len(cmd) > 1 and cmd[0] == sys.executable and os.path.basename(cmd[1]) in ("rules-check.py", "board-stop.py"))):
        CALLS.append((cmd, k.get("input"), k.get("env"), (r.stdout or "").strip()))
    return r
subprocess.run = _kept_run


import itertools
_tn = itertools.count()


def tr(first, extra=()):
    p = os.path.join(T, "t%d.jsonl" % next(_tn))
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


PEER = '<cross-session-message from="b">{"kind":"READY"}</cross-session-message>'


def card(ts=None):
    d = {"type": "assistant", "message": {"content": [{"type": "text", "text": "**IDLE \u00b7 crew**\n\nThe crew is idle. Here's what's next toward your goal,\n\n***A.*** one\n\n***B.*** two"}]}}
    if ts:
        d["timestamp"] = ts
    return d


report = lambda i: '<cross-session-message from="x">{"v":1,"kind":"PASS","id":"%s","job":"j"}</cross-session-message>' % i


def big(n):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": "x"}], "usage": {"input_tokens": 5, "cache_read_input_tokens": n - 5000, "cache_creation_input_tokens": 4995}}}



def run_raw(ev, **kw):
    r = subprocess.run([BIN, "rules"] if BIN else [sys.executable, HOOK], input=json.dumps(dict(dict(hook_event_name=ev, cwd=T), **kw)), capture_output=True, text=True, env=RUN_ENV)
    return r.stdout.strip()


def run(ev, **kw):
    """The hook's answer; a pending note (told once at the next event, never a refusal) is not an answer here: run_raw shows it."""
    out = run_raw(ev, **kw)
    return "" if out.startswith('{"hookSpecificOutput": {"hookEventName": "%s", "additionalContext": "Muster note' % ev) else out



def _proj(name, entry):
    d = os.path.join(T, name); os.makedirs(os.path.join(d, "muster"))
    open(os.path.join(d, "muster", "BOARD.md"), "w").write("# Board\n\n## Entries\n" + entry)
    return d
MG = "You are Manager_Muster_002"
_o = "### 2026-01-01 | ORDER | Manager_X -> %s | job\nStatus: %s\nORDER: job\n"
PJ_IDLE = _proj("pj_idle", "### 2026-01-01 | PASS | Inspector_X -> Manager_X | job\nStatus: open\n")
PJ_BUSY = _proj("pj_busy", _o % ("Builder A_X", "open"))
PJ_MGR = _proj("pj_mgr", _o % ("Manager_X", "open"))
PJ_DONE = _proj("pj_done", _o % ("Builder A_X", "done"))

b = tr("You are Builder A_Muster_002, agents/builder.md")
m = tr("You are Manager_Muster_002")
owner = tr("hello there")
good = "READY: x [ID builder-x-1]\nWhat: a\nWhere: b; touches: none\nWhy: c\nHow: 3/3 passed\nNeed: nothing\nUsage: n"
order = "To: B\nJob: j\nOwner's words: \"do it now\"\nOwns: a\nOut: b\nAccept: \"do it now\" met\nDone: c"
send = lambda msg, t, to="x": run("PreToolUse", tool_name="SendMessage", tool_input={"to": to, "message": msg}, transcript_path=t)
def compacted(first):
    """a transcript the way a compaction leaves it: the chat's own first message is kept beside it, the file opens with the summary"""
    p = tr("You are " + first)
    run("PreToolUse", tool_name="Read", tool_input={"file_path": "/home/x/p/a"}, transcript_path=p)  # the first sight keeps the first message
    with open(p, "w") as f:
        f.write(json.dumps({"type": "user", "isCompactSummary": True, "message": {"content": "This session is being continued from a previous conversation that ran out of context."}}) + "\n")
    return p


def tool_first(first):
    """a transcript whose first user line holds only tool results (a chat started by another chat), then the chat's real first message"""
    p = os.path.join(T, "tf%d.jsonl" % next(_tn))
    with open(p, "w") as f:
        f.write(json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}}) + "\n")
        f.write(json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": first}]}}) + "\n")
    return p


def summary_only(summary):
    """a compacted chat with NO .muster-first kept: the file opens with the summary, then a first line that names no crew chat"""
    p = os.path.join(T, "so%d.jsonl" % next(_tn))
    with open(p, "w") as f:
        f.write(json.dumps({"type": "user", "isCompactSummary": True, "message": {"content": summary}}) + "\n")
        f.write(json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "carry on"}]}}) + "\n")
    return p


sum_b = summary_only("Summary: I am Builder A_Muster (chat Builder A_Muster_006); I build what the manager orders.")
sum_m = summary_only("Summary: You are Manager_Muster_001, the go-between.")
sum_o = summary_only("Summary: the owner asked about the report that Builder A_Muster sent to the inspector.")
tool_first_b = tool_first("You are Builder A_Muster_002, agents/builder.md")
tool_first_o = tool_first("hello there")
compacted_mgr = compacted("Manager_Muster")
compacted_b = compacted("Builder A_Muster, agents/builder.md")

Q = "**ASK \u00b7 q**\nWhich first?\n\n***A.*** ship the menu fix *(my pick)* because it is small\n\n***B.*** wait for the next piece"
QM = "Coverage order?\nA: bot signs next, as ordered.\nB: X scan and callouts first."
QM6 = "Coverage order?\nA: bot signs next, as ordered.\nB: X scan and callouts first.\nA is smaller.\nB is wider.\nTell me which."
QU = "See https://example.com/a?b=1 for the notes on the coverage order and what comes next."
QL = "Coverage order: A (bot signs next, as ordered) or B (X scan and callouts first)?"
QC = "**ASK \u00b7 coverage now**\n\nOn the live list 280 coins show coverage.\n\n***A.*** Keep the order: bot signs next, as ordered. *(my pick)*\n\n***B.*** Put the X scan and callouts first."
asst = lambda t: {"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}
usr = lambda t: {"type": "user", "message": {"content": t}}
mgr_first = "You are Manager_Muster"
bn = tr("You are Builder A_Muster, agents/builder.md")
mn = tr("You are Manager_Muster")
cases = [
    ("a good READY goes through", send(good, b), False),
    ("D-040: a builder named with no number sends a good READY", send(good, bn), False),
    ("D-040: a builder named with no number is refused 'noted'", send("noted", bn), True),
    ("D-040: a manager named with no number may send an order that quotes his words", send(order, mn), False),
    ("D-040: a manager named with no number is refused an order without his words", send(order.replace('"do it now"', "do it now"), mn), True),
    ("item 108: a Write of crew rules into the chat's own memory is refused", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/home/x/.claude/projects/-home-x-Muster/memory/feedback_crew.md", "content": "Builders must send READY to the inspector (D-036)"}, transcript_path=b), True),
    ("item 108: an Edit of the memory index with the crew rules is refused", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/home/x/.claude/projects/-home-x-Muster/memory/MEMORY.md", "new_string": "- crew rules: the manager ships"}, transcript_path=b), True),
    ("item 108: the manager may not write crew rules into memory either", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/home/x/.claude/projects/-p/memory/a.md", "content": "Muster rule: item 107"}, transcript_path=m), True),
    ("item 108: a shell write of crew rules into memory is refused", run("PreToolUse", tool_name="Bash", tool_input={"command": "echo 'the Manager ships, builders send READY' >> ~/.claude/projects/-p/memory/a.md"}, transcript_path=b), True),
    ("item 108: a memory note with no crew rules goes through", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/home/x/.claude/projects/-home-x-Muster/memory/user.md", "content": "The owner likes short answers."}, transcript_path=b), False),
    ("item 108: crew words written outside memory go through", run("PreToolUse", tool_name="Write", tool_input={"file_path": "/home/x/Muster/notes.md", "content": "Builder A sends READY"}, transcript_path=b), False),
    ("D-039: a manager still edits the crew list after a compaction rewrote its first message", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/home/x/p/muster/CREW.md", "new_string": "x"}, transcript_path=compacted_mgr), False),
    ("item 119: a crew chat's wrap-up call with a question is refused", run("PreToolUse", tool_name="mcp__ccd_turn__wrap_up", tool_input={"recap": "done", "ask": "Ship it?"}, transcript_path=b), True),
    ("item 119: ...and with buttons only", run("PreToolUse", tool_name="mcp__ccd_turn__wrap_up", tool_input={"recap": "done", "actions": [{"label": "Yes"}]}, transcript_path=m), True),
    ("item 119: a wrap-up with only a recap goes through", run("PreToolUse", tool_name="mcp__ccd_turn__wrap_up", tool_input={"recap": "done"}, transcript_path=b), False),
    ("item 119: empty ask and actions go through", run("PreToolUse", tool_name="mcp__ccd_turn__wrap_up", tool_input={"recap": "done", "ask": "", "actions": []}, transcript_path=b), False),
    ("item 119: the owner's own chat is not checked", run("PreToolUse", tool_name="mcp__ccd_turn__wrap_up", tool_input={"recap": "done", "ask": "Ship it?"}, transcript_path=owner), False),
    ("item 120: a crew chat whose first transcript line holds only tool results is still known as crew (stopped from the crew list)", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/home/x/p/muster/CREW.md", "new_string": "x"}, transcript_path=tool_first_b), True),
    ("item 120: ...and its own first message is what gets kept beside the transcript", "" if open(tool_first_b + ".muster-first").read().startswith("You are Builder A_Muster_002") else "BAD", False),
    ("item 120: the owner's own chat with such a first line is still not crew", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/home/x/p/muster/CREW.md", "new_string": "x"}, transcript_path=tool_first_o), False),
    ("item box-check-pinr: with no kept first message, the summary still says this chat is a builder, so it is stopped from the crew list", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/home/x/p/muster/CREW.md", "new_string": "x"}, transcript_path=sum_b), True),
    ("item box-check-pinr: ...and a manager named only in the summary may edit the crew list", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/home/x/p/muster/CREW.md", "new_string": "x"}, transcript_path=sum_m), False),
    ("item box-check-pinr: ...and a summary that merely mentions a crew name does not make the owner's chat crew", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/home/x/p/muster/CREW.md", "new_string": "x"}, transcript_path=sum_o), False),
    ("item box-check-pinr: a summary-only builder's wrap-up question is refused (item 119)", run("PreToolUse", tool_name="mcp__ccd_turn__wrap_up", tool_input={"recap": "done", "ask": "Ship it?"}, transcript_path=sum_b), True),
    ("D-039: a builder is still stopped from the crew list after a compaction", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/home/x/p/muster/CREW.md", "new_string": "x"}, transcript_path=compacted_b), True),
    ("item 114: a question already put to him is not asked again", run("Stop", last_assistant_message=Q, transcript_path=tr(mgr_first, [asst(Q), usr("<cross-session-message from=x>PASS</cross-session-message>")])), True),
    ("item 114: the same question after he typed something is allowed", run("Stop", last_assistant_message=Q, transcript_path=tr(mgr_first, [asst(Q), usr("hello"), usr("<cross-session-message from=x>PASS</cross-session-message>")])), False),
    ("item 114: a question the Stop hook bounced is not counted as asked", run("Stop", last_assistant_message=Q, transcript_path=tr(mgr_first, [asst(Q), usr("Stop hook feedback: fix it"), asst(Q)])), False),
    ("item 114: a different question is allowed", run("Stop", last_assistant_message=Q.replace("ship the menu fix", "start the new report").replace("wait for the next piece", "park it"), transcript_path=tr(mgr_first, [asst(Q), usr("<cross-session-message from=x>PASS</cross-session-message>")])), False),
    ("item 114: a one-line question already put to him is not asked again", run("Stop", last_assistant_message=QL, transcript_path=tr(mgr_first, [asst(QL), usr("<cross-session-message from=x>PASS</cross-session-message>")])), True),
    ("item 114: the one-line question the first time is allowed", run("Stop", last_assistant_message=QL, transcript_path=tr(mgr_first, [usr("<cross-session-message from=x>PASS</cross-session-message>")])), False),
    ("item 114: the one-line question after he typed something is allowed", run("Stop", last_assistant_message=QL, transcript_path=tr(mgr_first, [asst(QL), usr("go on"), usr("<cross-session-message from=x>PASS</cross-session-message>")])), False),
    ("item 114: a one-line question after the same question as a card is not asked again (any form)", run("Stop", last_assistant_message=QL, transcript_path=tr(mgr_first, [asst(QC), usr("<cross-session-message from=x>PASS</cross-session-message>")])), True),
    ("item 114: the card after the same question as one line is not asked again (any form)", run("Stop", last_assistant_message=QC, transcript_path=tr(mgr_first, [asst(QL), usr("<cross-session-message from=x>PASS</cross-session-message>")])), True),
    ("item 114: a different one-line question is allowed", run("Stop", last_assistant_message="Site order: A (menu fix first) or B (footer first)?", transcript_path=tr(mgr_first, [asst(QL), usr("<cross-session-message from=x>PASS</cross-session-message>")])), False),
    ("item 114: a three-line plain question already put to him is not asked again", run("Stop", last_assistant_message=QM, transcript_path=tr(mgr_first, [asst(QM), usr("<cross-session-message from=x>PASS</cross-session-message>")])), True),
    ("item 114: a three-line question after the same one-liner is not asked again", run("Stop", last_assistant_message=QM, transcript_path=tr(mgr_first, [asst(QL), usr("<cross-session-message from=x>PASS</cross-session-message>")])), True),
    ("item 114: a three-line question the first time is allowed", run("Stop", last_assistant_message=QM, transcript_path=tr(mgr_first, [usr("<cross-session-message from=x>PASS</cross-session-message>")])), False),
    ("item 114: a six-line plain question already put to him is not asked again (any length)", run("Stop", last_assistant_message=QM6, transcript_path=tr(mgr_first, [asst(QM6), usr("<cross-session-message from=x>PASS</cross-session-message>")])), True),
    ("item 114: a six-line question after the same one-liner is not asked again", run("Stop", last_assistant_message=QM6, transcript_path=tr(mgr_first, [asst(QL), usr("<cross-session-message from=x>PASS</cross-session-message>")])), True),
    ("item 114: a '?' inside a web address is not a question", run("Stop", last_assistant_message=QU, transcript_path=tr(mgr_first, [asst(QU), usr("<cross-session-message from=x>PASS</cross-session-message>")])), False),
    ("item 114: a one-line question the Stop hook bounced is not counted as asked", run("Stop", last_assistant_message=QL, transcript_path=tr(mgr_first, [asst(QL), usr("Stop hook feedback: fix it"), asst(QL)])), False),
    ("item 103: 'is waiting for you' in a Working line is allowed", run("Stop", last_assistant_message="Working: Look Cards on the badge fix, and Engine on sources piece 1. The Evidence Web names question is waiting for you.", transcript_path=tr(mgr_first, [usr("<cross-session-message from=x>PASS</cross-session-message>")])), False),
    ("item 114: news riding along with a question is refused", run("Stop", last_assistant_message="The menu fix has PASS and is shipped.\n\n" + Q, transcript_path=tr(mgr_first, [usr("<cross-session-message from=x>PASS</cross-session-message>")])), True),
    ("item 114: the question alone is allowed", run("Stop", last_assistant_message=Q, transcript_path=tr(mgr_first, [usr("<cross-session-message from=x>PASS</cross-session-message>")])), False),
    ("a reply of 'noted' is refused", send("noted", b), True),
    ("'noted, thanks' is refused", send("noted, thanks", b), True),
    ("'Got it. Thanks and will do!' is refused", send("Got it. Thanks and will do!", b), True),
    ("a real message that starts with 'ok' is not called social", "BAD" if "no 'noted'" in send("ok, I will start the build now and report when the test passes", b) else "", False),
    ("a free-form message is refused", send("hey, can you look at this?", b), True),
    ("a READY with no test count is refused", send(good.replace("3/3 passed", "fine"), b), True),
    ("an order that quotes his words goes through", send(order, m), False),
    ("an order without his words quoted is refused", send(order.replace('"do it now"', "do it now"), m), True),
    ("an order with no Accept line is refused", send(order.replace('Accept: "do it now" met\n', ""), m), True),
    ("an order with an empty Accept line is refused", send(order.replace('Accept: "do it now" met', "Accept:"), m), True),
    ("an order with a filled Contract line goes through", send(order.replace("Done: c", "Contract: posts {filter: name}; list page reads it\nDone: c"), m), False),
    ("an order with an empty Contract line is refused", send(order.replace("Done: c", "Contract:\nDone: c"), m), True),
    ("an ID sent twice is refused", send(good, tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good), res("s1")])), True),
    ("a sibling send in the same turn (no result yet) does not use up the ID", send(good, tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good)])), False),
    ("the call's own copy in the transcript does not use up its ID", send(good, tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good)])), False),
    ("a refused send does not use up its ID", send(good, tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good), res("s1", "Muster rule: this report is wrong", True)])), False),
    ("a send that failed in the app does not use up its ID", send(good, tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good), res("s1", "could not deliver", True)])), False),
    ("two parallel sends with different IDs both go through", send(good.replace("x-1", "x-2").replace("builder-x-1", "builder-x-2"), tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", message=good), use("SendMessage", "s2", message=good.replace("builder-x-1", "builder-x-2"))])), False),
    ("a PASS copy to the manager as a message goes through (item 65)", send(good.replace("READY", "PASS").replace("Usage: n", "") .replace("\n\n", "\n").strip(), tr("You are Inspector_Muster_002, agents/inspector.md"), "Manager_Muster_002"), False),
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
    ("item 97: a lettered question that mentions the ship passes", run("Stop", last_assistant_message="**ASK \u00b7 q**\nShip 0.3.80 now?\n\n***A.*** yes, ship it (my pick)\n\n***B.*** hold it", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">PASS: x [ID b-3]</cross-session-message>")])), False),
    ("item 103: 'is waiting for you: type in <name>' is not refused by the 103 rule (it names no chat or window to type in)", run("Stop", last_assistant_message="Builder A is waiting for you: type in Builder A_Muster_002 (shipped work needs your yes).", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">x</cross-session-message>")])), False),
    ("item 97: an empty reply after a worker's message is not asked for text", run("Stop", last_assistant_message="", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">PASS: x [ID b-4]</cross-session-message>")])), False),
    ("item 123: the one working status line passes after a worker's message", run("Stop", last_assistant_message="Working: Engine on rug-archive-seed, Site on launch-signs-show", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">PASS: x [ID b-5]</cross-session-message>")])), False),
    ("item 123: a status line that names progress still passes as the status form", run("Stop", last_assistant_message="Working: Builder A on ship-mod-version (progress: CI)", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">PASS: x [ID b-6]</cross-session-message>")])), False),
    ("item 123: two lines are not the status line", run("Stop", last_assistant_message="Working: Engine on rug-archive-seed\nBuilder passed it, PASS.", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">PASS: x [ID b-7]</cross-session-message>")])), True),
    ("item 123: a line that does not start with Working: and brings news is still refused", run("Stop", last_assistant_message="Engine is working on rug-archive-seed and it shipped.", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">PASS: x [ID b-8]</cross-session-message>")])), True),
    ("item 123: 'Working:' with no job named is refused", run("Stop", last_assistant_message="Working: shipped all of it, PASS", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">PASS: x [ID b-9]</cross-session-message>")])), True),
    ("item 97: his own question may be answered with the news he asked for", run("Stop", last_assistant_message="It is shipped: 0.3.80 is live.", transcript_path=tr("You are Manager_Muster_002", [said("is it shipped yet?")])), False),
    ("item 97: the same report to the same chat unchanged is refused", run("PreToolUse", tool_name="SendMessage", tool_input={"to": "Inspector_Muster_002", "message": good.replace("x-1", "x-2")}, transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", to="Inspector_Muster_002", message=good), res("s1")])), True),
    ("item 97: the same report to another chat as a copy goes through", run("PreToolUse", tool_name="SendMessage", tool_input={"to": "Designer_Muster_002", "message": good.replace("x-1", "x-2")}, transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", to="Inspector_Muster_002", message=good), res("s1")])), False),
    ("item 97: a changed report to the same chat goes through", run("PreToolUse", tool_name="SendMessage", tool_input={"to": "Inspector_Muster_002", "message": good.replace("x-1", "x-2").replace("a\n", "a changed\n", 1)}, transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [use("SendMessage", "s1", to="Inspector_Muster_002", message=good), res("s1")])), False),
    ('item 105: a worker over 300000 tokens is no longer told to renew (it compacts in place)', run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [big(350000)])), False),
    ('item 105: a manager over 300000 tokens is not told to hand over by size', run("Stop", last_assistant_message="**ASK \u00b7 q**\nWhich first?\n\n***A.*** a *(my pick)* reason\n\n***B.*** b", transcript_path=tr("You are Manager_Muster_002", [big(350000)])), False),
    ("item 75: a short reply to HIS typed statement still blocks", run("Stop", last_assistant_message="All done, nice and good.", transcript_path=tr("You are Manager_Muster_002", [said("<cross-session-message from=\"b\">x</cross-session-message>"), said("ok thanks")])), True),
    ("his question, then hook feedback inside his turn: the answer still passes", run("Stop", last_assistant_message="Yes, it is shipped.", transcript_path=tr("You are Manager_Muster_002", [said("well?"), said("Stop hook feedback: rewrite it"), said("<system-reminder>note</system-reminder>")])), False),
    ("his question, then an app event (task notification): long narration blocked", run("Stop", last_assistant_message="The task finished and the result was written to the file and then checked against every one of the notes. " * 4, transcript_path=tr("You are Manager_Muster_002", [said("well?"), said("<system-reminder>[SYSTEM NOTIFICATION] <task-notification>x</task-notification></system-reminder>")])), True),
    ("a question mark in hook feedback or a system note is not his (long reply)", run("Stop", last_assistant_message="Yes, it is shipped and live on the site now, with the new version and every check green on all three systems. " * 4, transcript_path=tr("You are Manager_Muster_002", [said("[SYSTEM NOTIFICATION - NOT USER INPUT] ready?"), said("<system-reminder>really?")])), True),
    ("item 120: a lettered owner question with no heading line is a note, not a refusal", run("Stop", last_assistant_message="Which one?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=m), False),
    ("item 120: a bold line that is not 'WORD \u00b7 job' is no heading (a note)", run("Stop", last_assistant_message="**Score Audit and Monetization chats.**\n\nWhich one?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=m), False),
    ("item 120: a heading line above the choices passes", run("Stop", last_assistant_message="**ASK \u00b7 score-audit**\n\nWhich one?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=m), False),
    ("item 120: a heading below the choices does not count (a note)", run("Stop", last_assistant_message="Which one?\n\n***A.*** yes (my pick)\n\n***B.*** no\n\n**ASK \u00b7 score-audit**", transcript_path=m), False),
    ("a manager question as lettered lines passes", run("Stop", last_assistant_message="**ASK \u00b7 q**\nWhich one?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=m), False),
    ("a manager idle line passes", run("Stop", last_assistant_message="**IDLE · crew**\n\nThe crew is idle. Here's what's next.\n\nHere's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=m), False),
    # item 125: with no worker holding an open order on the board, the manager's turn ends with the idle card or the Working line
    ("item 125: all idle and no card is refused", run("Stop", last_assistant_message="Everything is done.", transcript_path=tr(MG, [said("<task-notification>x")]), cwd=PJ_IDLE), True),
    ("item 125: all idle and no text at all is refused", run("Stop", last_assistant_message="", transcript_path=tr(MG, [said("<task-notification>x")]), cwd=PJ_IDLE), True),
    ("item 125: all idle with the idle card passes", run("Stop", last_assistant_message="**IDLE \u00b7 crew**\n\nThe crew is idle. Here's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=tr(MG, [said("<task-notification>x")]), cwd=PJ_IDLE), False),
    # item 118 (worker-news-line): on a turn a worker's message started, a badge and one plain line; never the empty line
    ("news-line: a badge and one plain line passes", run("Stop", last_assistant_message="**READY \u00b7 login screen**\nApps finished the login screen; Build Inspector has it.", transcript_path=tr(MG, [said(PEER)])), False),
    ("news-line: a PASS badge and one plain line passes", run("Stop", last_assistant_message="**PASS \u00b7 login screen**\nBuild Inspector passed the login screen.", transcript_path=tr(MG, [said(PEER)])), False),
    ("news-line: the empty 'needs nothing from you' line is refused", run("Stop", last_assistant_message="Apps' message needs nothing from you.", transcript_path=tr(MG, [said(PEER)])), True),
    ("news-line: ...and the badge with that empty line under it is refused", run("Stop", last_assistant_message="**READY \u00b7 login screen**\nApps' message needs nothing from you.", transcript_path=tr(MG, [said(PEER)])), True),
    ("news-line: a badge and two news lines is a note, not a refusal", run("Stop", last_assistant_message="**READY \u00b7 login screen**\nApps finished it.\nBuild Inspector has it.", transcript_path=tr(MG, [said(PEER)])), False),
    ("news-line: a badge and a bullet is a note, not a refusal", run("Stop", last_assistant_message="**READY \u00b7 login screen**\n- Apps finished it", transcript_path=tr(MG, [said(PEER)])), False),
    ("news-line: a saved-version code in the line is a note, not a refusal", run("Stop", last_assistant_message="**READY \u00b7 login screen**\nApps finished the login screen at sha 4227291.", transcript_path=tr(MG, [said(PEER)])), False),
    ("news-line: a bare /Users path in the line is a note, not a refusal", run("Stop", last_assistant_message="**READY \u00b7 login screen**\nApps finished it, see /Us" "ers/sam/login.py", transcript_path=tr(MG, [said(PEER)])), False),
    ("news-line: a bare file name in the line is a note, not a refusal", run("Stop", last_assistant_message="**READY \u00b7 login screen**\nApps changed rules-check.py for it.", transcript_path=tr(MG, [said(PEER)])), False),
    ("news-line: a version number in the line is a note, not a refusal", run("Stop", last_assistant_message="**READY \u00b7 login screen**\nApps finished it as version 0.3.146.", transcript_path=tr(MG, [said(PEER)])), False),
    ("news-line: a file shown as a link is fine", run("Stop", last_assistant_message="**READY \u00b7 login screen**\nApps finished the [login page](login.html).", transcript_path=tr(MG, [said(PEER)])), False),
    ("news-line: a repeat of the same badge gets no second line", run("Stop", last_assistant_message="**READY \u00b7 login screen**\nApps finished the login screen again.", transcript_path=tr(MG, [said(PEER), {"type": "assistant", "message": {"content": [{"type": "text", "text": "**READY \u00b7 login screen**\nApps finished the login screen; Build Inspector has it."}]}}, said(PEER)])), True),
    ("news-line: a badge the hook bounced does not count as a repeat", run("Stop", last_assistant_message="**READY \u00b7 login screen**\nApps finished the login screen; Build Inspector has it.", transcript_path=tr(MG, [said(PEER), {"type": "assistant", "message": {"content": [{"type": "text", "text": "**READY \u00b7 login screen**\nApps finished the login screen; Build Inspector has it."}]}}, said("Stop hook feedback: rewrite it")])), False),
    ("news-line: a different job's badge is not a repeat", run("Stop", last_assistant_message="**READY \u00b7 sign-up page**\nApps finished the sign-up page.", transcript_path=tr(MG, [said(PEER), {"type": "assistant", "message": {"content": [{"type": "text", "text": "**READY \u00b7 login screen**\nApps finished the login screen."}]}}, said(PEER)])), False),
    ("news-line: on his own typed turn the badge news is still refused", run("Stop", last_assistant_message="**PASS \u00b7 login screen**\nBuild Inspector passed the login screen.", transcript_path=tr(MG, [said("carry on")])), True),
    # item 118 (idle-card-when-changed): after an idle card, the next one is asked for only when something changed
    ("idle-changed: nothing new since the last card passes", run("Stop", last_assistant_message="Nothing new.", transcript_path=tr(MG, [card(), said("<task-notification>x")]), cwd=PJ_IDLE), False),
    ("idle-changed: no text at all, nothing new, passes", run("Stop", last_assistant_message="", transcript_path=tr(MG, [card(), said("<task-notification>x")]), cwd=PJ_IDLE), False),
    ("idle-changed: a new owner message is a change", run("Stop", last_assistant_message="Done.", transcript_path=tr(MG, [card(), said("please add the thing")]), cwd=PJ_IDLE), True),
    ("idle-changed: a new report is a change", run("Stop", last_assistant_message="Done.", transcript_path=tr(MG, [card(), said(report("p-2"))]), cwd=PJ_IDLE), True),
    ("idle-changed: a repeat of a report seen before the card is not", run("Stop", last_assistant_message="Done.", transcript_path=tr(MG, [said(report("p-1")), card(), said(report("p-1"))]), cwd=PJ_IDLE), False),
    ("idle-changed: other-chat talk that is no report is not", run("Stop", last_assistant_message="Done.", transcript_path=tr(MG, [card(), said("<cross-session-message from=\"b\">got it, thanks</cross-session-message>")]), cwd=PJ_IDLE), False),
    ("idle-changed: a ship after the card is a change", run("Stop", last_assistant_message="Done.", transcript_path=tr(MG, [card(), {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "bash scripts/ship.sh"}}]}}, said("<task-notification>x")]), cwd=PJ_IDLE), True),
    ("idle-changed: a board changed since the card is a change", run("Stop", last_assistant_message="Done.", transcript_path=tr(MG, [card("2000-01-01T00:00:00Z"), said("<task-notification>x")]), cwd=PJ_IDLE), True),
    ("idle-changed: a board older than the card is not", run("Stop", last_assistant_message="Done.", transcript_path=tr(MG, [card("2999-01-01T00:00:00Z"), said("<task-notification>x")]), cwd=PJ_IDLE), False),
    ("idle-changed: a changed turn with the card passes", run("Stop", last_assistant_message="**IDLE \u00b7 crew**\n\nThe crew is idle. Here's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=tr(MG, [card(), said("please add the thing")]), cwd=PJ_IDLE), False),
    ("item 125: an open order and no text passes", run("Stop", last_assistant_message="", transcript_path=tr(MG, [said("<task-notification>x")]), cwd=PJ_BUSY), False),
    ("item 125: an open order and a Working line passes", run("Stop", last_assistant_message="Working: Builder A on idle-card", transcript_path=tr(MG, [said("<task-notification>x")]), cwd=PJ_BUSY), False),
    ("item 125: an open order to the manager itself is not a worker's", run("Stop", last_assistant_message="Done.", transcript_path=tr(MG, [said("<task-notification>x")]), cwd=PJ_MGR), True),
    ("item 125: a closed order is not open", run("Stop", last_assistant_message="Done.", transcript_path=tr(MG, [said("<task-notification>x")]), cwd=PJ_DONE), True),
    ("item 125: no board to read is not judged", run("Stop", last_assistant_message="", transcript_path=tr(MG, [said("<task-notification>x")]), cwd=T), False),
    ("item 125: his own typed words are not bounced", run("Stop", last_assistant_message="Here is the answer.", transcript_path=tr(MG, [said("what is the plan")]), cwd=PJ_IDLE), False),
    ("item 124: a bare idle card is refused", run("Stop", last_assistant_message="The crew is idle.", transcript_path=m), True),
    ("item 124: idle with only one lettered line is refused", run("Stop", last_assistant_message="**IDLE · crew**\n\nThe crew is idle. Here's what's next toward your goal,\n\n***A.*** one (my pick)", transcript_path=m), True),
    ("item 124: idle with two lettered next steps passes", run("Stop", last_assistant_message="**IDLE · crew**\n\nThe crew is idle. Here's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=m), False),
    ("item 103: a manager waiting line is refused", run("Stop", last_assistant_message="Builder A is waiting for you: type in Builder A_Muster_002.", transcript_path=m), True),
    ("item 103: 'type it in the chat' is refused", run("Stop", last_assistant_message="Please type it in the Builder A chat.", transcript_path=m), True),
    ("an unrecorded choice answer blocks the manager", run("Stop", last_assistant_message="ok", transcript_path=tr("You are Manager_Muster_002", [use("AskUserQuestion", questions=[])])), True),
    ("rust-first 1: an answered card names the recorder by its full path, wherever the program runs from", "" if os.path.normpath(os.path.join(HERE, "record-choice.py")) in run("Stop", last_assistant_message="ok", transcript_path=tr("You are Manager_Muster_002", [use("AskUserQuestion", questions=[])])).replace("\\\\", "\\") else "x", False),
    ("a recorded choice answer passes", run("Stop", last_assistant_message="ok", transcript_path=tr("You are Manager_Muster_002", [use("AskUserQuestion", questions=[]), use("Bash", command="python3 scripts/record-choice.py p 3 --picked A")])), False),
    ("a worker card passes", run("Stop", last_assistant_message="**WORKING · x**\n- a\n- b", transcript_path=b), False),
    ("REPORT: a READY card with no message to the manager passes (one-message-once: it goes to the inspector)", run("Stop", last_assistant_message="**READY · x**\n- a\n- b", transcript_path=b), False),
    ("REPORT: a PASS card with no message to the manager is blocked (item 65)", run("Stop", last_assistant_message="**PASS · x**\n- a\n- b", transcript_path=tr("You are Inspector_Muster_002, agents/inspector.md")), True),
    ("REPORT: a READY card sent only to the inspector passes", run("Stop", last_assistant_message="**READY · x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [said("go"), use("SendMessage", "s1", to="Inspector_Muster_002", message="m")])), False),
    ("REPORT: a READY card after a message to the manager passes", run("Stop", last_assistant_message="**READY · x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [said("go"), use("SendMessage", "s1", to="Manager_Muster_002", message="m")])), False),
    ("REPORT: a READY card after the app's send_message to the manager passes", run("Stop", last_assistant_message="**READY · x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [said("go"), use("mcp__ccd_session_mgmt__send_message", "s1", session_id="Manager_Muster_002", message="m")])), False),
    ("a worker reply that is not a card is a note, not a refusal", run("Stop", last_assistant_message="Done.", transcript_path=b), False),
    ("a stop already continued is let through", run("Stop", last_assistant_message="Done.", stop_hook_active=True, transcript_path=b), False),
    ("the owner's own chat is silent at stop", run("Stop", last_assistant_message="Done.", transcript_path=owner), False),
]
# the message form of the lean rebuild (records): the same cases for the Python copy and the Rust copy, key checks in Rust only
REC = '{"v":1,"kind":"PASS","id":"inspector-x-1","job":"x","from":"inspector","to":"builder-a","sha":"abcdef1","need":"none"}'
BI = tr("You are Inspector_Muster_002, agents/inspector.md")  # the sender of a PASS record is an inspector
def send_rec(msg, to="x", cwd=T):
    env = dict(os.environ); env.pop("MUSTER_MESSAGE_FORM", None)
    r = subprocess.run([BIN, "rules"] if BIN else [sys.executable, HOOK], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=cwd, tool_name="SendMessage", tool_input={"to": to, "message": msg}, transcript_path=BI)), capture_output=True, text=True, env=env)
    out = r.stdout.strip()
    return "" if out.startswith('{"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "Muster note') else out  # a pending note is not an answer
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
# item 115: his question gets an answer, not an order; an order in a turn his question started cites his recorded choice
QD = os.path.join(T, "qproj"); os.makedirs(os.path.join(QD, "muster"))
open(os.path.join(QD, "muster", "OWNERS-LIST.md"), "w").write("## Open\n\n35. \"fix the menu\"\n   Choice (2026-11-08): which one?\n     Options: A. a | B. b\n     Picked: A. a\n\n36. \"why is it waiting\"\n   Kind: question\n")
def q_order(item, turn, mgr=True):
    t = tr("You are Manager_Muster_002" if mgr else "You are Builder A_Muster_002, agents/builder.md", turn)
    o = ORD.replace('"item":35', '"item":%d' % item) % ("menu-fix", "menu-fix")
    env = dict(os.environ); env.pop("MUSTER_MESSAGE_FORM", None)
    r = subprocess.run([BIN, "rules"] if BIN else [sys.executable, HOOK], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=QD, tool_name="SendMessage", tool_input={"to": "builder-a", "message": o}, transcript_path=t)), capture_output=True, text=True, env=env)
    return r.stdout.strip()
# right-hand-vision (Part 7): an order that cites a decision number or a vision line is let through in a turn his question started
QV = os.path.join(T, "qvision"); os.makedirs(os.path.join(QV, "muster")); QN = os.path.join(T, "qnovision"); os.makedirs(os.path.join(QN, "muster"))
for _d in (QV, QN):
    open(os.path.join(_d, "muster", "OWNERS-LIST.md"), "w", encoding="utf-8", newline="").write("## Open\n\n36. \"why is it waiting\"\n   Kind: question\n")
    open(os.path.join(_d, "muster", "DECISIONS-LOG.md"), "w", encoding="utf-8", newline="").write("# Decisions log\n\n### D-050 \u00b7 2026-11-01 \u00b7 speed first\nDecision: x\n")
open(os.path.join(QV, "muster", "VISION.md"), "w").write("# Vision\n")
QC = os.path.join(T, "qcrlf"); os.makedirs(os.path.join(QC, "muster"))
open(os.path.join(QC, "muster", "OWNERS-LIST.md"), "w", encoding="utf-8", newline="").write("## Open\n\n36. \"why is it waiting\"\n   Kind: question\n")
open(os.path.join(QC, "muster", "DECISIONS-LOG.md"), "wb").write(b"# Decisions log\r\n\r\n### D-050 \xb7 2026-11-01 \xb7 speed first\r\nDecision: x\r\n")
def cite_order(proj, owner_words, note=None, text=None):
    t = tr("You are Manager_Muster_002", [said("why is the engine waiting?")])
    env = dict(os.environ); env.pop("MUSTER_MESSAGE_FORM", None)
    if text is None:
        o = json.loads(ORD % ("menu-fix", "menu-fix")); o["owner_words"] = owner_words
        if note is not None: o["note"] = note
        msg = json.dumps(o)
    else:
        msg = text; env["MUSTER_MESSAGE_FORM"] = "text"
    r = subprocess.run([BIN, "rules"] if BIN else [sys.executable, HOOK], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=proj, tool_name="SendMessage", tool_input={"to": "builder-a", "message": msg}, transcript_path=t)), capture_output=True, text=True, env=env)
    return "his question gets an answer" in r.stdout
cases += [
    ("right-hand 7: an order citing a decision number in the log is let through in a turn his question started (item 115)", not cite_order(QV, {"decision": "D-050"}), True),
    ("right-hand 7: a decision log with Windows line ends and a non-UTF-8 byte is still read", not cite_order(QC, {"decision": "D-050"}), True),
    ("right-hand 7: ...a decision number that is not in the log is still refused", cite_order(QV, {"decision": "D-099"}), True),
    ("right-hand 7: an order citing a vision line (a Serves: line) is let through when the project has a vision page", not cite_order(QV, {"item": 36}, note="Serves: what the product is for"), True),
    ("right-hand 7: ...a Serves: line with a project that has no vision page is still refused", cite_order(QN, {"item": 36}, note="Serves: what the product is for"), True),
    ("right-hand 7: ...a Serves: line of two words is still refused", cite_order(QV, {"item": 36}, note="Serves: speed"), True),
    ("right-hand 7: an order with no cite is still refused", cite_order(QV, {"item": 36}), True),
    ("right-hand 7: a written order citing a decision number is let through (item 115)", not cite_order(QV, None, text="Job: menu-fix\nOwner's words: item 36, D-050\nDo: x"), True),
    ("right-hand 7: a written order with a Serves: line is let through when the project has a vision page", not cite_order(QV, None, text="Job: menu-fix\nOwner's words: item 36\nServes: what the product is for\nDo: x"), True),
    ("right-hand 7: a written order with neither is still refused", cite_order(QV, None, text="Job: menu-fix\nOwner's words: item 36\nDo: x"), True),
]
cases += [
    ("item 115: an order in a turn his question started is refused", q_order(36, [said("why is the engine waiting?")]), True),
    ("item 115: ...a question word with no question mark counts", q_order(36, [said("why is the engine waiting")]), True),
    ("item 115: ...unless it cites his recorded choice", q_order(35, [said("why is the engine waiting?")]), False),
    ("item 115: an instruction he typed is not a question", q_order(36, [said("fix the menu now")]), False),
    ("item 115: a turn a worker's message started is not his question", q_order(36, [said("why is the engine waiting?"), said("<cross-session-message from=x>PASS</cross-session-message>")]), False),
    ("item 115: a builder's order-shaped message is not this check's business", q_order(36, [said("why is the engine waiting?")], mgr=False), False),
]
def week_order(pct):
    cfg = os.path.join(T, "cfg%s" % pct); os.makedirs(os.path.join(cfg, "muster-usage"), exist_ok=True)
    json.dump({"week_used_percent": pct, "saved_at": 1}, open(os.path.join(cfg, "muster-usage", "a.json"), "w"))
    env = dict(os.environ, CLAUDE_CONFIG_DIR=cfg); env.pop("MUSTER_MESSAGE_FORM", None)
    o = ORD.replace('"item":35', '"item":35') % ("menu-fix", "menu-fix")
    r = subprocess.run([BIN, "rules"] if BIN else [sys.executable, HOOK], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=QD, tool_name="SendMessage", tool_input={"to": "builder-a", "message": o}, transcript_path=tr("You are Manager_Muster_002"))), capture_output=True, text=True, env=env)
    return r.stdout.strip()
cases += [
    ("rust-first 4: a JSON order is held when the week is at 90% (the standing rule), by the reason", "" if "the week is at 90% or more" in week_order(95) else "x", False),
    ("rust-first 4: ...and goes through at 89%", week_order(89), False),
]
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
    ("STOP: a card he skipped needs no record", run("Stop", last_assistant_message="**IDLE · crew**\n\nThe crew is idle.\n\nHere's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=tr(MG, asked("q1", "The user doesn't want to proceed", True))), False),
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
    ("D-037: a typed word that starts with a letter is not an answer", run("Stop", last_assistant_message="**IDLE · crew**\n\nThe crew is idle.\n\nHere's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "***A.*** x (my pick)\n\n***B.*** y"}]}}, said("a quick question first")])), False),
    ("D-037: a typed letter with no lettered question before it is not an answer", run("Stop", last_assistant_message="**IDLE · crew**\n\nThe crew is idle.\n\nHere's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "All done."}]}}, said("a")])), False),
    ("D-037: a letter inside another chat's message is not his answer", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "***A.*** x (my pick)\n\n***B.*** y"}]}}, said("<cross-session-message from=\"x\">a</cross-session-message>")])), False),
    # item 80 addition: the letters are bold and italic, ***A.***
    ("item 80: a bold-italic lettered question passes", run("Stop", last_assistant_message="**ASK \u00b7 q**\nWhich?\n\n***A.*** red (my pick)\n\n***B.*** blue", transcript_path=tr(MG, [said("hi")])), False),
    ("item 80: a bold-only lettered question is flagged", run("Stop", last_assistant_message="Which?\n\n**A.** red\n\n**B.** blue", transcript_path=tr(MG, [said("hi")])), True),
    ("item 80: an italic-only or plain lettered question is flagged", run("Stop", last_assistant_message="Which?\n\n*A.* red\n\n*B.* blue", transcript_path=tr(MG, [said("hi")])), True),
    ("item 80: one wrong letter among right ones is a note, not a refusal", run("Stop", last_assistant_message="**ASK \u00b7 q**\nWhich?\n\n***A.*** red\n\n**B.** blue", transcript_path=tr(MG, [said("hi")])), False),
    ("item 80: his letter after a bold-italic question needs the record", run("Stop", last_assistant_message="Going ahead.", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "***A.*** x (my pick)\n\n***B.*** y"}]}}, said("b")])), True),
    ("item 80: ...and passes once recorded", run("Stop", last_assistant_message="Going ahead.", transcript_path=tr(MG, [{"type": "assistant", "message": {"content": [{"type": "text", "text": "***A.*** x (my pick)\n\n***B.*** y"}]}}, said("b"), use("Bash", command="python3 scripts/record-choice.py x 5 --question q --option 'A. x' --option 'B. y' --picked 'B. y'")])), False),
    ("SHOWFIRST/D-037: a look question card is refused", ask(tr(MG, [said("hi")]), questions=LQ), True),
    ("D-037: a manager card with option previews is refused too", ask(tr(MG, [said("hi")]), questions=LQP), True),
    ("D-037: a manager card after pictures is refused too", ask(tr(MG, [said("hi"), SHOT]), questions=LQ), True),
    ("D-037: any manager card is refused (it locks the chat)", ask(tr(MG, [said("hi")]), questions=[{"question": "Ship it now?", "options": []}]), True),
    ("SHOWFIRST: a worker's card is not this check's business", ask(b, questions=LQ), False),
    ("SHOWFIRST: a look question in a reply with no pictures is blocked", run("Stop", last_assistant_message="**ASK \u00b7 q**\nWhich colour do you prefer?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), True),
    ("SHOWFIRST: ...with pictures shown this turn it passes", run("Stop", last_assistant_message="**ASK \u00b7 q**\nWhich colour do you prefer?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi"), SHOT])), False),
    ("SHOWFIRST (item 88): 'layout' in a list above a non-look question passes", run("Stop", last_assistant_message="**ASK \u00b7 q**\nOpen items: burn layout, site cleanup.\n\nWhich do we push next?\n\n***A.*** the iPhone App Store path (my pick)\n\n***B.*** clear the open site questions", transcript_path=tr(MG, [said("hi")])), False),
    ("SHOWFIRST (item 88): a look word in a choice line only passes", run("Stop", last_assistant_message="**ASK \u00b7 q**\nWhich do we push next?\n\n***A.*** fix the colour of the banner (my pick)\n\n***B.*** clear the open site questions", transcript_path=tr(MG, [said("hi")])), False),
    ("SHOWFIRST (item 88): an idle card with plain next steps passes", run("Stop", last_assistant_message="**IDLE · crew**\n\nThe crew is idle. Here's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=tr(MG, [said("hi")])), False),
    ("SHOWFIRST (item 88): a real look question still blocks", run("Stop", last_assistant_message="**ASK \u00b7 q**\nOpen items: none.\n\nWhich colour do you prefer for the page?\n\n***A.*** blue (my pick)\n\n***B.*** green", transcript_path=tr(MG, [said("hi")])), True),
    ("PICK (item 100): a lettered question with no pick blocks", run("Stop", last_assistant_message="**ASK \u00b7 q**\nShip it now?\n\n***A.*** yes\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), True),
    ("PICK: the same question with a marked pick passes", run("Stop", last_assistant_message="**ASK \u00b7 q**\nShip it now?\n\n***A.*** yes *(my pick: it passed)*\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), False),
    ("PICK: a look question with its pick passes once the pictures were shown", run("Stop", last_assistant_message="**ASK \u00b7 q**\nWhich colour do you prefer?\n\n***A.*** blue *(my pick: it reads best)*\n\n***B.*** green", transcript_path=tr(MG, [said("hi"), SHOT])), False),
    ("PICK: a look question without a pick blocks", run("Stop", last_assistant_message="**ASK \u00b7 q**\nWhich colour do you prefer?\n\n***A.*** blue\n\n***B.*** green", transcript_path=tr(MG, [said("hi"), SHOT])), True),
    ("PICK: a reply with no lettered question is not this check's business", run("Stop", last_assistant_message="**IDLE · crew**\n\nThe crew is idle.\n\nHere's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=tr(MG, [said("hi")])), False),
    ("SHOWFIRST: a question that is not about looks passes", run("Stop", last_assistant_message="**ASK \u00b7 q**\nShip it now?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), False),
    # item 91: two or more lettered choice lines are the question, with or without a question mark
    ("LETTERS: a lead-in ending in a colon plus lettered lines passes", run("Stop", last_assistant_message="**ASK \u00b7 q**\nSentence 5 of 6, on what stays on the phone:\n\n***A.*** the list stays (my pick)\n\n***B.*** only the totals stay\n\n***C.*** nothing stays", transcript_path=tr(MG, [said("hi")])), False),
    ("LETTERS: two lettered lines with a question mark still pass", run("Stop", last_assistant_message="**ASK \u00b7 q**\nKeep it?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), False),
    ("LETTERS: one lone lettered line with no question still blocks", run("Stop", last_assistant_message="**ASK \u00b7 q**\nHere is the thing.\n\n***A.*** yes", transcript_path=tr(MG, [said("hi")])), True),
    ("LETTERS: filler with no lettered lines still blocks", run("Stop", last_assistant_message="On what stays on the phone:\nthe list stays.", transcript_path=tr(MG, [said("hi")])), True),
    # item 88: his question with no question mark is still a question; "looks" in a rules choice is not a look question
    ("ANSWER: his question (no question mark) then a plain two-line answer passes", run("Stop", last_assistant_message="Make up a new one for the keystore.\nIt is not your machine password.", transcript_path=tr(MG, [said("make up a keystore password or is that my machine password")])), False),
    ("ANSWER: a question with a question mark then a plain answer passes", run("Stop", last_assistant_message="Make up a new one for the keystore.\nIt is not your machine password.", transcript_path=tr(MG, [said("should i make up a keystore password?")])), False),
    ("ANSWER: the same plain reply with nothing asked by him is still blocked", run("Stop", last_assistant_message="Make up a new one for the keystore.\nIt is not your machine password.", transcript_path=tr(MG, [said("hi")])), True),
    ("ANSWER: a statement of his that is not a question still blocks a filler reply", run("Stop", last_assistant_message="Make up a new one for the keystore.\nIt is not your machine password.", transcript_path=tr(MG, [said("the build finished overnight")])), True),
    ("LOOKS: a rules choice that says 'looks right' passes without pictures", run("Stop", last_assistant_message="**ASK \u00b7 q**\nWhich rule wording reads right?\n\n***A.*** the short one (my pick)\n\n***B.*** it looks right as written", transcript_path=tr(MG, [said("hi")])), False),
    ("LOOKS: 'look' about the crew's order, not a screen, passes", run("Stop", last_assistant_message="**ASK \u00b7 q**\nShould the manager look at the board first?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), False),
    ("LOOKS: a real visual choice (header on a page) still needs pictures", run("Stop", last_assistant_message="**ASK \u00b7 q**\nShould the header look bigger on the page?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi")])), True),
    ("LOOKS: ...and passes once the pictures were shown", run("Stop", last_assistant_message="**ASK \u00b7 q**\nShould the header look bigger on the page?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("hi"), SHOT])), False),
]
# founder orders (item 76): a manager does not say it cannot do, or argue with, a task he typed
cases += [
    ("FOUNDER: a refusal of a task he typed is blocked", run("Stop", last_assistant_message="I can't do that from here, it would break the board.", transcript_path=tr(MG, [said("archive the old chats now")])), True),
    ("FOUNDER: an argument against his order is blocked", run("Stop", last_assistant_message="I would advise against that. Which one? Pick a letter.", transcript_path=tr(MG, [said("archive the old chats now")])), True),
    ("FOUNDER: doing it and asking one question passes", run("Stop", last_assistant_message="**ASK \u00b7 q**\nWhich chats do you mean?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("archive the old chats now")])), False),
    ("FOUNDER: a refusal is blocked even after one bounce already (no once-per-turn pass)", run("Stop", last_assistant_message="I can't do that from here, it would break the board.", transcript_path=tr(MG, [said("archive the old chats now"), said("Stop hook feedback:\nx")])), True),
    ("FOUNDER: ...even when the stop hook is already active", run("Stop", last_assistant_message="I cannot do that.", stop_hook_active=True, transcript_path=tr(MG, [said("archive the old chats now")])), True),
    ("FOUNDER: one short question is the way through", run("Stop", last_assistant_message="**ASK \u00b7 q**\nI can't tell which chats: do you mean all of them?\n\n***A.*** yes (my pick)\n\n***B.*** no", transcript_path=tr(MG, [said("archive the old chats now")])), False),
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
    ("GROUP: a start followed by the move and the read-back passes", run("Stop", last_assistant_message="**IDLE · crew**\n\nThe crew is idle.\n\nHere's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=tr(MG, [said("start it"), S(initiation="user_asked"), MV, LS])), False),
    ("GROUP: a read-back before the move does not count", run("Stop", last_assistant_message="The crew is idle.", transcript_path=tr(MG, [said("start it"), S(initiation="user_asked"), LS, MV])), True),
    ("GROUP: a card that only proposes a chat is not a start", run("Stop", last_assistant_message="**IDLE · crew**\n\nThe crew is idle.\n\nHere's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=tr(MG, [said("start it"), S(initiation="offer")])), False),
    ("GROUP: a refused step named with the drag line passes", run("Stop", last_assistant_message="**IDLE · crew**\n\nThe crew is idle. The app refused the move: drag Engine_P_006 into the group.\n\nHere's what's next toward your goal,\n\n***A.*** one (my pick)\n\n***B.*** two", transcript_path=tr(MG, [said("start it"), S(initiation="user_asked")])), False),
    ("GROUP: a worker is not checked", run("Stop", last_assistant_message="**WORKING \u00b7 x**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [said("go"), S(initiation="user_asked")])), False),
]

# play-back-shortcut: his message ending with ?? gets the instruction; that turn orders and edits nothing until his yes
def pb(msg, *more):
    return tr(MG, [said(msg)] + list(more))
PB_Q = "**PLAYBACK \u00b7 login**\n\nI heard: the login page should remember the user.\n\n***A.*** Yes, that's it (my pick)\n\n***B.*** Something is off"
PB_ORDER = "To: B\nJob: j\nOwns: a"
prompt = lambda t, text: run("UserPromptSubmit", prompt=text, transcript_path=t)
cases += [
    ("play-back: his message ending ?? gets the instruction", "play back" in prompt(pb("make the login remember me??"), "make the login remember me??"), True),
    ("play-back: trailing space after ?? still counts", "play back" in prompt(pb("x??  "), "x??  "), True),
    ("play-back: one ? does not trigger", prompt(pb("remember me?"), "remember me?"), False),
    ("play-back: ?? in the middle does not trigger", prompt(pb("what?? no way, do it"), "what?? no way, do it"), False),
    ("play-back: three ? is not the mark", prompt(pb("x???"), "x???"), False),
    ("play-back: a peer's message ending ?? does not trigger", prompt(pb("x"), '<cross-session-message from="b">ok??</cross-session-message>'), False),
    ("play-back: a letter pick does not trigger", prompt(pb("B"), "B"), False),
    ("play-back: a worker chat gets no instruction", prompt(tr("You are Builder A_Muster_002", [said("x??")]), "x??"), False),
    ("play-back: an order message is refused that turn", run("PreToolUse", tool_name="SendMessage", tool_input={"to": "x", "message": PB_ORDER}, transcript_path=pb("do it??")), True),
    ("play-back: a file edit is refused that turn", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/p/a.md", "old_string": "a", "new_string": "b"}, transcript_path=pb("do it??")), True),
    ("play-back: starting a chat is refused that turn", run("PreToolUse", tool_name="mcp__ccd_session__start_session", tool_input={"title": "Builder A_X_001"}, transcript_path=pb("do it??")), True),
    ("play-back: a file-writing command is refused that turn", run("PreToolUse", tool_name="Bash", tool_input={"command": "echo hi >> muster/BOARD.md"}, transcript_path=pb("do it??")), True),
    ("play-back: a git commit is refused that turn", run("PreToolUse", tool_name="Bash", tool_input={"command": "git commit -m x"}, transcript_path=pb("do it??")), True),
    ("play-back: reading a file is still allowed", run("PreToolUse", tool_name="Read", tool_input={"file_path": "/p/a.md"}, transcript_path=pb("do it??")), False),
    ("play-back: a read-only command is still allowed", run("PreToolUse", tool_name="Bash", tool_input={"command": "git log --oneline -3 2>&1 | head"}, transcript_path=pb("do it??")), False),
    ("play-back: a reply with no lettered question is refused", run("Stop", last_assistant_message="Heard it.", transcript_path=pb("do it??")), True),
    ("play-back: a reply that plays back and asks A or B passes", run("Stop", last_assistant_message=PB_Q, transcript_path=pb("do it??")), False),
    ("play-back: one ? gets no play-back demand", run("Stop", last_assistant_message="Heard it. On it.", transcript_path=pb("do it?")), False),
    ("play-back: after his yes a file-writing command is allowed", run("PreToolUse", tool_name="Bash", tool_input={"command": "echo hi >> muster/notes.md"}, transcript_path=pb("do it??", {"type": "assistant", "message": {"content": [{"type": "text", "text": PB_Q}]}}, said("A"))), False),
    ("play-back: after his yes a file edit is allowed", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/p/a.md", "old_string": "a", "new_string": "b"}, transcript_path=pb("do it??", said("yes that's it"))), False),
    ("play-back: a peer's report in the turn clears nothing (still his ??)", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/p/a.md", "old_string": "a", "new_string": "b"}, transcript_path=pb("do it??", {"type": "user", "message": {"content": "Stop hook feedback: x"}})), True),
    ("play-back: a turn a worker's message starts is not held (he can forward a READY)", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/p/a.md", "old_string": "a", "new_string": "b"}, transcript_path=pb("do it??", {"type": "assistant", "message": {"content": [{"type": "text", "text": PB_Q}]}}, said(PEER))), False),
    ("play-back: a worker-started turn may send a message", run("PreToolUse", tool_name="SendMessage", tool_input={"to": "x", "message": "noted"}, transcript_path=pb("do it??", said(PEER))) and "play back" in run("PreToolUse", tool_name="SendMessage", tool_input={"to": "x", "message": "noted"}, transcript_path=pb("do it??", said(PEER))), False),
    ("play-back: a worker-started turn needs no A/B question", run("Stop", last_assistant_message="Forwarded.", transcript_path=pb("do it??", said(PEER))) and "play back" in run("Stop", last_assistant_message="Forwarded.", transcript_path=pb("do it??", said(PEER))), False),
    ("play-back: a worker chat is not held to it", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/p/a.md", "old_string": "a", "new_string": "b"}, transcript_path=tr("You are Builder A_Muster_002", [said("do it??")])), False),
]

# manager-known-by-title: a chat whose file opens with a compaction summary is known by its own title (profile pinr)
PINR = dict(RUN_ENV, MUSTER_PROFILE=os.path.join(HERE, "..", "profiles", "pinr.json"))
def runp(ev, **kw):
    r = subprocess.run([BIN, "rules"] if BIN else [sys.executable, HOOK], input=json.dumps(dict(dict(hook_event_name=ev, cwd=T), **kw)), capture_output=True, text=True, env=PINR)
    return r.stdout.strip()
def titled(title, first, *more):
    p = os.path.join(T, "ti%d.jsonl" % next(_tn))
    with open(p, "w") as f:
        f.write(json.dumps({"type": "user", "isCompactSummary": True, "message": {"content": "This session is being continued from a previous conversation that ran out of context."}}) + "\n")
        f.write(json.dumps({"type": "user", "message": {"content": first}}) + "\n")
        for m in more:
            f.write(json.dumps({"type": "user", "message": {"content": m}}) + "\n")
        if title is not None:
            f.write(json.dumps({"type": "custom-title", "customTitle": title, "sessionId": "x"}) + "\n")
    return p
WRAP = dict(tool_name="mcp__ccd_turn__wrap_up", tool_input={"ask": "Which?", "actions": [{"label": "A"}]})
cases += [
    ("title: a summary-first chat titled Manager_PINR gets play-back on ??", "play back" in runp("UserPromptSubmit", prompt="do it??", transcript_path=titled("Manager_PINR", "carry on", "do it??")), True),
    ("title: ...and its wrap-up call with ask and actions is refused", runp("PreToolUse", transcript_path=titled("Manager_PINR", "carry on"), **WRAP), True),
    ("title: a worker titled Builder A_PINR whose first message names its manager is not a manager (no play-back)", runp("UserPromptSubmit", prompt="do it??", transcript_path=titled("Builder A_PINR", "You are Builder A_PINR. Manager_PINR gives the orders.", "do it??")), False),
    ("title: a worker whose first message only mentions Manager_PINR is decided by its title (no play-back)", runp("UserPromptSubmit", prompt="do it??", transcript_path=titled("Builder A_PINR", "report to Manager_PINR_001", "do it??")), False),
    ("title: a chat with no crew title and no crew name stays silent", runp("UserPromptSubmit", prompt="do it??", transcript_path=titled("my own chat", "hello", "do it??")), False),
    ("title: no title record at all stays silent", runp("UserPromptSubmit", prompt="do it??", transcript_path=titled(None, "carry on", "do it??")), False),
]


# one-message-once: a READY goes to the inspector only; a PASS or FAIL comes only from an inspector (house rules, on in Muster by default)
def _rec(kind, to):
    return json.dumps({"v": 1, "kind": kind, "id": "x-" + kind.lower() + "-1", "job": "x", "to": to, "need": "pass_or_fail", "note": "n"})
def _route(first, kind, to, runner=None):
    out = (runner or run)("PreToolUse", tool_name="SendMessage", tool_input={"to": to, "message": _rec(kind, to)}, transcript_path=tr(first))
    return "goes to the inspector only" in out or "only an inspector sends PASS or FAIL" in out
BLD, INS, DSG = "You are Builder A_Muster_002, agents/builder.md", "You are Inspector_Muster_002, agents/inspector.md", "You are Designer_Muster_002, agents/designer.md"
_once = [
    ("one-message-once: a builder's READY to the manager is refused", _route(BLD, "READY", "Manager_Muster_002"), True),
    ("one-message-once: a builder's READY to the inspector goes through", _route(BLD, "READY", "Inspector_Muster_002"), False),
    ("one-message-once: a designer's READY to the manager is refused", _route(DSG, "READY", "Manager_Muster_002"), True),
    ("one-message-once: a builder's PASS is refused", _route(BLD, "PASS", "Manager_Muster_002"), True),
    ("one-message-once: a builder's relayed FAIL is refused", _route(BLD, "FAIL", "Manager_Muster_002"), True),
    ("one-message-once: a designer's PASS is refused", _route(DSG, "PASS", "Builder_Muster_002"), True),
    ("one-message-once: an inspector's PASS to the builder goes through", _route(INS, "PASS", "Builder A_Muster_002"), False),
    ("one-message-once: an inspector's PASS to the manager goes through", _route(INS, "PASS", "Manager_Muster_002"), False),
    ("one-message-once: a design inspector's FAIL goes through", _route("You are Design Inspector_Muster_002, agents/design-inspector.md", "FAIL", "Manager_Muster_002"), False),
    ("one-message-once: the manager's own PASS copy goes through", _route(MG, "PASS", "Builder A_Muster_002"), False),
    ("one-message-once: a builder's NEED to the manager goes through", _route(BLD, "NEED", "Manager_Muster_002"), False),
    ("one-message-once: a chat whose name is not known is let through", _route("hello there", "PASS", "Manager_Muster_002"), False),
    ("one-message-once: the refusal says where the news goes", "inspector sends the manager its copy" in run("PreToolUse", tool_name="SendMessage", tool_input={"to": "Manager_Muster_002", "message": _rec("READY", "Manager_Muster_002")}, transcript_path=tr(BLD)), True),
    ("one-message-once: PINR is not touched (a builder's READY to the manager still goes)", _route("You are Builder A_PINR_002, agents/builder.md", "READY", "Manager_PINR_002", runp), False),
    ("one-message-once: PINR is not touched (a builder's PASS still goes)", _route("You are Builder A_PINR_002, agents/builder.md", "PASS", "Manager_PINR_002", runp), False),
    ("one-message-once: PINR still needs a READY card's message to the manager", runp("Stop", last_assistant_message="**READY · x**\n- a\n- b", transcript_path=tr("You are Builder A_PINR_002, agents/builder.md")), True),
]
# several crews in one project (item 134): a crew's records, its own manager and inspector; nothing changes for a one-crew name
EVB, EVI = "You are Builder A Evidence_Muster_001, agents/builder.md", "You are Inspector Evidence_Muster_001, agents/inspector.md"
EVM = "You are Manager Evidence_Muster_001"
_CR = os.path.join(T, "proj", "muster")
def _wr(first, rel, tool="Write"):
    return run("PreToolUse", tool_name=tool, tool_input={"file_path": os.path.join(_CR, rel), "content": "x"}, transcript_path=tr(first))
def _sh(first, cmd):
    return run("PreToolUse", tool_name="Bash", tool_input={"command": cmd}, transcript_path=tr(first), cwd=os.path.join(T, "proj"))
def _ev(first, kind, to):
    return run("PreToolUse", tool_name="SendMessage", tool_input={"to": to, "message": _rec(kind, to)}, transcript_path=tr(first))
_once += [
    ("several-crews: a crew chat writes its own crew's board", _wr(EVB, "crews/evidence/BOARD.md"), False),
    ("several-crews: a crew chat writing another crew's board is refused", "crew-records" in _wr(EVB, "crews/other/BOARD.md"), True),
    ("several-crews: a crew chat writing the main board is refused", "crew-records" in _wr(EVB, "BOARD.md"), True),
    ("several-crews: a crew chat writing the shared decisions is refused", "crew-records" in _wr(EVB, "DECISIONS-LOG.md", "Edit"), True),
    ("several-crews: the main crew writing a crew's board is refused", "crew-records" in _wr(BLD, "crews/evidence/BOARD.md"), True),
    ("several-crews: the main manager writing a crew's board is refused", "crew-records" in _wr(MG, "crews/evidence/BOARD.md"), True),
    ("several-crews: the main crew writes the main board as before", _wr(BLD, "BOARD.md"), False),
    ("several-crews: a crew manager writes its own crew's owner list", _wr(EVM, "crews/evidence/OWNERS-LIST.md"), False),
    ("several-crews: a crew chat writing another crew's file by shell is refused", "crew-records" in _sh(EVB, "echo x >> muster/crews/other/BOARD.md"), True),
    ("several-crews: a crew chat writing its own file by shell goes through", _sh(EVB, "echo x >> muster/crews/evidence/BOARD.md"), False),
    ("several-crews: a crew builder's READY to its own crew's manager is refused (it goes to the inspector)", "goes to the inspector only" in _ev(EVB, "READY", "Manager Evidence_Muster_001"), True),
    ("several-crews: a crew builder's READY to its inspector goes through", "goes to the inspector only" in _ev(EVB, "READY", "Inspector Evidence_Muster_001"), False),
    ("several-crews: a crew inspector's PASS to its manager goes through", "only an inspector sends" in _ev(EVI, "PASS", "Manager Evidence_Muster_001"), False),
    ("several-crews: a crew builder's PASS is refused", "only an inspector sends" in _ev(EVB, "PASS", "Manager Evidence_Muster_001"), True),
    ("several-crews: a crew card with no message to its manager is refused", run("Stop", last_assistant_message="**DONE \u00b7 x**\n- a\n- b", transcript_path=tr(EVB)), True),
    ("several-crews: a crew card after a message to its own manager passes", run("Stop", last_assistant_message="**DONE \u00b7 x**\n- a\n- b", transcript_path=tr(EVB, [said("go"), use("SendMessage", "s9", to="Manager Evidence_Muster_001", message="x"), res("s9")])), False),
    ("several-crews: a crew card after a message only to the main manager is refused", run("Stop", last_assistant_message="**DONE \u00b7 x**\n- a\n- b", transcript_path=tr(EVB, [said("go"), use("SendMessage", "s8", to="Manager_Muster_002", message="x"), res("s8")])), True),
]
# right-hand part 2 (item 128): an ANSWER and a VIEW are let through; the wording checks become notes (told once, never a refusal); the hard stops stay
LONG = " ".join("The build is slow because the first step waits for the whole folder, and that step reads every file." for _ in range(12))
ANS = "**ANSWER \u00b7 slow-build**\n\n" + LONG
VIEW = "**VIEW \u00b7 slow-build**\n\n" + LONG
WRONGLETTER = "**ASK \u00b7 q**\nWhich?\n\n***A.*** red *(my pick)* because it is nearest\n\n**B.** blue"
ASKED = [said("why is the build slow?")]
TYPED = [said("make the build faster")]
PEERT = [said(PEER)]
def told(t, ev="UserPromptSubmit", **kw):
    """what the chat is told (as added context) at its next event; '' when nothing"""
    return run_raw(ev, prompt="go on", transcript_path=t, **kw)
def stop_then_told(first, extra, text, ev="UserPromptSubmit", **kw):
    t = tr(first, extra)
    out = run_raw("Stop", last_assistant_message=text, transcript_path=t)
    return out, told(t, ev, **kw), told(t, ev, **kw)
_n1 = stop_then_told(MG, [said("hi")], WRONGLETTER)
NOTE_LETTERS = "" if (_n1[0] == "" and "bold and italic" in _n1[1] and "Muster note" in _n1[1] and _n1[2] == "") else "BAD"
_n2 = stop_then_told("You are Builder A_Muster_002, agents/builder.md", [said("go")], "Done.")
_n3 = stop_then_told(MG, PEERT, "**READY \u00b7 login screen**\n- Apps finished it\nsee rules-check.py")
_n4 = stop_then_told(MG, [said("hi")], WRONGLETTER, ev="PreToolUse", tool_name="Read", tool_input={"file_path": "/p/a"})
_n5t = tr(MG, [said("hi")])
run_raw("Stop", last_assistant_message=WRONGLETTER, transcript_path=_n5t)
_n5 = run_raw("PreToolUse", tool_name="SendMessage", tool_input={"to": "x", "message": "noted"}, transcript_path=_n5t)  # a refusal comes first
_n5b = told(_n5t)  # ...and the note waits for the next event
cases += [
    ("right-hand 2c: an ANSWER on a turn he started with a question is let through at any length", run("Stop", last_assistant_message=ANS, transcript_path=tr(MG, ASKED)), False),
    ("right-hand 2c: ...the same long reply with no title is refused", run("Stop", last_assistant_message=LONG, transcript_path=tr(MG, ASKED + [said("ok")] + PEERT)), True),
    ("right-hand 2c: an ANSWER on a turn he started with an instruction (no question) is not let through", run("Stop", last_assistant_message=ANS, transcript_path=tr(MG, TYPED)), True),
    ("right-hand 2c: an ANSWER on a turn another chat started is not let through", run("Stop", last_assistant_message=ANS, transcript_path=tr(MG, ASKED + PEERT)), True),
    ("right-hand 2c: a VIEW is let through on a turn he started with a question", run("Stop", last_assistant_message=VIEW, transcript_path=tr(MG, ASKED)), False),
    ("right-hand 2c: a VIEW is let through on a turn he started with an instruction", run("Stop", last_assistant_message=VIEW, transcript_path=tr(MG, TYPED)), False),
    ("right-hand 2c: a VIEW is let through on a turn another chat started", run("Stop", last_assistant_message=VIEW, transcript_path=tr(MG, PEERT)), False),
    ("right-hand 2c: a title with no job is no title", run("Stop", last_assistant_message="**VIEW**\n\n" + LONG, transcript_path=tr(MG, PEERT)), True),
    ("right-hand 2c: a turn another chat started still ends with no text: long news is refused", run("Stop", last_assistant_message="The build passed and it is shipped. " + LONG, transcript_path=tr(MG, PEERT)), True),
    ("right-hand 2c: ...one short news line per job is still allowed", run("Stop", last_assistant_message="**READY \u00b7 login screen**\nApps finished the login screen; Build Inspector has it.", transcript_path=tr(MG, PEERT)), False),
    ("right-hand 2d hard stop: a VIEW that sends him to type in a worker's chat is refused (item 103)", run("Stop", last_assistant_message=VIEW + "\n\nPlease type in the Builder chat.", transcript_path=tr(MG, PEERT)), True),
    ("right-hand 2d hard stop: a VIEW that puts a waiting question to him again is refused (item 114)", run("Stop", last_assistant_message="**VIEW \u00b7 order**\n\n" + QL, transcript_path=tr(MG, [asst(QL), said(PEER)])), True),
    ("right-hand 2d hard stop: ...the first time it is let through", run("Stop", last_assistant_message="**VIEW \u00b7 order**\n\n" + QL, transcript_path=tr(MG, PEERT)), False),
    ("right-hand 2d hard stop: a VIEW with lettered choices and no pick is refused (item 100)", run("Stop", last_assistant_message="**VIEW \u00b7 order**\n\nWhich?\n\n***A.*** one\n\n***B.*** two", transcript_path=tr(MG, PEERT)), True),
    ("right-hand 2d hard stop: an answered choice card not recorded is still refused", run("Stop", last_assistant_message=VIEW, transcript_path=tr(MG, [said("hi"), use("AskUserQuestion", "q1", questions=[{"question": "Which?", "options": [{"label": "A"}, {"label": "B"}]}]), res("q1", "A")])), True),
    ("right-hand 2d hard stop: a choice card is still refused (it locks his chat)", ask(tr(MG, [said("hi")]), questions=LQ), True),
    ("right-hand 2d hard stop: an order in a turn his question started without his recorded choice is still refused (item 115)", q_order(36, [said("why is the engine waiting?")]), True),
    ("right-hand 2d hard stop: a worker's report that does not reach the manager as a message is still refused (item 65)", run("Stop", last_assistant_message="**DONE \u00b7 job**\n- a\n- b", transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [said("go")])), True),
    ("right-hand 2d hard stop: the manager-only files stay manager-only", run("PreToolUse", tool_name="Edit", tool_input={"file_path": "/p/muster/OWNERS-LIST.md", "old_string": "a", "new_string": "b"}, transcript_path=tr("You are Builder A_Muster_002, agents/builder.md", [said("go")])), True),
    ("right-hand 2d notes: a letter style not bold and italic is let through, and the chat is told once at its next prompt", NOTE_LETTERS, False),
    ("right-hand 2d notes: a worker's card with no title and bullets is let through, then told once", "" if (_n2[0] == "" and "end-of-turn reply is a card" in _n2[1] and _n2[2] == "") else "BAD", False),
    ("right-hand 2d notes: a news line with a second line, a bullet and a bare path is let through, then told once", "" if (_n3[0] == "" and "ONE plain line" in _n3[1] and _n3[2] == "") else "BAD", False),
    ("right-hand 2d notes: the note also arrives at the next tool call", "" if (_n4[0] == "" and "Muster note" in _n4[1] and '"hookEventName": "PreToolUse"' in _n4[1]) else "BAD", False),
    ("right-hand 2d notes: a refusal at the next tool call comes first and the note waits", "" if ("deny" in _n5 and "Muster note" not in _n5 and "bold and italic" in _n5b) else "BAD", False),
    ("right-hand 2d notes: a chat with nothing pending is told nothing", told(tr(MG, [said("hi")])), False),
    ("right-hand 2d notes: the owner's own chat is told nothing", told(tr("hello there", [said("hi")])), False),
    ("right-hand 2e: 'I cannot' with no choices is still refused", run("Stop", last_assistant_message="I cannot do that, sorry.", transcript_path=tr(MG, TYPED)), True),
    ("right-hand 2e: not possible as asked, with the reason and lettered choices, is let through", run("Stop", last_assistant_message="**ASK \u00b7 build**\n\nThat is not possible as asked: the build tool reads the whole folder.\n\n***A.*** use the cache *(my pick)* because it is nearest\n\n***B.*** split the folder", transcript_path=tr(MG, TYPED)), False),
    ("right-hand 2e: arguing with the order is still refused even with choices", run("Stop", last_assistant_message="**ASK \u00b7 build**\n\nI disagree with this.\n\n***A.*** use the cache *(my pick)* because it is nearest\n\n***B.*** split the folder", transcript_path=tr(MG, TYPED)), True),
    ("right-hand 2e: a VIEW may say 'I disagree' (that is a view)", run("Stop", last_assistant_message="**VIEW \u00b7 build**\n\nI disagree with splitting the folder: " + LONG, transcript_path=tr(MG, TYPED)), False),
    ("right-hand 2e: a VIEW that only says 'I cannot' with no choices is still refused", run("Stop", last_assistant_message="**VIEW \u00b7 build**\n\nI cannot do that.", transcript_path=tr(MG, TYPED)), True),
]
# right-hand 4 (Part 4 of the right-hand page): safety stops and house rules, one list (docs/checks.md). Every refusal above is replayed under a
# profile that switches every house rule off, and under one that switches off only its own rule. A house rule switched off is silent; a safety stop
# still refuses with every switch off. Each refusal names its group and the rule.
import re as _re
_page = open(os.path.join(HERE, "..", "docs", "checks.md"), encoding="utf-8").read()
LISTED = {m.group(1): m.group(2) for m in _re.finditer(r"^\| `([a-z-]+)` \| (safety stop|house rule) \|", _page, _re.M)}
HOUSE = sorted(k for k, g in LISTED.items() if g == "house rule")
LABEL = _re.compile(r'\[(safety stop|house rule) \\?"([a-z-]+)\\?"')
def _profile(off, basep=None):
    p = os.path.join(T, "prof_%d.json" % next(_tn))
    base = json.load(open(basep)) if basep else {"name": "Other"}  # a call that already ran under a project profile keeps what that profile says
    base["house_rules"] = {k: False for k in off}
    json.dump(base, open(p, "w"))
    return p
def _replay(call, off):
    cmd, inp, env, _ = call
    r = _real_run(cmd, input=inp, capture_output=True, text=True, env=dict(env or os.environ, MUSTER_PROFILE=_profile(off, (env or {}).get("MUSTER_PROFILE"))))
    return r.stdout.strip()
def _is_refusal(o):
    return '"permissionDecision": "deny"' in o or '"decision": "block"' in o
# calls under a project's own profile: the guard (item 117, protected folders) and a project's manager-only files
_gprot = os.path.join(T, "protd"); os.makedirs(_gprot)
for _pdict, _tool, _inp in (({"name": "G", "guard": {"protected_folders": [_gprot]}}, "Write", {"file_path": os.path.join(_gprot, "a.txt"), "content": "key = " + "AKIA" + "ABCDEFGHIJKLMNOP"}),
                            ({"name": "Prot", "protected": ["/Founder/LIST\\.md$"]}, "Bash", {"command": "echo x > /p/Founder/LIST.md"})):
    _pp = os.path.join(T, "own_%d.json" % next(_tn)); json.dump(_pdict, open(_pp, "w"))
    subprocess.run([BIN, "rules"] if BIN else [sys.executable, HOOK], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=T, tool_name=_tool, tool_input=_inp, transcript_path=b)), capture_output=True, text=True, env=dict(RUN_ENV, MUSTER_PROFILE=_pp))
_seen = {}
for call in list(CALLS):
    if _is_refusal(call[3]):
        mm = LABEL.search(call[3])
        if mm and mm.group(2) not in _seen:
            _seen[mm.group(2)] = call
_rcases = [("right-hand 4: every refusal names its group and rule, and the rule is on the page", "" if _seen and all(k in LISTED and LISTED[k] == LABEL.search(v[3]).group(1) for k, v in _seen.items()) else "BAD " + str([k for k in _seen if k not in LISTED]), False)]
for rid, call in sorted(_seen.items()):
    if LISTED.get(rid) == "safety stop":
        _rcases.append(("right-hand 4: safety stop '%s' still refuses with every switch off" % rid, "" if ('"%s"' % rid) in _replay(call, HOUSE).replace('\\"', '"') else "BAD", False))
    else:
        o1 = _replay(call, [rid])
        o2 = _replay(call, HOUSE)
        _rcases.append(("right-hand 4: house rule '%s' is silent with its switch off" % rid, "" if ('"%s"' % rid) not in o1.replace('\\"', '"') else "BAD " + o1[:200], False))
        _rcases.append(("right-hand 4: ...and with every house rule off only safety stops speak (%s)" % rid, "" if (not o2 or all(g == "safety stop" for g, _ in LABEL.findall(o2.replace('\\"', '"')))) else "BAD " + o2[:200], False))
_rcases.append(("right-hand 4: the guard is a safety stop, not a house rule", "" if LISTED.get("guard") == "safety stop" else "BAD", False))
_needed = set(LISTED) - {"note-letters", "note-heading", "note-badge-line", "note-card", "talk-note", "board-pick-claim", "queue-waiting", "queue-idle", "idle-sweep", "idle-silent"} - ({"note-shape", "order-action"} if BIN else set())
_seen_ids = set(_seen)
_rcases.append(("right-hand 4: every listed refusing check of the rules hook is reached by a case here (missing: %s)" % ", ".join(sorted(_needed - _seen_ids)), "" if not (_needed - _seen_ids) else "BAD", False))
# the wording notes and the other checks: each house rule silent with its switch off, the same input speaking with it on
def _off_env(rid):
    pp = os.path.join(T, "off_%d.json" % next(_tn)); json.dump({"name": "Other", "house_rules": {k: False for k in ([rid] if isinstance(rid, str) else rid)}}, open(pp, "w"))
    return dict(RUN_ENV, MUSTER_PROFILE=pp)
def _note_after(env, first, extra, text):
    t = tr(first, extra)
    subprocess.run([BIN, "rules"] if BIN else [sys.executable, HOOK], input=json.dumps(dict(hook_event_name="Stop", cwd=T, last_assistant_message=text, transcript_path=t)), capture_output=True, text=True, env=env)
    return open(t + ".muster-notes", encoding="utf-8").read() if os.path.exists(t + ".muster-notes") else ""
BCARD = "You are Builder A_Muster_002, agents/builder.md"
for _rid, _first, _extra, _text, _phrase in (("note-letters", MG, [said("hi")], WRONGLETTER, "bold and italic"),
                                             ("note-card", BCARD, [said("go")], "Done.", "end-of-turn reply is a card"),
                                             ("note-badge-line", MG, PEERT, "**READY \u00b7 login screen**\n- Apps finished it\nsee rules-check.py", "ONE plain line"),
                                             ("note-heading", MG, [said("hi")], "Which first?\n\n***A.*** ship the fix *(my pick)* because it is small\n\n***B.*** wait", "bold heading line")):
    _rcases.append(("right-hand 4: the note '%s' is kept by default" % _rid, "" if _phrase in _note_after(RUN_ENV, _first, _extra, _text) else "BAD", False))
    _rcases.append(("right-hand 4: ...and never kept with its switch off (%s)" % _rid, "" if _note_after(_off_env(_rid), _first, _extra, _text) == "" else "BAD", False))
    _rcases.append(("right-hand 4: ...a different switch off keeps it (%s)" % _rid, "" if _phrase in _note_after(_off_env("no-thanks"), _first, _extra, _text) else "BAD", False))
# told-when-asked: the owner's standing "tell me when X" lets one ANSWER about X through on a later turn, whoever started it
SAF = "**ANSWER \u00b7 safari-fix**\n\nThe safari fix is LIVE and shipped. " + LONG
def _said_asst(t): return {"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}
_TELL = said("tell me when the safari fix is live")
cases += [
    ("told-when-asked: his 'tell me when the safari fix is live', then a peer-started turn with an ANSWER about it, passes", run("Stop", last_assistant_message=SAF, transcript_path=tr(MG, [_TELL, _said_asst("ok"), said(PEER)])), False),
    ("told-when-asked: 'let me know when ...' and 'ping me when ...' work the same", run("Stop", last_assistant_message=SAF, transcript_path=tr(MG, [said("let me know when safari is fixed"), said(PEER)])), False),
    ("told-when-asked: the same reply with no such request is still refused", run("Stop", last_assistant_message=SAF, transcript_path=tr(MG, [said("fix safari"), said(PEER)])), True),
    ("told-when-asked: a second reply for the same request is refused", run("Stop", last_assistant_message=SAF, transcript_path=tr(MG, [_TELL, _said_asst(SAF), said(PEER)])), True),
    ("told-when-asked: a reply the Stop hook bounced does not use up the request", run("Stop", last_assistant_message=SAF, transcript_path=tr(MG, [_TELL, _said_asst(SAF), said("Stop hook feedback: Muster rule: no"), said(PEER)])), False),
    ("told-when-asked: an ANSWER about something else is still refused", run("Stop", last_assistant_message=SAF.replace("safari", "android"), transcript_path=tr(MG, [_TELL, said(PEER)])), True),
    ("told-when-asked: a reply with no ANSWER title is still refused", run("Stop", last_assistant_message=SAF.replace("**ANSWER \u00b7 safari-fix**\n\n", ""), transcript_path=tr(MG, [_TELL, said(PEER)])), True),
    ("told-when-asked: a request with no key word (only 'live') ties to nothing", run("Stop", last_assistant_message=SAF, transcript_path=tr(MG, [said("tell me when it is live"), said(PEER)])), True),
]
# right-hand choice-bullet-note: a letter written inside a list line is noted; bare letter lines are not
BULLETED = "**ASK \u00b7 q**\nWhich first?\n\n- ***A.*** ship the fix *(my pick)* because it is small\n- ***B.*** wait"
BARELETTERS = "**ASK \u00b7 q**\nWhich first?\n\n***A.*** ship the fix *(my pick)* because it is small\n\n***B.*** wait"
_rcases.append(("choice-bullet-note: Manager_PINR's reply shape (letters in list lines) gets the note", "" if "no bullet" in _note_after(RUN_ENV, MG, [said("hi")], BULLETED) else "BAD", False))
_rcases.append(("choice-bullet-note: star bullets and plain letters in a list get it too", "" if "no bullet" in _note_after(RUN_ENV, MG, [said("hi")], "Which?\n\n* **A.** red\n* **B.** blue") else "BAD", False))
_rcases.append(("choice-bullet-note: bare bold-italic letter lines get no note", "" if "no bullet" not in _note_after(RUN_ENV, MG, [said("hi")], BARELETTERS) else "BAD", False))
_rcases.append(("choice-bullet-note: one bulleted line alone (not a choice) gets none", "" if _note_after(RUN_ENV, MG, [said("hi")], "Done.\n\n- A. one thing") == "" or "no bullet" not in _note_after(RUN_ENV, MG, [said("hi")], "Done.\n\n- A. one thing") else "BAD", False))
# talk-note: the owner's reply with a bare path
TALKCMD = [BIN, "talk"] if BIN else [sys.executable, os.path.join(HERE, "..", "hooks", "talk-check.py")]
def _talk(env):
    t = tr(BCARD, [said("go")])
    subprocess.run(TALKCMD, input=json.dumps(dict(hook_event_name="Stop", cwd=T, last_assistant_message="**DONE \u00b7 x**\n- changed hooks/rules-check.py", transcript_path=t)), capture_output=True, text=True, env=env)
    return open(t + ".muster-notes", encoding="utf-8").read() if os.path.exists(t + ".muster-notes") else ""
_rcases.append(("right-hand 4: the note 'talk-note' is kept by default", "" if "bare file path" in _talk(RUN_ENV) else "BAD", False))
_rcases.append(("right-hand 4: ...and never kept with its switch off", "" if _talk(_off_env("talk-note")) == "" else "BAD", False))
_pf = os.path.join(T, "tc_false.json"); json.dump({"talk_check": False}, open(_pf, "w"))
_rcases.append(("right-hand 4: ...the older switch name talk_check:false does the same", "" if _talk(dict(RUN_ENV, MUSTER_PROFILE=_pf)) == "" else "BAD", False))
# board-stop: the claim of choosing for the owner
def _bstop_off(rid, said_):
    d = tempfile.mkdtemp(dir=T); os.makedirs(os.path.join(d, "muster"))
    open(os.path.join(d, "muster", "BOARD.md"), "w", encoding="utf-8").write("# Board\n")
    env = dict(_off_env(rid) if rid else RUN_ENV, MUSTER_ASSUME_MANAGER="1")
    return subprocess.run([BIN, "board-stop"] if BIN else [sys.executable, BSH], input=json.dumps(dict(hook_event_name="Stop", cwd=d, last_assistant_message=said_, transcript_path=tr(MG))), capture_output=True, text=True, env=env).stdout.strip()
_claim = "I went with option A and I am recording it for him."
_rcases.append(("right-hand 4: 'board-pick-claim' refuses a claim of choosing for the owner, naming the rule", "" if 'house rule \\"board-pick-claim\\"' in _bstop_off(None, _claim) else "BAD", False))
_rcases.append(("right-hand 4: ...and is silent with its switch off", "" if _bstop_off("board-pick-claim", _claim) == "" else "BAD", False))
# the idle manager check and the worker-queue check (their Python copies): a house rule off says nothing
import importlib.util as _ilu, io as _io, contextlib as _cl
def _load(name, path):
    sp = _ilu.spec_from_file_location(name, os.path.join(HERE, path)); m = _ilu.module_from_spec(sp); sp.loader.exec_module(m); return m
for _mn, _path, _rids in (("idle_mod", "idle-check.py", ("idle-sweep", "idle-silent")), ("wq_mod", "worker-queue-check.py", ("queue-waiting", "queue-idle"))):
    _m = _load(_mn, _path)
    for _rid in _rids:
        _m.PROFILE = {}
        _b1 = _io.StringIO()
        with _cl.redirect_stdout(_b1):
            _m.say_block(_rid, "Do not go idle." + _m.NOREPEAT)
        _m.PROFILE = {"house_rules": {_rid: False}}
        _b2 = _io.StringIO()
        with _cl.redirect_stdout(_b2):
            _m.say_block(_rid, "Do not go idle." + _m.NOREPEAT)
        _rcases.append(("right-hand 4: '%s' (%s) names its rule, and is silent with its switch off" % (_rid, _path), "" if ('house rule \\"%s\\"' % _rid) in _b1.getvalue() and _b2.getvalue() == "" else "BAD " + _b1.getvalue()[:120], False))
# the list page and the code say the same: every name the checks use is on the page with its group, every refusing name on the page is in both copies
def _ids(files, pat):
    out = set()
    for f in files:
        out |= set(_re.findall(pat, open(os.path.join(HERE, "..", f), encoding="utf-8").read()))
    return out
_PY = _ids(["hooks/rules-check.py", "hooks/board-stop.py", "scripts/idle-check.py", "scripts/worker-queue-check.py"], r'(?:deny|block|say_block|note_add)\(\s*(?:data\.get\("transcript_path"\) or "",\s*)?"([a-z-]+)"') | {"talk-note"}
_RS = _ids(["checks/src/rules.rs", "checks/src/boardstop.rs", "checks/src/idle.rs", "checks/src/wq.rs", "checks/src/talk.rs"], r'(?:deny|block|say_block|note_add|refuse|reply)\((?:tpath, |s\(&data, "transcript_path"\), )?"([a-z-]+)"') | {"note-secret", "record-form"}
_PYONLY = {"note-shape", "order-action"}  # the program's record check carries these under record-form
_rcases.append(("right-hand 4: the Python copy uses exactly the names on the page (extra: %s; missing: %s)" % (sorted(_PY - set(LISTED)), sorted(set(LISTED) - _PY)), "" if _PY == set(LISTED) else "BAD", False))
_rcases.append(("right-hand 4: the program uses exactly the names on the page (extra: %s; missing: %s)" % (sorted(_RS - set(LISTED)), sorted(set(LISTED) - _PYONLY - _RS)), "" if _RS == set(LISTED) - _PYONLY else "BAD", False))
_safe_py = _re.search(r"SAFETY = \{([^}]*)\}", open(os.path.join(HERE, "..", "hooks", "rules-check.py"), encoding="utf-8").read()).group(1)
_safe_rs = _re.search(r"pub const SAFETY: \[&str; \d+\] = \[([^\]]*)\]", open(os.path.join(HERE, "..", "checks", "src", "common.rs"), encoding="utf-8").read()).group(1)
_sp = set(_re.findall(r'"([a-z-]+)"', _safe_py)); _sr = set(_re.findall(r'"([a-z-]+)"', _safe_rs))
_rcases.append(("right-hand 4: the safety stops in both copies are exactly the page's safety stops", "" if _sp == _sr == {k for k, g in LISTED.items() if g == "safety stop"} else "BAD %s %s" % (sorted(_sp), sorted(_sr)), False))
_ntemp = {}
# redo-loop-less (item 132): a refusal names every fault it found, so a message is rewritten once
def _refusal(msg, first=MG, text=False, to="inspector"):
    env = dict(RUN_ENV); env.pop("MUSTER_MESSAGE_FORM", None)
    if text: env["MUSTER_MESSAGE_FORM"] = "text"
    r = subprocess.run([BIN, "rules"] if BIN else [sys.executable, HOOK], input=json.dumps(dict(hook_event_name="PreToolUse", cwd=T, tool_name="SendMessage", tool_input={"to": to, "message": msg}, transcript_path=tr(first))), capture_output=True, text=True, env=env)
    return r.stdout
_bad_rec = json.dumps({"v": 2, "kind": "READY", "id": "wrong", "job": "x", "from": "builder-a", "to": "inspector", "need": "pass_or_fail", "note": "n" * 450, "extra": 1})
_o1 = _refusal(_bad_rec, BLD)
_bad_ord = "To: B\nJob: j\nOwner's words: no quotes here\nOwns: a\nOut:\nAccept:\nDone: c"
_o2 = _refusal(_bad_ord, MG, text=True, to="Builder A_Muster_002")
cases += [] if not BIN else [  # the record check is the program's; the older Python copy only refuses plain sentences
    ("redo-loop-less: one refusal names a wrong version, a wrong id, a long note and an unknown key together", all(w in _o1 for w in ("v must be 1", "id must be", "note is 450", "unknown key 'extra'")), True),
    ("redo-loop-less: ...and the missing sha, tests, touches and usage of a READY in the same answer", all(w in _o1 for w in ("a READY needs sha", "a READY needs tests", "a READY needs touches", "a READY needs usage")), True),
]
cases += [
    ("redo-loop-less: a written order lists every empty line and the missing quotes in one answer", all(w in _o2 for w in ("'Out:'", "'Accept:'", "quote his words")), True),
]

cases += _once
cases += _rcases
if os.environ.get("MUSTER_CALLS_OUT"):  # for scripts/rules-apart-diff.py: every call of the rules and board-stop checks, to be replayed under a profile
    json.dump([[("bin" if (BIN and c[0][0] == BIN) else "py"), c[0][1], c[1], {k: v for k, v in (c[2] or os.environ).items() if k.startswith("MUSTER_") or k == "CLAUDE_CONFIG_DIR"}] for c in CALLS], open(os.environ["MUSTER_CALLS_OUT"], "w"))
bad = 0
for name, out, should_block in cases:
    ok = bool(out) == should_block
    bad += not ok
    print(("ok   " if ok else "MISS ") + name)
print("%d of %d passed" % (len(cases) - bad, len(cases)))
sys.exit(1 if bad else 0)
