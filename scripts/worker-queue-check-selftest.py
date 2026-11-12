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
w("muster/BOARD.md", "### 2026-01-01 | ORDER | Manager_X_001 -> Builder Q_X_001 | job-one\nStatus: open\n\n### 2026-01-01 | ORDER | Manager_X_001 -> Builder R_X_001 | job-two\nStatus: open\n\n### 2026-01-01 | ORDER | Manager_X_001 -> Builder Q_X_001 | job-old\nStatus: done\n")
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
t("ignores a closed order, another worker's order and a standing item", "job-old" not in o and "job-two" not in o and "item 2" not in o)
t("allows when the reply names the job and the item", run({"last_assistant_message": "waiting on job-one and item 1: inspector"}) == "")
t("never loops", run({"stop_hook_active": True}) == "")
t("silent in the manager's own folder", run({}, cwd=main) == "")
t("silent outside any project", run({}, cwd=tempfile.mkdtemp()) == "")
sys.exit(1 if bad else 0)
