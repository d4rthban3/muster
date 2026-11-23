#!/usr/bin/env python3
"""Self-test for hooks/other-computer-changes.sh (item 133): the other computer's new CHANGES.md lines, once per chat.
Runs the real hook in temporary project folders. Prints the pass count; exit 1 on any failure."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "..", "hooks", "other-computer-changes.sh")
fails = []
n = 0


def check(name, cond, extra=""):
    global n
    n += 1
    if not cond:
        fails.append(name + (": " + extra if extra else ""))


def run(proj, sid="chat-1", me="alpha", seen=None, cap=None, event="UserPromptSubmit", raw=None):
    env = dict(os.environ, MUSTER_COMPUTER=me, MUSTER_SEEN_DIR=seen)
    env.pop("MUSTER_CHANGES_CAP", None)
    if cap:
        env["MUSTER_CHANGES_CAP"] = str(cap)
    data = raw if raw is not None else json.dumps({"hook_event_name": event, "session_id": sid, "cwd": proj})
    p = subprocess.run(["sh", HOOK], input=data, capture_output=True, text=True, env=env, cwd=proj, timeout=30)
    return p.returncode, p.stdout, p.stderr


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def add(path, text):
    with open(path, "a") as f:
        f.write(text)


with tempfile.TemporaryDirectory() as t:
    proj = os.path.join(t, "proj")
    seen = os.path.join(t, "seen")
    a_log = os.path.join(t, "alpha Workspace", "CHANGES.md")
    b_log = os.path.join(t, "beta Workspace", "CHANGES.md")
    put(a_log, "a1\n")
    put(b_log, "b1\nb2\n")

    # 1. no computers.txt: nothing, exit 0, nothing written
    os.makedirs(os.path.join(proj, "muster"))
    rc, out, err = run(proj, seen=seen)
    check("off without computers.txt", rc == 0 and out == "" and not os.path.exists(seen))

    # 2. one computer named: still off
    put(os.path.join(proj, "muster", "computers.txt"), "alpha = ../alpha Workspace/CHANGES.md\n")
    rc, out, err = run(proj, seen=seen)
    check("off with one computer", rc == 0 and out == "" and not os.path.exists(seen))

    # 3. two computers: first turn shows the other's lines
    put(os.path.join(proj, "muster", "computers.txt"),
        "# the two computers\nalpha = ../alpha Workspace/CHANGES.md\nbeta = ../beta Workspace/CHANGES.md  # second\n")
    rc, out, err = run(proj, seen=seen)
    check("first turn shows the other's lines", rc == 0 and "b1" in out and "b2" in out and "a1" not in out, out)
    check("names the computer and the log", "beta" in out and "2 new lines" in out and b_log in out, out)

    # 4. same chat, next turn: nothing
    rc, out, err = run(proj, seen=seen)
    check("printed once, not again", rc == 0 and out == "", out)

    # 5. new line: only the new line
    add(b_log, "b3\n")
    rc, out, err = run(proj, seen=seen)
    check("only the new line", "b3" in out and "b1" not in out and "1 new line " in out, out)

    # 6. a second chat sees them once too
    rc, out, err = run(proj, sid="chat-2", seen=seen)
    check("second chat sees them", "b1" in out and "b3" in out, out)
    rc, out, err = run(proj, sid="chat-2", seen=seen)
    check("second chat once only", out == "", out)

    # 7. the other direction: beta reads alpha's log, never beta's own
    rc, out, err = run(proj, sid="chat-3", me="beta", seen=seen)
    check("works from the other computer", "a1" in out and "b1" not in out and "alpha" in out, out)

    # 8. this computer's own log growing prints nothing
    add(a_log, "a2\n")
    rc, out, err = run(proj, sid="chat-1", me="alpha", seen=seen)
    check("own log never printed", out == "", out)

    # 9. neither line is this computer: off
    rc, out, err = run(proj, sid="chat-9", me="gamma", seen=seen)
    check("unknown computer: off", rc == 0 and out == "")

    # 10. long news is capped, newest kept, count of the rest said
    add(b_log, "".join("n%02d\n" % i for i in range(30)))
    rc, out, err = run(proj, sid="chat-1", seen=seen, cap=5)
    lines = out.strip().splitlines()
    check("capped", len(lines) == 1 + 1 + 5 and "n29" in out and "n24" not in out, out)
    check("says how many were left out", "25 earlier lines not shown" in out, out)

    # 11. missing or unreadable log: no output, exit 0
    os.rename(b_log, b_log + ".gone")
    rc, out, err = run(proj, sid="chat-5", seen=seen)
    check("missing log: silent exit 0", rc == 0 and out == "" and err == "", out + err)
    os.rename(b_log + ".gone", b_log)
    if os.geteuid() != 0:
        os.chmod(b_log, 0)
        rc, out, err = run(proj, sid="chat-6", seen=seen)
        check("unreadable log: silent exit 0", rc == 0 and out == "" and err == "", out + err)
        os.chmod(b_log, 0o644)

    # 12. garbage on input, other events, unusable seen folder: never a failure
    rc, out, err = run(proj, sid="chat-7", seen=seen, raw="not json")
    check("bad input does not fail", rc == 0)
    rc, out, err = run(proj, sid="chat-8", seen=seen, event="Stop")
    check("other events print nothing", rc == 0 and out == "")
    blocked = os.path.join(t, "blocked")
    put(blocked, "a file, not a folder")
    rc, out, err = run(proj, sid="chat-10", seen=blocked)
    check("unusable seen folder: still exit 0, lines shown", rc == 0 and "n29" in out, out + err)

    # 13. a log that got shorter prints nothing and the mark catches up
    put(b_log, "only\n")
    rc, out, err = run(proj, sid="chat-1", seen=seen)
    check("shorter log: no flood", rc == 0 and out == "", out)
    add(b_log, "next\n")
    rc, out, err = run(proj, sid="chat-1", seen=seen)
    check("after a rewrite, new lines show again", "next" in out and "only" not in out, out)

    # 14. runs from a folder inside the project (a worker's copy)
    sub = os.path.join(proj, "sub", "deeper")
    os.makedirs(sub)
    rc, out, err = run(sub, sid="chat-11", seen=seen)
    check("found from a folder inside the project", "next" in out, out)

    # 15. the log is never written
    with open(b_log) as f:
        check("log untouched", f.read() == "only\nnext\n")

print("%d checks, %d failed" % (n, len(fails)))
for f in fails:
    print("FAIL: " + f)
sys.exit(1 if fails else 0)
