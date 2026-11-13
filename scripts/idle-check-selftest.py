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
  "".join("| %s | m | medium | f | %s | d |\n" % (n, cid(i)) for i, n in enumerate(["Manager_X_001", "Builder Q_X_001", "Builder R_X_001", "Builder S_X_001", "Builder T_X_001"], 1)) + "\n## Archived\n")
w("muster/OWNERS-LIST.md", "## Open\n1. \"a\"\n   Stands: with Builder R_X_001\n2. \"b\"\n   Stands: done\n3. \"c\"\n   Stands: waiting on you\n\n## Closed\n")
def rec(i, ago, arch=False, summ=None):
    json.dump({"isArchived": arch, "lastActivityAt": now - ago * 1000, "postTurnSummary": summ or {}}, open(os.path.join(tmp, "s", "a", "b", cid(i) + ".json"), "w"))
rec(1, 5); rec(2, 600); rec(3, 600); rec(4, 600, True); rec(5, 5, summ={"status_category": "blocked", "status_detail": "WAIT: Manager's choice", "needs_action": "the manager's choice"})
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
t("allows when both are named", run({"last_assistant_message": "Builder Q_X_001, Builder R_X_001 and Builder T_X_001 are on it"}) == "")
t("a running chat that says it waits on the manager is named", "Builder T_X_001 says it waits on the manager" in o)
o2 = run({"last_assistant_message": "Builder Q_X_001 and Builder R_X_001 are on it"})
t("a waiting chat alone blocks until named", "Builder T_X_001 says" in o2 and "Builder Q_X_001 has been" not in o2)
t("never loops", run({"stop_hook_active": True}) == "")
t("silent outside a manager folder", subprocess.run([sys.executable, CHK, "--project", tempfile.mkdtemp()], input="{}", capture_output=True, text=True, env=env).stdout == "")

# a manager's hold must rest on his word (item 74)
def hproj(board, style=None):
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, "muster"))
    open(os.path.join(d, "muster", "BOARD.md"), "w").write(board)
    open(os.path.join(d, "muster", "CREW.md"), "w").write("## Running now\n\n## Archived\n")
    return d
def hrun(d, msg, extra_env=None):
    return subprocess.run([sys.executable, CHK, "--project", d], input=json.dumps({"last_assistant_message": msg}),
                          capture_output=True, text=True, env=dict(env, **(extra_env or {}))).stdout
d1 = hproj("### 2026-11-12 | ORDER | Manager_X_001 -> Builder U_X_001 | quiet\nStatus: open\nAction: hold\nNeed: wait for the measurement.\n")
t("a manager's hold with no owner basis is refused", "holds Builder U_X_001" in hrun(d1, "ok"))
t("allowed once the reply names the held worker", hrun(d1, "Releasing Builder U_X_001") == "")
d2 = hproj("### 2026-11-12 | ORDER | Manager_X_001 -> Builder U_X_001 | quiet\nStatus: open\nAction: hold\nNeed: hold after PASS for his go (item 12).\n")
t("a hold that cites his item is allowed", hrun(d2, "ok") == "")
d3 = hproj("### 2026-11-12 | ORDER | Manager_X_001 -> Builder U_X_001 | quiet\nStatus: done\nAction: hold\nNeed: wait.\n")
t("a closed hold is ignored", hrun(d3, "ok") == "")
d4 = tempfile.mkdtemp(); open(os.path.join(d4, "BOARD.md"), "w").write(
    "2026-11-12 | RULE | Manager_P_005 -> Eng_P_006 | quiet window for timing. Action: hold\n"
    "2026-11-12 | RULE | Manager_P_005 -> Web_P_004 | wait for his word on the route (item 12). Action: hold\n"
    "2026-11-12 | NEED | Eng_P_006 -> Manager_P_005 | wait. Action: hold\n")
open(os.path.join(d4, "profile.json"), "w").write(json.dumps({"board": "BOARD.md", "board_style": "lines", "crew_names": []}))
os.makedirs(os.path.join(d4, "muster")); open(os.path.join(d4, "muster", "BOARD.md"), "w").write("")
pe = {"MUSTER_PROFILE": os.path.join(d4, "profile.json")}
o4 = hrun(d4, "ok", pe)
t("PINR: a manager's hold line with no owner basis is refused", "holds Eng_P_006" in o4)
t("PINR: a hold that cites his item and a worker's own line are not", "Web_P_004" not in o4.split("Do not end")[-1] and "Manager_P_005 (" not in o4)
sys.exit(1 if bad else 0)
