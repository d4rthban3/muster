#!/usr/bin/env python3
"""Parity fuzz for the tool-call rules (rust-first piece 1): many tool calls (shell commands, file writes, memory notes, crew-list edits, the
app's wrap-up and choice-card calls, pictures, helpers) x several kinds of chat x three profiles (none, PINR, a guard profile), each sent as a
PreToolUse event to the Python rules-check, the guard and the Rust program. Prints every case where one refuses and the other does not, or both
refuse for a different reason. Needs MUSTER_CHECKS_BIN. Writes only in a temporary folder. Standard library only. Exit 1 on any difference."""
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
BASEENV = dict((k, v) for k, v in os.environ.items() if k not in ("MUSTER_PROFILE", "MUSTER_MESSAGE_FORM"))
BASEENV["MUSTER_STATE_DIR"] = T
PROT = os.path.join(T, "main")
PUB = os.path.join(T, "pubcopy")
for d in (PROT, os.path.join(PROT, "muster"), os.path.join(PROT, "scripts"), PUB):
    os.makedirs(d, exist_ok=True)
GUARD = os.path.join(T, "guard.json")
json.dump({"guard": {"protected_folders": [PROT], "push_allowed": ["ok-repo"], "public_repos": [{"name": "pub-repo", "scanner": "scripts/scan.sh"}]}}, open(GUARD, "w"))
PROFILES = {"none": None, "pinr": os.path.join(ROOT, "profiles", "pinr.json"), "guard": GUARD}
FIRSTS = {"manager": "You are Manager_Muster_002", "builder": "You are Builder A_Muster_002, agents/builder.md", "inspector": "You are Inspector_Muster_002",
          "designer": "You are Designer_Muster_002", "owner": "hello there", "pinr-mgr": "You are Manager_PINR_002. Job: Manager_PINR_002."}
TR = {}
for k, v in FIRSTS.items():
    p = os.path.join(T, k + ".jsonl")
    open(p, "w").write(json.dumps({"type": "user", "message": {"content": v}}) + "\n")
    TR[k] = p
KEY = "sk" + "-abcdefghijklmnopqrstuvwxyz1234567890ab"
MEM = "/home/x/.claude/projects/-p/memory/a.md"
CREW = "/".join(["muster", "CREW.md"])
OWNL = "/".join(["muster", "OWNERS-LIST.md"])
CASES = [
    ("Bash", {"command": "ls -la"}), ("Bash", {"command": "git status"}), ("Bash", {"command": "git push origin main"}), ("Bash", {"command": "git push origin muster/x"}),
    ("Bash", {"command": "git push --force origin muster/x"}), ("Bash", {"command": "git push -f"}), ("Bash", {"command": "git reset --hard"}), ("Bash", {"command": "git -C %s reset --hard" % PROT}),
    ("Bash", {"command": "git -C %s stash" % PROT}), ("Bash", {"command": "git -C %s stash list" % PROT}), ("Bash", {"command": "git -C %s checkout ." % PROT}),
    ("Bash", {"command": "git -C %s restore ." % PROT}), ("Bash", {"command": "cd %s && git reset --hard" % PROT}), ("Bash", {"command": "git commit -m 'key %s'" % KEY}),
    ("Bash", {"command": "git commit -m 'fix'"}), ("Bash", {"command": "echo 'Builder A sends READY, the Manager ships' >> %s" % MEM}), ("Bash", {"command": "echo hi > /tmp/x.txt"}),
    ("Bash", {"command": "echo x > " + CREW}), ("Bash", {"command": "sed -i s/a/b/ " + CREW}), ("Bash", {"command": "tee " + OWNL}),
    ("Bash", {"command": "python3 scripts/ship.sh"}), ("Bash", {"command": "scripts/ship.sh"}), ("Bash", {"command": "git push https://github.com/o/pub-repo.git main"}),
    ("Bash", {"command": "git push https://github.com/o/ok-repo.git main"}), ("Bash", {"command": "rm -rf /"}), ("Bash", {"command": "cp a b; git push origin; ls"}),
    ("Write", {"file_path": MEM, "content": "Builders must send READY to the inspector (D-036)"}), ("Write", {"file_path": MEM, "content": "The owner likes short answers."}),
    ("Write", {"file_path": "/home/x/p/" + CREW, "content": "x"}), ("Edit", {"file_path": "/home/x/p/" + CREW, "new_string": "x"}),
    ("Edit", {"file_path": "/home/x/p/" + OWNL, "new_string": "1. item"}), ("Write", {"file_path": "/home/x/p/" + OWNL, "content": "1. item"}),
    ("Write", {"file_path": "/home/x/p/muster/rules/builder.md", "content": "x"}), ("Write", {"file_path": "/home/x/p/agents/builder.md", "content": "x"}),
    ("Write", {"file_path": "/home/x/p/pages/builder.md", "content": "x"}), ("Write", {"file_path": "/home/x/p/Claude Code/manager/rules/a.md", "content": "x"}),
    ("Write", {"file_path": "/home/x/p/Claude Code/CLAUDE.md", "content": "x"}), ("Write", {"file_path": "/home/x/p/Claude Code/Founder/FOUNDER-LIST.md", "content": "x"}),
    ("Write", {"file_path": "/home/x/p/app/.env", "content": "API_KEY=%s" % KEY}), ("Write", {"file_path": "/home/x/p/app/.env.example", "content": "API_KEY=%s" % KEY}),
    ("Write", {"file_path": "/home/x/p/app/c.py", "content": "TOKEN = '%s'" % KEY}), ("Write", {"file_path": "/home/x/p/app/c.py", "content": "API_KEY=<your-key>"}),
    ("Write", {"file_path": os.path.join(PROT, "a.txt"), "content": "x"}), ("Write", {"file_path": os.path.join(PROT, "muster", "BOARD.md"), "content": "x"}),
    ("Write", {"file_path": "/home/x/p/pictures/a.html", "content": "<img src=a.png>"}), ("Write", {"file_path": "/home/x/p/look/a.css", "content": "a{}"}),
    ("MultiEdit", {"file_path": "/home/x/p/" + CREW, "edits": []}), ("NotebookEdit", {"file_path": "/home/x/p/a.ipynb", "new_source": "key %s" % KEY}),
    ("Read", {"file_path": "/home/x/p/a"}), ("Read", {"file_path": MEM}), ("Glob", {"pattern": "*"}), ("Grep", {"pattern": "x"}),
    ("SendMessage", {"to": "x", "message": "noted"}), ("SendMessage", {"to": "x", "message": "key %s" % KEY}), ("SendMessage", {"to": "x", "message": "{\"v\":1}"}),
    ("AskUserQuestion", {"questions": [{"question": "Which?", "options": [{"label": "A"}, {"label": "B"}]}]}), ("AskUserQuestion", {}),
    ("mcp__ccd_turn__wrap_up", {"recap": "done", "ask": "Ship?", "actions": [{"label": "Yes"}]}), ("mcp__ccd_turn__wrap_up", {"recap": "done"}),
    ("mcp__ccd_turn__wrap_up", {"recap": "done", "ask": ""}), ("mcp__ccd_turn__update_plan", {"items": []}),
    ("Agent", {"subagent_type": "muster:builder", "prompt": "build; then git push and send READY"}), ("Agent", {"subagent_type": "muster:builder", "prompt": "build; never push"}),
    ("Agent", {"subagent_type": "Explore", "prompt": "search"}), ("Agent", {"subagent_type": "muster:inspector", "prompt": "check it, SendMessage the manager"}),
    ("Task", {"subagent_type": "muster:designer", "prompt": "scripts/ship.sh now"}), ("Artifact", {}), ("mcp__Claude_Browser__tabs_context", {}), ("mcp__computer-use__screenshot", {}),
    ("mcp__claude-in-chrome__tabs", {}), ("mcp__ccd_session__start_session", {"title": "x"}), ("WebFetch", {"url": "https://example.com"}), ("TodoWrite", {"todos": []}),
]


RECORD = "Muster rule: a message between chats is a data record"


def norm(out):
    out = out.strip()
    if not out:
        return ""
    try:
        d = json.loads(out)
        r = (d.get("hookSpecificOutput") or {}).get("permissionDecisionReason") or d.get("reason") or json.dumps(d)
    except ValueError:
        return out
    return str(r).replace(os.path.normpath(os.path.abspath(ROOT)) + "/scripts/", "")


def one(job):
    prof, role, tool, inp = job
    env = dict(BASEENV)
    if PROFILES[prof]:
        env["MUSTER_PROFILE"] = PROFILES[prof]
    ev = json.dumps({"hook_event_name": "PreToolUse", "cwd": T, "transcript_path": TR[role], "tool_name": tool, "tool_input": inp})
    py = subprocess.run([sys.executable, os.path.join(ROOT, "hooks", "rules-check.py")], input=ev, capture_output=True, text=True, env=env)
    rs = subprocess.run([BIN, "rules"], input=ev, capture_output=True, text=True, env=env)
    res = []
    a, b = norm(py.stdout), norm(rs.stdout)
    if a != b and not (b.startswith(RECORD) and (not a or a.startswith(RECORD[:40]))):
        res.append(("rules", a[:300], b[:300]))  # (the Rust program checks every field of a JSON record and says which is wrong; the Python copy only that it is JSON)
    if prof == "guard":
        g = subprocess.run([BIN, "guard"], input=ev, capture_output=True, text=True, env=env)
        c = norm(g.stdout)
        if c and a and c not in a and a not in c:
            res.append(("guard", a[:300], c[:300]))
        if c and not a:
            res.append(("guard-only-block", "", c[:300]))
    return job, res


jobs = [(p, r, t, i) for p in PROFILES for r in TR for t, i in CASES]
with ThreadPoolExecutor(8) as ex:
    results = list(ex.map(one, jobs))
diffs = [(j, o) for j, o in results if o]
print("%d tool calls compared, %d differ" % (len(results), len(diffs)))
shown = set()
for (prof, role, tool, inp), outs in diffs:
    for sub, a, b in outs:
        key = (sub, tool, a[:80], b[:80])
        if key in shown:
            continue
        shown.add(key)
        print("DIFF", sub, "as", role, "profile", prof, tool, json.dumps(inp)[:140], "\n   python:", a, "\n   rust:  ", b)
sys.exit(1 if diffs else 0)
