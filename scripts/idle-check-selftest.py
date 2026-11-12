#!/usr/bin/env python3
"""Self-test for scripts/idle-check.py on a made-up project. Prints PASS/FAIL lines; exit 1 on any failure."""
import json, os, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
CHK = os.path.join(HERE, "idle-check.py")
now = int(time.time() * 1000)
tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, "muster")); os.makedirs(os.path.join(tmp, "s", "a", "b"))
cid = lambda n: "local_" + ("%d" % n) * 8 + "-1111-1111-1111-" + ("%d" % n) * 12
def w(p, t): open(os.path.join(tmp, p), "w").write(t)
w("muster/BOARD.md", "### 2026-01-01 | ORDER | Manager_X_001 -> Builder Q_X_001 | job1\nStatus: open\n")
w("muster/CREW.md", "## Running now\n| Name | Model | Effort | Folder | Chat id | Started |\n|---|---|---|---|---|---|\n" +
  "".join("| %s | m | medium | f | %s | d |\n" % (n, cid(i)) for i, n in enumerate(["Manager_X_001", "Builder Q_X_001", "Builder R_X_001", "Builder S_X_001"], 1)) + "\n## Archived\n")
w("muster/OWNERS-LIST.md", "## Open\n1. \"a\"\n   Stands: with Builder R_X_001\n2. \"b\"\n   Stands: done\n3. \"c\"\n   Stands: waiting on you\n\n## Closed\n")
def rec(i, ago, arch=False):
    json.dump({"isArchived": arch, "lastActivityAt": now - ago * 1000}, open(os.path.join(tmp, "s", "a", "b", cid(i) + ".json"), "w"))
rec(1, 5); rec(2, 600); rec(3, 600); rec(4, 600, True)
env = dict(os.environ, MUSTER_SESSIONS_DIR=os.path.join(tmp, "s"))
def run(inp):
    return subprocess.run([sys.executable, CHK, "--project", tmp], input=json.dumps(inp), capture_output=True, text=True, env=env).stdout
bad = 0
def t(name, ok):
    global bad; bad += (not ok); print(("PASS " if ok else "FAIL ") + name)
o = run({"last_assistant_message": "done"})
t("blocks on idle chat with an open board order", "Builder Q_X_001" in o and "block" in o)
t("blocks on idle chat with an open list item", "Builder R_X_001" in o)
t("running chat is not named", "Manager_X_001" not in o.split("Do not end")[1])
t("archived chat is not named", "Builder S_X_001" not in o)
t("allows when both are named", run({"last_assistant_message": "Builder Q_X_001 and Builder R_X_001 are on it"}) == "")
t("never loops", run({"stop_hook_active": True}) == "")
t("silent outside a manager folder", subprocess.run([sys.executable, CHK, "--project", tempfile.mkdtemp()], input="{}", capture_output=True, text=True, env=env).stdout == "")
sys.exit(1 if bad else 0)
