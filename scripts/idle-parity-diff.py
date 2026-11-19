#!/usr/bin/env python3
"""Parity check (rust-first piece 5): feeds the idle check's Python copy and the Rust program's idle-check command the same pretend Stop events
and lists every one where they answer differently (what they print, the exit code, and what each leaves in its "already said" file). The events
are every call idle-check-selftest.py makes, plus the same call with other last messages, no message, empty input, bad JSON and a non-object.
Needs MUSTER_CHECKS_BIN. Prints the differences; exit 1 on any. Standard library only.
Usage: MUSTER_CHECKS_BIN=<program> python3 scripts/idle-parity-diff.py"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.environ.get("MUSTER_CHECKS_BIN")
if not BIN:
    sys.exit("set MUSTER_CHECKS_BIN to the Rust program")
real_run = subprocess.run
MESSAGES = ["done", "", "ok", "Builder Q_X_001, Builder R_X_001 and Builder T_X_001 are on it", "Builder Q_X_001 and Builder R_X_001 are on it",
            "Releasing Builder U_X_001", "The crew is idle.", "**IDLE · crew**\n- Builder A_Y_001: since 14:02, why: nothing open, unblocked by: an order\n\n***A.*** one\n\n***B.*** two",
            "Giving Builder B_Z_001 its next order", "BUILDER Q_X_001 ON IT"]
diffs = []
count = [0]


def state_snapshot(d):
    out = {}
    for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        try:
            out[n] = open(os.path.join(d, n), encoding="utf-8").read()
        except OSError:
            pass
    return out


def one(cmd, kw, label):
    """Run both copies from the same starting 'already said' folder, each on its own copy, and compare what they print and leave behind."""
    count[0] += 1
    env = dict(kw.get("env") or os.environ)
    state = env.get("MUSTER_STATE_DIR")
    res = []
    for which in ("py", "rs"):
        sd = tempfile.mkdtemp()
        if state and os.path.isdir(state):
            shutil.rmtree(sd)
            shutil.copytree(state, sd)
        e = dict(env, MUSTER_STATE_DIR=sd)
        c = cmd
        if which == "rs":
            exe = BIN
            folder = os.path.dirname(os.path.abspath(str(cmd[1])))
            if os.path.basename(folder) == ".muster-checks":  # the installed copy: the program sits where the Python copy does
                exe = os.path.join(folder, "muster-checks" + (".exe" if os.name == "nt" else ""))
                if not os.path.exists(exe):
                    shutil.copy(BIN, exe)
            c = [exe, "idle-check"] + cmd[2:]
        r = real_run(c, **dict(kw, env=e, capture_output=True, text=True, encoding="utf-8"))
        out = re.sub(r" idle \d+s:", " idle Ns:", r.stdout) if "--list" in cmd else r.stdout  # the seconds idle tick between the two runs
        res.append((out, r.returncode, state_snapshot(sd)))
    if res[0] != res[1]:
        diffs.append((label, str(kw.get("input", ""))[:300], str(res[0])[:400], str(res[1])[:400]))


def patched(cmd, *a, **kw):
    if isinstance(cmd, list) and len(cmd) >= 2 and os.path.basename(str(cmd[1])) == "idle-check.py" and cmd[0] == sys.executable:
        one(cmd, kw, "as run")
        try:
            ev = json.loads(kw.get("input") or "")
        except ValueError:
            ev = None
        if isinstance(ev, dict):
            for m in MESSAGES:
                one(cmd, dict(kw, input=json.dumps(dict(ev, last_assistant_message=m))), "message %r" % m)
            gone = {k: v for k, v in ev.items() if k != "last_assistant_message"}
            one(cmd, dict(kw, input=json.dumps(gone)), "no message")
            one(cmd, dict(kw, input=json.dumps(dict(ev, stop_hook_active=True))), "stop hook active")
            one(cmd, dict(kw, input=""), "empty input")
            one(cmd, dict(kw, input="not json"), "bad json")
            one(cmd, dict(kw, input="[1]"), "not an object")
        one(cmd + ["--list"], dict(kw, input=""), "--list")
    return real_run(cmd, *a, **kw)


subprocess.run = patched
src = open(os.path.join(HERE, "idle-check-selftest.py"), encoding="utf-8").read()
os.environ.pop("MUSTER_CHECKS_BIN", None)
os.environ["MUSTER_IDLE_PASS"] = "python"
g = {"__name__": "selftest", "__file__": os.path.join(HERE, "idle-check-selftest.py")}
try:
    exec(compile(src, "idle-check-selftest.py", "exec"), g)
except SystemExit:
    pass
print("%d runs compared, %d differences" % (count[0], len(diffs)))
for label, inp, py, rs in diffs[:40]:
    print("DIFF %s\n  input  %s\n  python %s\n  rust   %s" % (label, inp, py, rs))
sys.exit(1 if diffs else 0)
