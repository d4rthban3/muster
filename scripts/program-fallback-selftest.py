#!/usr/bin/env python3
"""Self-test for the safety net (rust-first piece 4): every hook that runs the ready-built program first must run its Python copy when the
program is missing, will not start, crashes, is killed, or ends with any exit code but 0, and must never print half an answer from the program
beside the Python one. A program that answers with exit 0 is trusted, and its answer (even an empty one) is the hook's.
Uses stand-in programs and stand-in Python copies in a temporary folder; no real program is needed. Prints 'N of M passed'; exit 1 on a miss."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
T = tempfile.mkdtemp()
WIN = os.name == "nt"
HOOKS = [  # hook script, program check, Python copy the hook runs (relative to the plugin folder)
    ("rules-check.sh", "rules", "hooks/rules-check.py"), ("guard-check.sh", "guard", "hooks/rules-check.py"), ("talk-check.sh", "talk", "hooks/talk-check.py"),
    ("board-stop.sh", "board-stop", "hooks/board-stop.py"), ("renew-after-summary.sh", "renew", "hooks/renew-after-summary.py"),
    ("precompact-board.sh", "precompact", "hooks/precompact-board.py"), ("worker-queue-check.sh", "worker-queue", "scripts/worker-queue-check.py"),
]
PROJECT = os.path.join(T, "proj")
os.makedirs(os.path.join(PROJECT, "muster"))
for f in ("CLAUDE.md", "BOARD.md"):
    open(os.path.join(PROJECT, "muster", f), "w").write("x\n")
os.makedirs(os.path.join(PROJECT, ".muster-checks"))  # a profile: the guard hook runs only where the project has one
open(os.path.join(PROJECT, ".muster-checks", "profile.json"), "w").write("{}")
results = []


def plugin(program):
    """A plugin copy whose Python copies print PYTHON RAN, with the given stand-in program (None: no program) in every system's bin folder."""
    pl = os.path.join(tempfile.mkdtemp(dir=T), "plugin")
    for d in ("hooks", "scripts"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(pl, d), ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(os.path.join(pl, ".claude-plugin"))
    open(os.path.join(pl, ".claude-plugin", "plugin.json"), "w").write("{}")
    for _, _, py in HOOKS:
        open(os.path.join(pl, py), "w").write("import sys\nsys.stdin.read()\nsys.stdout.write('PYTHON RAN\\n')\n")
    if program is not None:
        for d, exe in (("windows-x86_64", "muster-checks.exe"), ("macos-arm64", "muster-checks"), ("macos-x86_64", "muster-checks"), ("linux-x86_64", "muster-checks"), ("linux-arm64", "muster-checks")):
            os.makedirs(os.path.join(pl, "bin", d))
            dst = os.path.join(pl, "bin", d, exe)
            open(dst, "w").write((program if program.startswith("#!") else "#!/bin/sh\n" + program) + "\n")
            os.chmod(dst, 0o755 if "no-exec" not in program else 0o644)
    return pl


def run(pl, script):
    env = {k: v for k, v in os.environ.items() if k not in ("MUSTER_PROFILE", "CLAUDE_PROJECT_DIR")}
    r = subprocess.run(["sh", os.path.join(pl, "hooks", script)], input="{}", capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=PROJECT, env=env)
    return r.returncode, r.stdout


CASES = [  # name, stand-in program, the Python copy must run (else the program's own answer stands)
    ("no program at all", None, True),
    ("a program that ends with exit 1", "exit 1", True),
    ("an older program that ends with exit 2", "exit 2", True),
    ("a crash (exit 101) after half an answer", "echo PARTIAL; exit 101", True),
    ("a program that will not start (a missing interpreter)", "#!/nonexistent/interpreter\nexit 0", True),
    ("a program with exit 0 and an answer", "echo PROGRAM ANSWER; exit 0", False),
    ("a program with exit 0 and no answer", "exit 0", False),
]
if not WIN:
    CASES.insert(5, ("a program that is killed", "echo PARTIAL; kill -9 $$", True))
for hook, _, _ in HOOKS:
    for name, prog, want_py in CASES:
        rc, out = run(plugin(prog), hook)
        if want_py:
            ok = rc == 0 and out.strip() == "PYTHON RAN"
        else:
            ok = rc == 0 and "PYTHON RAN" not in out and out.strip() == ("PROGRAM ANSWER" if "ANSWER" in prog else "")
        results.append(ok)
        print(("ok   " if ok else "FAIL ") + "%s: %s" % (hook, name) + ("" if ok else "  -> rc=%s out=%r" % (rc, out)))
print("%d of %d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
