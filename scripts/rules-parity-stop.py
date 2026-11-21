#!/usr/bin/env python3
"""Parity fuzz for the end-of-turn replies (rust-first piece 1): many reply texts (cards, questions, lettered choices, status lines, news,
paths, codes, plain talk) x several kinds of chat x several shapes of conversation, each sent as a Stop event to the Python rules-check,
board-stop and talk-check and to the Rust program. Prints every case where one blocks and the other does not, or both block with a different
reason. Needs MUSTER_CHECKS_BIN. Writes only in a temporary folder. Standard library only. Exit 1 on any difference."""
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
BIN = os.environ.get("MUSTER_CHECKS_BIN")
if not BIN:
    sys.exit("set MUSTER_CHECKS_BIN to the Rust program")
T = tempfile.mkdtemp()
ENV = dict((k, v) for k, v in os.environ.items() if k not in ("MUSTER_PROFILE", "MUSTER_MESSAGE_FORM"))
ENV["MUSTER_STATE_DIR"] = T
if os.environ.get("MUSTER_PARITY_PROFILE"):  # run the same cases under a project profile (for example pinr): the program and Python must still answer alike
    ENV["MUSTER_PROFILE"] = os.path.join(ROOT, "profiles", os.environ["MUSTER_PARITY_PROFILE"] + ".json")
FIRSTS = {"manager": "You are Manager_Muster_002", "builder": "You are Builder A_Muster_002, agents/builder.md", "inspector": "You are Inspector_Muster_002",
          "designer": "You are Designer_Muster_002", "owner": "hello there"}
PROJ = os.path.join(T, "proj")
os.makedirs(os.path.join(PROJ, "muster"))
open(os.path.join(PROJ, "muster", "BOARD.md"), "w").write("### 2026-01-01 | NEED | Builder A_X -> Manager_X | job\nStatus: open\n\n### 2026-01-02 | PASS | Inspector_X -> Manager_X | job2\nStatus: open\n")
IDLE = os.path.join(T, "idle")
os.makedirs(os.path.join(IDLE, "muster"))
open(os.path.join(IDLE, "muster", "BOARD.md"), "w").write("### 2026-01-01 | PASS | Inspector_X -> Manager_X | job\nStatus: done\n")
Q = "**ASK · q**\n\nWhich first?\n\n***A.*** ship the menu fix *(my pick)* because it is small\n\n***B.*** wait for the next piece"
TEXTS = [
    "ok", "Done.", "Working: Engine on rug-archive-seed, Site on launch-signs-show", "**DONE · job**\n- what\n- result 3/3\n- nothing left", "**DONE · job**\n- a\n- b\n- c\n- d",
    "**DONE · job**\n- see [the file](docs/a.md)\n- 3 passed", "**DONE · job**\n- see docs/a.md\n- 3 passed", "I changed hooks/rules-check.py and it works.", "Saved as abc1234 on the branch.",
    "The commit 39ed244 is in.", Q, Q.replace("***A.***", "A."), Q.replace("(my pick)", ""), Q.replace("**ASK · q**\n\n", ""), "Which one?\n\n***A.*** one\n\n***B.*** two", "***A.*** one\n***B.*** two",
    "The crew is idle. Here's what's next toward your goal,\n\n***A.*** one\n\n***B.*** two", "**IDLE · crew**\n\nThe crew is idle. Here's what's next toward your goal,\n\n***A.*** one\n\n***B.*** two",
    "The crew is idle.", "The board has news on the board.", "News is on the board.", "I need your yes to ship.", "Do you want me to ship it?", "I'm recording A as your pick.", "You picked A, recording it.",
    "I went with B because it is smaller.", "Fine. Builder A_X and job are handled.", "Builder A_X has a need about job.", "Noted, thanks!", "A long reply. " * 40, "line one\nline two\nline three\nline four",
    "```\nsome/path/file.py\n```", "see https://example.com/a/b.md", "key sk" + "-abcdefghijklmnopqrstuvwxyz123456 leaked", "**WORD · job**\n- a\n- b", "Working: x", "Working: Engine on a\nWorking: Site on b",
    "pictures: [screenshot](a.png)", "I made a picture and saved it.", "**PASS · job**\n- ok\n- 3/3\n- none", "Which first?\n\n***A.*** a\n\n***B.*** b\n\n***C.*** c\n\n***D.*** d\n\n***E.*** e",
    "¿Cuál?\n\n***A.*** uno\n\n***B.*** dos *(my pick)*", "**ASK · q**\n\nOne question?\n\n***A.*** yes *(my pick)*", "(A) one\n(B) two", "Should I go on? ***A.*** yes ***B.*** no",
]
QL = "Coverage order: A (bot signs next, as ordered) or B (X scan and callouts first)?"
QC = "**ASK \u00b7 coverage**\n\nWhich first?\n\n***A.*** Bot signs next, as ordered *(my pick)* because it is small\n\n***B.*** X scan and callouts first"
TEXTS += [QL, QC, "Coverage order: A (menu fix first) or B (footer first)?", "Ship it?", "Which one, A (red) or B (blue)?"]
TEXTS = list(dict.fromkeys(TEXTS))


def asst(t):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}


def usr(t):
    return {"type": "user", "message": {"content": t}}


PEER = '<cross-session-message from="local_x">{"kind":"READY"}</cross-session-message>'
SHAPES = {
    "bare": lambda: [],
    "typed": lambda: [usr("do the thing please")],
    "typed-question": lambda: [usr("what is up?")],
    "typed-letter": lambda: [asst(Q), usr("A")],
    "typed-letter-card": lambda: [asst(Q), usr("A"), asst("Good, going ahead.")],
    "peer": lambda: [usr(PEER)],
    "asked-oneline": lambda: [asst(QL), usr(PEER)],
    "asked-oneline-bounced": lambda: [asst(QL), usr("Stop hook feedback: fix it")],
    "asked-card-then-typed": lambda: [asst(Q), usr("go on"), usr(PEER)],
    "asked-oneline-card": lambda: [asst(QC), usr(PEER)],
    "hook-feedback": lambda: [usr("Stop hook feedback: fix the card")],
    "ask-card": lambda: [usr("go"), {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "a", "name": "AskUserQuestion", "input": {}}]}}],
}
jobs = []
n = 0
for role, first in FIRSTS.items():
    for shape, mk in SHAPES.items():
        p = os.path.join(T, "t%d.jsonl" % n)
        n += 1
        with open(p, "w") as f:
            f.write(json.dumps(usr(first)) + "\n")
            for e in mk():
                f.write(json.dumps(e) + "\n")
        for text in TEXTS:
            for cwd in (PROJ, IDLE):
                jobs.append((role, shape, text, p, cwd))
SUBS = [("hooks/rules-check.py", "rules"), ("hooks/board-stop.py", "board-stop"), ("hooks/talk-check.py", "talk")]


def norm(out):
    out = out.strip()
    if not out:
        return ""
    try:
        d = json.loads(out)
        r = d.get("reason") or d.get("systemMessage") or json.dumps(d)
    except ValueError:
        return out
    return str(r).replace(os.path.normpath(os.path.abspath(ROOT)) + "/scripts/", "")


def one(job):
    role, shape, text, p, cwd = job
    ev = json.dumps({"hook_event_name": "Stop", "cwd": cwd, "transcript_path": p, "last_assistant_message": text})
    out = []
    for hook, sub in SUBS:
        st = tempfile.mkdtemp(dir=T)
        env = dict(ENV, MUSTER_STATE_DIR=st)
        py = subprocess.run([sys.executable, os.path.join(ROOT, hook)], input=ev, capture_output=True, text=True, env=env)
        st2 = tempfile.mkdtemp(dir=T)
        rs = subprocess.run([BIN, sub], input=ev, capture_output=True, text=True, env=dict(ENV, MUSTER_STATE_DIR=st2))
        a, b = norm(py.stdout), norm(rs.stdout)
        if a != b:
            out.append((sub, a[:260], b[:260]))
    return job, out


with ThreadPoolExecutor(8) as ex:
    results = list(ex.map(one, jobs))
diffs = [(j, o) for j, o in results if o]
print("%d replies compared, %d differ" % (len(results), len(diffs)))
shown = set()
for (role, shape, text, p, cwd), outs in diffs:
    for sub, a, b in outs:
        key = (sub, a[:100], b[:100])
        if key in shown:
            continue
        shown.add(key)
        print("DIFF", sub, "as", role, shape, "in", os.path.basename(cwd), "text:", json.dumps(text[:90]), "\n   python:", a, "\n   rust:  ", b)
sys.exit(1 if diffs else 0)
