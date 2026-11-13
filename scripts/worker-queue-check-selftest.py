#!/usr/bin/env python3
"""Self-test for scripts/worker-queue-check.py on a made-up project with a worker copy. Prints PASS/FAIL; exit 1 on a failure."""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
CHK = os.path.join(HERE, "worker-queue-check.py")
main = tempfile.mkdtemp()
def sh(*a, cwd=main): subprocess.run(a, cwd=cwd, check=True, capture_output=True)
sh("git", "init", "-q"); sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x")
wt = os.path.join(main, ".claude", "worktrees", "builder-q-001")
sh("git", "worktree", "add", "-q", wt, "-b", "q")
os.makedirs(os.path.join(main, "muster"))
def w(p, t): open(os.path.join(main, p), "w").write(t)
w("muster/BOARD.md", "### 2026-01-01 | ORDER | Manager_X_001 -> Builder Q_X_001 | job-one\nStatus: open\n\n### 2026-01-01 | ORDER | Manager_X_001 -> Builder R_X_001 | job-two\nStatus: open\n\n### 2026-01-01 | ORDER | Manager_X_001 -> Builder Q_X_001 | job-old\nStatus: done\n\n### 2026-01-01 | ORDER | Manager_X_001 -> Builder Q_X_001 | job-fin\nStatus: open\n\n### 2026-01-02 | PASS | Inspector_X_001 -> Builder Q_X_001 | job fin\nStatus: open\nPASS: job-fin [ID i-1]\n")
w("muster/CREW.md", "## Running now\n| Name | Model | Effort | Folder copy | Chat id | Started |\n|---|---|---|---|---|---|\n| Manager_X_001 | m | medium | none (main) | local_1 | d |\n| Builder Q_X_001 | m | medium | .claude/worktrees/builder-q-001 (line q) | local_2 | d |\n\n## Archived\n")
w("muster/OWNERS-LIST.md", "## Open\n1. \"a\"\n   Stands: with Builder Q_X_001\n2. \"b\"\n   Stands: standing; open fixes with Builder Q_X_001\n\n## Closed\n")
def run(inp, cwd=wt):
    return subprocess.run([sys.executable, CHK], input=json.dumps(inp), capture_output=True, text=True, cwd=cwd).stdout
bad = 0
def t(name, ok):
    global bad; bad += (not ok); print(("PASS " if ok else "FAIL ") + name)
o = run({"last_assistant_message": "done"})
t("blocks a worker with an open order", "block" in o and "job-one" in o)
t("blocks for an open list item", "item 1" in o)
t("ignores a closed order, one a later PASS names, another worker's order and a standing item", "job-old" not in o and "job-fin" not in o and "job-two" not in o and "item 2" not in o)
t("allows when the reply names the job and the item", run({"last_assistant_message": "waiting on job-one and item 1: inspector"}) == "")
t("never loops", run({"stop_hook_active": True}) == "")
t("silent in the manager's own folder", run({}, cwd=main) == "")
t("silent outside any project", run({}, cwd=tempfile.mkdtemp()) == "")

# line-style board (PINR): no ORDER tag, workers found by the name in the chat's first message
pp = tempfile.mkdtemp()
open(os.path.join(pp, "BOARD.md"), "w").write(
    "2026-11-12 | RULE | Manager_P_005 -> Eng_P_006 | old thing. Action: start\n"
    "2026-11-12 | DONE | Eng_P_006 -> Manager_P_005 | old thing live. Action: start\n"
    "2026-11-12 | NEED | Look_P_002 -> Eng_P_006 | serve burns route. Action: start\n"
    "2026-11-12 | RULE | Manager_P_005 -> Eng_P_006 | wait for the build. Action: hold\n"
    "2026-11-12 | PASS | Eng Inspector_P_003 -> Manager_P_005 | checked. Action: start\n"
    "2026-11-12 | NEED | Manager_P_005 -> Web_P_004 | other worker task. Action: start\n")
open(os.path.join(pp, "profile.json"), "w").write(json.dumps({"board": "BOARD.md", "board_style": "lines"}))
def transcript(first):
    f = os.path.join(pp, "t%d.jsonl" % len(os.listdir(pp)))
    open(f, "w").write(json.dumps({"type": "user", "message": {"content": first}}) + "\n")
    return f
def prun(first, msg, **extra):
    d = {"transcript_path": transcript(first), "last_assistant_message": msg}; d.update(extra)
    return subprocess.run([sys.executable, CHK], input=json.dumps(d), capture_output=True, text=True, cwd=pp,
                          env=dict(os.environ, MUSTER_PROFILE=os.path.join(pp, "profile.json"))).stdout
o = prun("You are Eng_P_006, the engine chat.", "done")
t("PINR: blocks on a NEED line after the worker's last DONE", "block" in o and "serve burns" in o)
t("PINR: ignores work before its last DONE, a hold line and another worker's line", "old thing" not in o and "wait for the build" not in o and "other worker" not in o)
t("PINR: allows when the reply names the sender", prun("You are Eng_P_006", "waiting on Look_P_002") == "")
t("PINR: never loops", prun("You are Eng_P_006", "x", stop_hook_active=True) == "")
t("PINR: finds the worker when the first message also names its manager and inspector",
  "block" in prun("You are Eng_P_006. Your manager is Manager_P_005 and your inspector is Eng Inspector_P_003.", "done"))
t("PINR: the earliest name wins without \"You are\"", "block" in prun("Eng_P_006 here; inspector Eng Inspector_P_003", "done"))
t("PINR: silent for a chat that names no crew worker", prun("hello there", "x") == "")
t("PINR: silent for the manager", prun("You are Manager_P_005", "x") == "")
sys.exit(1 if bad else 0)
