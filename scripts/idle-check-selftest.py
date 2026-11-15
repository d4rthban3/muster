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
env = dict(os.environ, MUSTER_SESSIONS_DIR=os.path.join(tmp, "s"), MUSTER_NO_SWEEP="1")
def run(inp, state=None):
    e = dict(env, MUSTER_STATE_DIR=state or tempfile.mkdtemp())  # a fresh memory of what was said, unless a test shares one
    return subprocess.run([sys.executable, CHK, "--project", tmp], input=json.dumps(inp), capture_output=True, text=True, env=e).stdout
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
                          capture_output=True, text=True, env=dict(env, MUSTER_STATE_DIR=tempfile.mkdtemp(), **(extra_env or {}))).stdout
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

# item 81: once said, unchanged, a worker's message must not make the manager say it again
st = tempfile.mkdtemp()
first = run({"last_assistant_message": "ok", "transcript_path": "/t/one"}, st)
t("repeat: the first stop with idle chats and open items blocks", "block" in first)
t("repeat: the same findings on the next stop pass silently", run({"last_assistant_message": "ok", "transcript_path": "/t/one"}, st) == "")
t("repeat: another manager chat has its own memory", "block" in run({"last_assistant_message": "ok", "transcript_path": "/t/two"}, st))
os.makedirs(os.path.join(tmp, "muster"), exist_ok=True)
open(os.path.join(tmp, "muster", "OWNERS-LIST.md"), "a").write("\n")
with open(os.path.join(tmp, "muster", "OWNERS-LIST.md"), "w") as f:
    f.write("## Open\n1. \"a\"\n   Stands: with Builder R_X_001 (changed)\n\n## Closed\n")
t("repeat: a changed item is said again", "Builder R_X_001" in run({"last_assistant_message": "ok", "transcript_path": "/t/one"}, st))

# item 95: two or more idle workers with nothing to order: the owner gets one card with each worker's since, why and unblock, and one lettered question
def cproj(idle_ago, items=""):
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, "muster")); sd = os.path.join(d, "s", "a", "b"); os.makedirs(sd)
    names = ["Manager_Y_001"] + ["Builder %s_Y_001" % c for c in "ABC"]
    open(os.path.join(d, "muster", "BOARD.md"), "w").write("")
    open(os.path.join(d, "muster", "OWNERS-LIST.md"), "w").write("## Open\n" + items + "\n## Closed\n")
    open(os.path.join(d, "muster", "CREW.md"), "w").write("## Running now\n| Name | Model | Effort | Folder | Chat id | Started |\n|---|---|---|---|---|---|\n" +
        "".join("| %s | m | medium | f | %s | d |\n" % (n, cid(i)) for i, n in enumerate(names, 1)) + "\n## Archived\n")
    for i, ago in enumerate([5] + idle_ago, 1):
        json.dump({"isArchived": False, "lastActivityAt": now - ago * 1000, "postTurnSummary": {}}, open(os.path.join(sd, cid(i) + ".json"), "w"))
    return d, os.path.join(d, "s")
def crun(d, sd, msg):
    return subprocess.run([sys.executable, CHK, "--project", d], input=json.dumps({"last_assistant_message": msg}), capture_output=True, text=True,
                          env=dict(os.environ, MUSTER_SESSIONS_DIR=sd, MUSTER_STATE_DIR=tempfile.mkdtemp(), MUSTER_NO_SWEEP="1")).stdout
CARD = ("**IDLE \u00b7 crew**\n- Builder A_Y_001: idle since 14:02, why: its piece passed and nothing is open, unblocked by: a new order from his list\n"
        "- Builder B_Y_001: idle since 14:10, why: waits for the owner's ship allowance, unblocked by: his typed yes\n\n"
        "Which should come first?\n\n***A.*** the usage meter\n\n***B.*** the site clean-up")
d, sd = cproj([600, 600, 5])
o = crun(d, sd, "The crew is idle.")
t("idle card: two idle workers and a one-line news reply block", "block" in o and "Builder A_Y_001" in o and "Builder B_Y_001" in o and "item 95" in o)
t("idle card: a card naming each with since, why, unblocked by and a lettered question passes", crun(d, sd, CARD) == "")
t("idle card: a card with no lettered question blocks", "lettered question" in crun(d, sd, CARD.split("Which should")[0]))
t("idle card: a line without 'why' blocks and names the worker", "Builder B_Y_001" in crun(d, sd, CARD.replace("why: waits", "waits")).split("Missing:")[-1])
d1, sd1 = cproj([600, 5, 5])
t("idle card: one idle worker is not the card's business", crun(d1, sd1, "ok") == "")
d2, sd2 = cproj([600, 600, 5], "1. \"x\"\n   Stands: with Builder A_Y_001\n")
o2 = crun(d2, sd2, "ok")
t("idle card: an idle worker with open work and no order blocks, named, before the card", "Builder A_Y_001 has been idle" in o2)
st2 = tempfile.mkdtemp()
a1 = subprocess.run([sys.executable, CHK, "--project", d], input=json.dumps({"last_assistant_message": "ok", "transcript_path": "/t/c"}), capture_output=True, text=True, env=dict(os.environ, MUSTER_SESSIONS_DIR=sd, MUSTER_STATE_DIR=st2, MUSTER_NO_SWEEP="1")).stdout
a2 = subprocess.run([sys.executable, CHK, "--project", d], input=json.dumps({"last_assistant_message": "ok", "transcript_path": "/t/c"}), capture_output=True, text=True, env=dict(os.environ, MUSTER_SESSIONS_DIR=sd, MUSTER_STATE_DIR=st2, MUSTER_NO_SWEEP="1")).stdout
t("idle card: said once, unchanged, it is not asked again", "block" in a1 and a2 == "")

# item 96: a replaced chat not yet archived, and crew members with no order and no report for a day
import datetime
TODAY = datetime.date.today().isoformat()
def sproj(titles, board, names=("Manager_Z_001", "Builder A_Z_001", "Builder B_Z_001")):
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, "muster")); sd = os.path.join(d, "s", "a", "b"); os.makedirs(sd)
    open(os.path.join(d, "muster", "BOARD.md"), "w").write(board)
    open(os.path.join(d, "muster", "OWNERS-LIST.md"), "w").write("## Open\n\n## Closed\n")
    open(os.path.join(d, "muster", "CREW.md"), "w").write("## Running now\n| Name | Model | Effort | Folder | Chat id | Started |\n|---|---|---|---|---|---|\n" +
        "".join("| %s | m | medium | f | %s | d |\n" % (n, cid(i)) for i, n in enumerate(names, 1)) + "\n## Archived\n")
    for i, (title, arch) in enumerate(titles, 1):
        json.dump({"title": title, "sessionId": cid(i), "isArchived": arch, "lastActivityAt": now - 5000, "postTurnSummary": {}}, open(os.path.join(sd, cid(i) + ".json"), "w"))
    return d, os.path.join(d, "s")
def srun(d, sd, st=None, msg="ok"):
    return subprocess.run([sys.executable, CHK, "--project", d], input=json.dumps({"last_assistant_message": msg, "transcript_path": "/t/s"}), capture_output=True, text=True,
                          env=dict(os.environ, MUSTER_SESSIONS_DIR=sd, MUSTER_STATE_DIR=st or tempfile.mkdtemp())).stdout
BOARD_OK = "### %s | ORDER | Manager_Z_001 -> Builder A_Z_001 | j\nStatus: open\n### %s | READY | Builder B_Z_001 -> Inspector_Z_001 | k\nStatus: open\n" % (TODAY, TODAY)
d, sd = sproj([("Manager_Z_001", False), ("Builder A_Z_001", False), ("Builder A_Z_002", False), ("Builder B_Z_001", False)], BOARD_OK)
o = srun(d, sd)
t("sweep: a replaced chat that is not archived is named with its replacement", "Builder A_Z_001 was replaced by Builder A_Z_002" in o and "item 96" in o)
d, sd = sproj([("Manager_Z_001", False), ("Builder A_Z_001", True), ("Builder A_Z_002", False), ("Builder B_Z_001", False)], BOARD_OK)
t("sweep: an archived replaced chat is not named", srun(d, sd) == "")
d, sd = sproj([("Manager_Z_001", False), ("Builder A_Z_001", False), ("Builder B_Z_001", False)], BOARD_OK.replace("Builder B_Z_001", "Builder C_Z_001"))
o = srun(d, sd)
t("sweep: a member with no order and no report in a day is named", "Builder B_Z_001 has had no order and no report" in o and "Builder A_Z_001 has had" not in o)
d, sd = sproj([("Manager_Z_001", False), ("Builder A_Z_001", False), ("Builder B_Z_001", False)], BOARD_OK.replace(TODAY, "2020-01-01"))
t("sweep: an old board names both workers, never the manager", "Builder A_Z_001 has had" in srun(d, sd) and "Manager_Z_001 has had" not in srun(d, sd))
d, sd = sproj([("Manager_Z_001", False), ("Builder A_Z_001", False), ("Builder B_Z_001", False)], BOARD_OK)
t("sweep: everyone active and nothing replaced is silent", srun(d, sd) == "")
st3 = tempfile.mkdtemp(); d, sd = sproj([("Manager_Z_001", False), ("Builder A_Z_001", False), ("Builder A_Z_002", False), ("Builder B_Z_001", False)], BOARD_OK)
t("sweep: said once, unchanged, it is not said again the same day", "block" in srun(d, sd, st3) and srun(d, sd, st3) == "")
d, sd = sproj([("Manager_Z_001", False), ("Builder A_Z_001", False), ("Builder A_Z_002", False), ("Builder B_Z_001", False)], BOARD_OK)
t("sweep: naming the chat in the reply satisfies it", srun(d, sd, msg="Archiving Builder A_Z_001 now") == "")
d, sd = sproj([("Manager_Z_001", False), ("Builder A_Z_001", False), ("Builder A_Z_002", False), ("Other_Q_001", False), ("Other_Q_002", False)], BOARD_OK)
t("sweep: another project's replaced chat is not this crew's", "Other_Q_001" not in srun(d, sd))
sys.exit(1 if bad else 0)
