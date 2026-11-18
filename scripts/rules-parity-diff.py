#!/usr/bin/env python3
"""Parity check (rust-first piece 1): feeds the same pretend hook events to the Python copy of a check and to the Rust program and lists
every event where they answer differently. The events are every call a self-test makes (rules-check-selftest.py by default; or name
profile-selftest.py), plus variants of each (another chat role as its first message, another hook event, the other message form).
Needs MUSTER_CHECKS_BIN. Prints the differences; exit 1 on any. Standard library only.
Usage: MUSTER_CHECKS_BIN=<program> python3 scripts/rules-parity-diff.py [rules-check-selftest.py|profile-selftest.py]"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SUB = {"rules-check.py": "rules", "board-stop.py": "board-stop", "talk-check.py": "talk"}
TEST = sys.argv[1] if len(sys.argv) > 1 else "rules-check-selftest.py"
BIN = os.environ.get("MUSTER_CHECKS_BIN")
if not BIN:
    sys.exit("set MUSTER_CHECKS_BIN to the Rust program")
real_run = subprocess.run
FIRSTS = ["You are Manager_Muster_002", "You are Builder A_Muster_002, agents/builder.md", "You are Inspector_Muster_002", "You are Designer_Muster_002",
          "You are Sketchpad_Muster", "hello there"]
EVENTS = ["Stop", "PreToolUse", "UserPromptSubmit", "PostToolUse", "SessionStart"]
diffs = []
seen = set()
count = [0]


def norm(s):
    try:
        return json.dumps(json.loads(s), sort_keys=True)
    except ValueError:
        return s.strip()


def rust_cmd(cmd):
    """The Rust program for a Python hook command; in a project's .muster-checks folder a copy sits beside the profile, as in an install."""
    script = cmd[1]
    d = os.path.dirname(os.path.abspath(script))
    exe = BIN
    if os.path.basename(d) == ".muster-checks":
        exe = os.path.join(d, "muster-checks")
        if not os.path.isfile(exe):
            shutil.copyfile(BIN, exe)
            os.chmod(exe, 0o755)
    return [exe, SUB[os.path.basename(script)]]


def both(cmd, inp, env, label):
    count[0] += 1
    renv = env
    sd = env.get("MUSTER_STATE_DIR")
    if sd and os.path.isdir(sd):  # what the manager was told is kept in a state folder: each copy starts from the same one
        copy = tempfile.mkdtemp()
        shutil.rmtree(copy)
        shutil.copytree(sd, copy)
        renv = dict(env, MUSTER_STATE_DIR=copy)
    py = real_run(cmd, input=inp, capture_output=True, text=True, env=env)
    rs = real_run(rust_cmd(cmd), input=inp, capture_output=True, text=True, env=renv)
    if renv is not env:
        shutil.rmtree(renv["MUSTER_STATE_DIR"], ignore_errors=True)
    rec = "Muster rule: a message between chats is a data record"
    a, b = norm(py.stdout), norm(rs.stdout)
    if a != b and (b.startswith(rec) and (not a or a.startswith(rec[:40]))):
        return  # the Rust program checks every field of a JSON record and says which is wrong; the Python copy only that it is JSON
    if a != b and (cmd[1], inp, label) not in seen:
        seen.add((cmd[1], inp, label))
        diffs.append((label + " [" + os.path.basename(cmd[1]) + "]", inp[:600], py.stdout.strip()[:400], rs.stdout.strip()[:400]))


def variants(cmd, kw):
    inp = kw.get("input", "")
    env = kw.get("env") or os.environ
    try:
        ev = json.loads(inp)
    except ValueError:
        return
    both(cmd, inp, env, "as run")
    tp = ev.get("transcript_path")
    envs = {"as is": env, "text": dict(env, MUSTER_MESSAGE_FORM="text"), "json": {k: v for k, v in env.items() if k != "MUSTER_MESSAGE_FORM"}}
    for en, e in envs.items():
        if en != "as is":
            both(cmd, inp, e, "env " + en)
    for name in EVENTS:
        if name != ev.get("hook_event_name"):
            both(cmd, json.dumps(dict(ev, hook_event_name=name)), env, "event " + name)
    if tp and os.path.isfile(tp):
        lines = open(tp, encoding="utf-8").read().splitlines()
        for i, f in enumerate(FIRSTS):
            alt = tp + ".v%d" % i
            out = list(lines)
            for j, l in enumerate(out):
                try:
                    d = json.loads(l)
                except ValueError:
                    continue
                if d.get("type") == "user" and isinstance(d.get("message", {}).get("content"), str) and not d.get("isCompactSummary"):
                    d["message"]["content"] = f
                    out[j] = json.dumps(d)
                    break
            else:
                continue
            open(alt, "w", encoding="utf-8").write("\n".join(out) + "\n")
            both(cmd, json.dumps(dict(ev, transcript_path=alt)), env, "first message %d" % i)


def patched(cmd, *a, **kw):
    if isinstance(cmd, list) and len(cmd) == 2 and cmd[0] == sys.executable and os.path.basename(str(cmd[1])) in SUB:
        variants(cmd, kw)
    return real_run(cmd, *a, **kw)


subprocess.run = patched
src = open(os.path.join(HERE, TEST), encoding="utf-8").read()
os.environ.pop("MUSTER_CHECKS_BIN", None)  # the self-test drives the Python copy; this script compares it with the program
g = {"__name__": "selftest", "__file__": os.path.join(HERE, TEST)}
try:
    exec(compile(src, TEST, "exec"), g)
except SystemExit:
    pass
print("%d runs compared, %d differences" % (count[0], len(diffs)))
for label, inp, py, rs in diffs:
    print("--", label, "\n  in:", inp, "\n  python:", py, "\n  rust:  ", rs)
sys.exit(1 if diffs else 0)
