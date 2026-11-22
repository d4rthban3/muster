#!/usr/bin/env python3
"""start-weight (item 132): how much text Muster itself adds to a chat's start, and after a compaction. Prints the numbers
(characters; tokens are about a quarter of that) and fails if one grows past its budget, so the weight cannot creep back.

  start (a manager / a worker): the role's one page (agents/<role>.md without its front matter) + every skill's description
        + every agent's description (the lists a chat is handed at start)
  after a compaction: what the compact hook prints (renew-after-summary.py, with talk-block.txt)
The BEFORE figures are 0.3.181 (measured once, kept here). The budget is two thirds of them, rounded down.
  start-weight.py          print and check        start-weight.py --table   print only"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEFORE = {"manager": 12640, "builder": 9436, "compact": 755}
BUDGET = {k: v * 2 // 3 for k, v in BEFORE.items()}


def read(*p):
    return open(os.path.join(ROOT, *p), encoding="utf-8").read()


def description(text):
    m = re.search(r"^description:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def lists():
    skills = sum(len(description(read("skills", d, "SKILL.md"))) for d in sorted(os.listdir(os.path.join(ROOT, "skills")))
                 if os.path.isfile(os.path.join(ROOT, "skills", d, "SKILL.md")))
    agents = sum(len(description(read("agents", f))) for f in sorted(os.listdir(os.path.join(ROOT, "agents"))) if f.endswith(".md"))
    return skills, agents


def page(role):
    return len(re.sub(r"^---\n.*?\n---\n", "", read("agents", role + ".md"), flags=re.S).strip())


def compact():
    with tempfile.TemporaryDirectory() as d:
        tp = os.path.join(d, "t.jsonl")
        open(tp, "w", encoding="utf-8").write(json.dumps({"type": "user", "message": {"content": "You are Builder A_Proj_001, agents/builder.md"}}) + "\n")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "hooks", "renew-after-summary.py")], capture_output=True, text=True,
                           input=json.dumps({"hook_event_name": "SessionStart", "transcript_path": tp}), env=dict(os.environ, MUSTER_PROFILE=""))
        return len(r.stdout.strip())


def main():
    sk, ag = lists()
    now = {"manager": page("manager") + sk + ag, "builder": page("builder") + sk + ag, "compact": compact()}
    bad = 0
    for k in ("manager", "builder", "compact"):
        over = now[k] > BUDGET[k]
        bad += over
        print("%-8s before %5d  now %5d (%+d%%)  budget %5d  %s" % (k, BEFORE[k], now[k], round(100 * (now[k] - BEFORE[k]) / BEFORE[k]), BUDGET[k], "TOO HEAVY" if over else "ok"))
    print("(skills' descriptions %d, agents' descriptions %d, manager page %d, builder page %d characters)" % (sk, ag, page("manager"), page("builder")))
    return 0 if "--table" in sys.argv else (1 if bad else 0)


if __name__ == "__main__":
    sys.exit(main())
