#!/usr/bin/env python3
"""Parity fuzz (rust-first piece 1): builds many message records (a good one of each kind, then every key left out, set to an odd value, or
added) and sends each, as a SendMessage from several kinds of chat, to the Python rules-check and to the Rust program. Prints every message
one of them lets through and the other refuses. 'python allows, rust refuses' is the program being stricter (listed, fine); 'python refuses,
rust allows' is a gap in the program (exit 1). Needs MUSTER_CHECKS_BIN. Writes only in a temporary folder. Standard library only."""
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "..", "hooks", "rules-check.py")
BIN = os.environ.get("MUSTER_CHECKS_BIN")
if not BIN:
    sys.exit("set MUSTER_CHECKS_BIN to the Rust program")
T = tempfile.mkdtemp()
ENV = dict((k, v) for k, v in os.environ.items() if k not in ("MUSTER_PROFILE", "MUSTER_MESSAGE_FORM"))
ENV["MUSTER_STATE_DIR"] = T
FIRSTS = {"manager": "You are Manager_Muster_002", "builder": "You are Builder A_Muster_002, agents/builder.md", "inspector": "You are Inspector_Muster_002"}
TRANS = {}
for k, v in FIRSTS.items():
    p = os.path.join(T, k + ".jsonl")
    open(p, "w").write(json.dumps({"type": "user", "message": {"content": v}}) + "\n")
    TRANS[k] = p
PROJ = os.path.join(T, "proj")
os.makedirs(os.path.join(PROJ, "muster"))
open(os.path.join(PROJ, "muster", "BOARD.md"), "w").write("# Board\n\n## Entries\n")
for d in ("agents", "scripts", "checks"):
    os.makedirs(os.path.join(PROJ, d))
GOAL = os.path.join(T, "goalproj")
os.makedirs(os.path.join(GOAL, "muster"))
open(os.path.join(GOAL, "muster", "GOAL.md"), "w").write('Goal (his words): "ship the menu"\nDone when: live\nSet list (jobs):\n- a-job\n')

BASE = {
    "READY": {"v": 1, "kind": "READY", "id": "builder-a-job-1", "job": "job", "from": "builder-a", "to": "inspector", "sha": "abcdef1", "version": "1.2.3",
              "tests": {"passed": 3, "failed": 0}, "touches": ["board"], "need": "pass_or_fail", "usage": {"week_pct": 10}},
    "DONE": {"v": 1, "kind": "DONE", "id": "builder-a-job-2", "job": "job", "from": "builder-a", "to": "manager", "need": "none", "usage": {"week_pct": 10}},
    "PASS": {"v": 1, "kind": "PASS", "id": "inspector-job-1", "job": "job", "from": "inspector", "to": "builder-a", "sha": "abcdef1", "need": "none"},
    "FAIL": {"v": 1, "kind": "FAIL", "id": "inspector-job-2", "job": "job", "from": "inspector", "to": "builder-a", "sha": "abcdef1", "need": "fix"},
    "STUCK": {"v": 1, "kind": "STUCK", "id": "builder-a-job-3", "job": "job", "from": "builder-a", "to": "manager", "need": "unblock"},
    "NEED": {"v": 1, "kind": "NEED", "id": "builder-a-job-4", "job": "job", "from": "builder-a", "to": "manager", "need": "order"},
    "OWNER_CALL": {"v": 1, "kind": "OWNER_CALL", "id": "builder-a-job-5", "job": "job", "from": "builder-a", "to": "manager", "need": "owner_answer"},
    "ORDER": {"v": 1, "kind": "ORDER", "id": "manager-job-1", "job": "job", "from": "manager", "to": "builder-a", "owner_words": {"item": 12}, "owns": ["board"],
              "out": ["site"], "action": "start", "need": "none"},
}
ODD = [None, "", 0, 1, -1, True, "x y", "A", "Z" * 60, "none", "go", [], ["board"], ["nothing-here"], {}, {"item": 1}, {"item": "x"},
       {"passed": 1, "failed": 0}, {"passed": 0, "failed": 0}, {"week_pct": 5}, {"week_pct": 500}, "1.2", "abcdef", "manager", "builder-aa", "board", "owner", "a-job",
       "x\ny", "token=abcdef", "plain note", "n" * 401]
msgs = []
for kind, rec in BASE.items():
    msgs.append(rec)
    for key in list(rec) + ["note", "action", "version", "sha", "tests", "touches", "usage", "owner_words", "owns", "out", "extra"]:
        d = dict(rec)
        d.pop(key, None)
        msgs.append(d)
        for v in ODD:
            d = dict(rec)
            d[key] = v
            msgs.append(d)
    for k2, v2 in BASE.items():
        if k2 != kind:
            msgs.append(dict(rec, kind=k2))
seen, uniq = set(), []
for m in msgs:
    s = json.dumps(m, sort_keys=True)
    if s not in seen:
        seen.add(s)
        uniq.append(m)
def sender(m):
    f = str(m.get("from"))
    return "manager" if f == "manager" else "inspector" if f.startswith("inspector") else "builder"


jobs = [(m, sender(m), PROJ) for m in uniq] + [(m, "manager", GOAL) for m in uniq if m.get("kind") == "ORDER"]


def verdict(out):
    out = out.strip()
    if not out:
        return "allow"
    try:
        d = json.loads(out)
    except ValueError:
        return "odd"
    return "deny" if "deny" in out or d.get("decision") == "block" else "allow"


def one(job):
    m, role, cwd = job
    ev = json.dumps({"hook_event_name": "PreToolUse", "cwd": cwd, "tool_name": "SendMessage", "transcript_path": TRANS[role],
                     "tool_input": {"to": m.get("to", "x") if isinstance(m.get("to"), str) else "x", "message": json.dumps(m)}})
    py = subprocess.run([sys.executable, HOOK], input=ev, capture_output=True, text=True, env=ENV)
    rs = subprocess.run([BIN, "rules"], input=ev, capture_output=True, text=True, env=ENV)
    return job, verdict(py.stdout), verdict(rs.stdout), py.stdout.strip()[:300], rs.stdout.strip()[:300]


with ThreadPoolExecutor(8) as ex:
    results = list(ex.map(one, jobs))
gaps = [r for r in results if r[1] == "deny" and r[2] != "deny"]
stricter = [r for r in results if r[1] != "deny" and r[2] == "deny"]
print("%d messages sent, python refuses and rust allows: %d; python allows and rust refuses: %d" % (len(results), len(gaps), len(stricter)))
import collections
import re
why = collections.Counter()
ex_ = {}
for r in stricter:  # group the stricter refusals by the reason the program gives (numbers and names folded away)
    k = re.sub(r"'[^']*'|\d+", "_", r[4].split("is wrong:")[-1].strip())[:110]
    why[k] += 1
    ex_.setdefault(k, r)
if "--why" in sys.argv:
    for k, n in why.most_common():
        print("%6d  %s\n          e.g. %s" % (n, k, json.dumps(ex_[k][0][0])[:200]))
shown = set()
for r in gaps:
    key = r[3][:120]
    if key in shown:
        continue
    shown.add(key)
    print("GAP", json.dumps(r[0][0]), "as", r[0][1], "in", os.path.basename(r[0][2]), "\n   python:", r[3], "\n   rust:  ", r[4])
sys.exit(1 if gaps else 0)
