#!/usr/bin/env python3
"""Self-test for the handover rules (item 101) in hooks/rules-check.py, the ready-built Rust copy (set MUSTER_CHECKS_BIN) and scripts/idle-check.py,
on a made-up project: (2) a manager the crew list replaced ends silent and gets no idle demand; (3) once the new manager runs, every running worker
must be told its name and id, and a worker's report must go to the manager in force; (4) then the outgoing manager archives itself.
Prints PASS/FAIL lines; exit 1 on any failure."""
import json, os, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "..", "hooks", "rules-check.py")
IDLE = os.path.join(HERE, "idle-check.py")
BIN = os.environ.get("MUSTER_CHECKS_BIN")
cid = lambda n: "local_" + ("%d" % n) * 8 + "-1111-1111-1111-" + ("%d" % n) * 12
OLD, NEW, WA, WB = 1, 2, 3, 4
bad = 0
def t(name, ok):
    global bad; bad += (not ok); print(("PASS " if ok else "FAIL ") + name)

def project(new_running=True, new_row=True):
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, "muster")); sd = os.path.join(d, "s", "a", "b"); os.makedirs(sd)
    rows = [("Manager_H_001", OLD)] + ([("Manager_H_002", NEW)] if new_row else []) + [("Builder A_H_001", WA), ("Inspector_H_001", WB)]
    open(os.path.join(d, "muster", "CREW.md"), "w").write("## Running now\n| Name | Model | Effort | Folder | Chat id | Started |\n|---|---|---|---|---|---|\n" +
        "".join("| %s | m | medium | f | %s | d |\n" % (n, cid(i)) for n, i in rows) +
        "\n## Archived\n| Manager_H_000 | m | d | none |\n| Manager_H_009 | m | d | none |\n")
    open(os.path.join(d, "muster", "BOARD.md"), "w").write("")
    open(os.path.join(d, "muster", "OWNERS-LIST.md"), "w").write("## Open\n1. \"a\"\n   Stands: with Builder A_H_001\n\n## Closed\n")
    for n, i in rows:
        arch = (i == NEW and not new_running)
        json.dump({"title": n, "sessionId": cid(i), "isArchived": arch, "lastActivityAt": int(time.time() * 1000) - 900000}, open(os.path.join(sd, cid(i) + ".json"), "w"))
    return d, os.path.join(d, "s")

def transcript(first, sends=()):
    p = os.path.join(tempfile.mkdtemp(), "t.jsonl")
    with open(p, "w") as f:
        f.write(json.dumps({"type": "user", "message": {"content": first}}) + "\n")
        f.write(json.dumps({"type": "user", "message": {"content": "<cross-session-message from=\"x\">DONE</cross-session-message>"}}) + "\n")
        for k, (to, msg) in enumerate(sends):
            f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "s%d" % k, "name": "SendMessage", "input": {"to": to, "message": msg}}]}}) + "\n")
    return p

def hook(d, sd, tp, text="", **extra):
    ev = dict(hook_event_name="Stop", cwd=d, last_assistant_message=text, transcript_path=tp, **extra)
    env = dict(os.environ, MUSTER_SESSIONS_DIR=sd, MUSTER_MESSAGE_FORM="text")
    cmd = [BIN, "rules"] if BIN else [sys.executable, HOOK]
    return subprocess.run(cmd, input=json.dumps(ev), capture_output=True, text=True, env=env).stdout

FIRST_OLD = "You are Manager_H_001, the manager."
TOLD = "The new manager is Manager_H_002, chat id %s." % cid(NEW)
d, sd = project()
o = hook(d, sd, transcript(FIRST_OLD))
t("handover: the outgoing manager is told to tell both workers", "block" in o and "Builder A_H_001" in o and "Inspector_H_001" in o and cid(NEW) in o)
t("handover: ... and to archive itself", "archive_session" in o and '\\"self\\"' in o or "archive_session" in o and "self" in o)
o = hook(d, sd, transcript(FIRST_OLD, [(cid(WA), TOLD)]))
t("handover: a worker already told is not named again", "Inspector_H_001" in o and "Builder A_H_001" not in o)
o = hook(d, sd, transcript(FIRST_OLD, [(cid(WA), TOLD), ("Inspector_H_001", TOLD)]))
t("handover: all told: only the archive step is asked", "block" in o and "tell each" not in o and "archive_session" in o)
t("handover: a message without the new id does not count", "Builder A_H_001" in hook(d, sd, transcript(FIRST_OLD, [(cid(WA), "the manager changed")])))
t("handover: no text and no owner demand: a text reply is not bounced for form", "lettered" not in hook(d, sd, transcript(FIRST_OLD), "PASS: all good, shipped"))
t("handover: it never loops", hook(d, sd, transcript(FIRST_OLD), "", stop_hook_active=True) == "")
d2, sd2 = project(new_running=False)
t("handover: a new manager that does not run yet gets no demand, and the old one may end silent", hook(d2, sd2, transcript(FIRST_OLD), "PASS: x shipped") == "")
d3, sd3 = project(new_row=False)
t("handover: no newer manager in the crew list: the usual rules apply", "never tell the owner" in hook(d3, sd3, transcript(FIRST_OLD), "PASS: x shipped"))
t("handover: the new manager itself is not the outgoing one", "handover" not in hook(d, sd, transcript("You are Manager_H_002, the manager."), ""))
tp = transcript(FIRST_OLD)
open(tp, "a").write(json.dumps({"type": "user", "message": {"content": "status please"}}) + "\n")
t("handover: his own typed words still get the usual rules", "never tell the owner" in hook(d, sd, tp, "PASS: x shipped") and "handover" not in hook(d, sd, tp, "PASS: x shipped"))

# (3) a worker's report goes to the manager in force
WCARD = "**DONE · job**\n- did it\n- 3 of 3 passed"
def worker(sends):
    return transcript("You are Builder A_H_001, agents/builder.md", sends)
for label, to, blocked in [("the old manager's name", "Manager_H_001", True), ("the old manager's id", cid(OLD), True),
                           ("the new manager's id", cid(NEW), False), ("the new manager's name", "Manager_H_002", False), ("an archived older manager's name", "Manager_H_009", True)]:
    o = hook(d, sd, worker([(to, "x")]), WCARD)
    t("report check: a report sent to %s is %s" % (label, "refused" if blocked else "accepted"), ("block" in o) == blocked)
t("report check: the refusal names the manager in force", "Manager_H_002" in hook(d, sd, worker([("Manager_H_001", "x")]), WCARD) and cid(NEW) in hook(d, sd, worker([("Manager_H_001", "x")]), WCARD))
dn = tempfile.mkdtemp()
t("report check: with no crew list, any Manager name still counts (as before)", hook(dn, sd, worker([("Manager_Q_007", "x")]), WCARD) == "")

# (2) the idle check: a manager the crew list replaced owes nothing
env = dict(os.environ, MUSTER_SESSIONS_DIR=sd, MUSTER_STATE_DIR=tempfile.mkdtemp(), MUSTER_NO_SWEEP="1")
def idle(d, tp):
    return subprocess.run([sys.executable, IDLE, "--project", d], input=json.dumps({"last_assistant_message": "ok", "transcript_path": tp}), capture_output=True, text=True, env=env).stdout
t("idle: the current manager is still asked about an idle worker with open work", "block" in idle(d, transcript("You are Manager_H_002, the manager.")))
t("idle: the outgoing manager gets no idle card or demand", idle(d, transcript(FIRST_OLD)) == "")
t("idle: a manager named only in passing is not taken for the outgoing one", "block" in idle(d, transcript("You are Manager_H_002. Manager_H_001 has handed over.")))
sys.exit(1 if bad else 0)
