#!/usr/bin/env python3
"""Parity check (rust-first piece 4): feeds the worker queue check's Python copy and the Rust program's worker-queue command the same pretend
Stop events and lists every one where they answer differently. The events are every call worker-queue-check-selftest.py makes, plus the same
call with other last messages (naming nothing, naming the job, waiting on the manager, an empty message, no message at all).
Needs MUSTER_CHECKS_BIN. Prints the differences; exit 1 on any. Standard library only.
Usage: MUSTER_CHECKS_BIN=<program> python3 scripts/worker-queue-parity-diff.py"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.environ.get("MUSTER_CHECKS_BIN")
if not BIN:
    sys.exit("set MUSTER_CHECKS_BIN to the Rust program")
real_run = subprocess.run
MESSAGES = ["done", "", "job-one", "waiting on job-one and item 1: inspector", "Waiting on the manager's choice.", "WAIT: the route; Manager's choice",
            "I need to edit the manager page next", "Needs the manager to pick one", "Burns route is live.", "waiting on Look_P_002", "JOB-ONE ITEM 1"]
diffs = []
count = [0]


def compare(cmd, kw, label):
    count[0] += 1
    py = real_run(cmd, **kw)
    rs = real_run([BIN, "worker-queue"] + cmd[2:], **kw)
    if (py.stdout, py.returncode) != (rs.stdout, rs.returncode):
        diffs.append((label, str(kw.get("input", ""))[:300], py.stdout.strip()[:300], rs.stdout.strip()[:300]))


def patched(cmd, *a, **kw):
    if isinstance(cmd, list) and len(cmd) >= 2 and cmd[0] == sys.executable and os.path.basename(str(cmd[1])) == "worker-queue-check.py":
        kw = dict(kw, capture_output=True, text=True)
        compare(cmd, kw, "as run")
        try:
            ev = json.loads(kw.get("input") or "")
        except ValueError:
            ev = None
        if isinstance(ev, dict):
            for m in MESSAGES:
                compare(cmd, dict(kw, input=json.dumps(dict(ev, last_assistant_message=m))), "message %r" % m)
            gone = {k: v for k, v in ev.items() if k != "last_assistant_message"}
            compare(cmd, dict(kw, input=json.dumps(gone)), "no message")
            compare(cmd, dict(kw, input=""), "empty input")
            compare(cmd, dict(kw, input="not json"), "bad json")
            compare(cmd, dict(kw, input="[1]"), "not an object")
    return real_run(cmd, *a, **kw)


subprocess.run = patched
src = open(os.path.join(HERE, "worker-queue-check-selftest.py"), encoding="utf-8").read()
os.environ.pop("MUSTER_CHECKS_BIN", None)
os.environ["MUSTER_WQ_PASS"] = "python"
g = {"__name__": "selftest", "__file__": os.path.join(HERE, "worker-queue-check-selftest.py")}
try:
    exec(compile(src, "worker-queue-check-selftest.py", "exec"), g)
except SystemExit:
    pass
print("%d runs compared, %d differences" % (count[0], len(diffs)))
for label, inp, py, rs in diffs:
    print("--", label, "\n  in:", inp, "\n  python:", py, "\n  rust:  ", rs)
sys.exit(1 if diffs else 0)
