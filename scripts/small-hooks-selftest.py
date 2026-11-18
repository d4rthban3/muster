#!/usr/bin/env python3
"""Self-test for the three small hooks (rust-first piece 3): hooks/renew-after-summary.py, hooks/precompact-board.py and scripts/usage.py.
Runs the Python copies always; with MUSTER_CHECKS_BIN set it also runs the ready-built program's renew, precompact and usage and demands the
same answer, and runs the shell hooks with the program present (they use it) and absent (they fall back to Python, same answer).
Writes only in a temporary folder. Standard library only. Prints 'N of M passed'; exit 1 on any failure."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BIN = os.environ.get("MUSTER_CHECKS_BIN")
T = tempfile.mkdtemp()
PINR = os.path.join(ROOT, "profiles", "pinr.json")
PLUG = os.path.join(T, "p1", "plugin")
for d in ("hooks", "scripts", "profiles"):
    shutil.copytree(os.path.join(ROOT, d), os.path.join(PLUG, d), ignore=shutil.ignore_patterns("__pycache__"))
os.makedirs(os.path.join(PLUG, ".claude-plugin"))
shutil.copyfile(os.path.join(ROOT, ".claude-plugin", "plugin.json"), os.path.join(PLUG, ".claude-plugin", "plugin.json"))
BINX = None
if BIN:  # the program runs from a plugin-shaped folder (bin/<name>/), as shipped, so it finds hooks/talk-block.txt and scripts/ the way it does for a user
    os.makedirs(os.path.join(PLUG, "bin", "stage"))
    BINX = os.path.join(PLUG, "bin", "stage", "muster-checks")
    shutil.copyfile(BIN, BINX)
    os.chmod(BINX, 0o755)
results = []


def add(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else "\n     " + detail))


def env(**kw):
    e = {k: v for k, v in os.environ.items() if k not in ("MUSTER_PROFILE", "CLAUDE_CONFIG_DIR", "MUSTER_CHECKS_BIN")}
    e.update(kw)
    return e


def transcript(first, extra=(), title=None, summary_first=False):
    p = os.path.join(T, "t%d.jsonl" % len(os.listdir(T)))
    with open(p, "w") as f:
        if summary_first:
            f.write(json.dumps({"type": "user", "isCompactSummary": True, "message": {"content": "This session is being continued... You are Builder A_Muster_002"}}) + "\n")
        else:
            f.write(json.dumps({"type": "user", "message": {"content": first}}) + "\n")
        if title:
            f.write(json.dumps({"type": "custom-title", "customTitle": title}) + "\n")
        for e in extra:
            f.write(json.dumps(e) + "\n")
    return p


def both(py_cmd, rs_args, stdin, e, cwd=None, py_args=()):
    """Run the Python copy and (when a program is given) the program; return [(name, rc, stdout)]."""
    out = [("python", subprocess.run([sys.executable] + py_cmd + list(py_args), input=stdin, capture_output=True, text=True, env=e, cwd=cwd))]
    if BIN:
        out.append(("rust", subprocess.run([BINX] + rs_args, input=stdin, capture_output=True, text=True, env=e, cwd=cwd)))
    return [(n, r.returncode, r.stdout) for n, r in out]


def same(name, runs, check=None):
    """All copies answer alike, and the answer passes check(rc, stdout) when one is given."""
    base = runs[0]
    alike = all(r[1:] == base[1:] for r in runs)
    ok = alike and (check is None or check(base[1], base[2]))
    add(name, ok, "\n     ".join("%s rc=%s %r" % (n, rc, o[:200]) for n, rc, o in runs))


RENEW = ["hooks/renew-after-summary.py"]
RP = lambda p: [os.path.join(ROOT, p)]


def renew(first, prof=None, **kw):
    ev = json.dumps({"transcript_path": transcript(first, **kw)})
    e = env(**({"MUSTER_PROFILE": prof} if prof else {}))
    return both(RP("hooks/renew-after-summary.py"), ["renew"], ev, e)


said = lambda rc, o: rc == 0 and "compacted in place" in o
silent = lambda rc, o: rc == 0 and o == ""
same("renew: a Muster manager chat is told it was compacted in place, and the talking rules come back", renew("You are Manager_Muster_002"), said)
same("renew: a builder chat too", renew("You are Builder A_Muster_002, agents/builder.md"), said)
same("renew: a chat naming only a role file", renew("Read agents/inspector.md and begin"), said)
same("renew: the owner's own chat is silent", renew("hello there"), silent)
same("renew: a PINR-named chat is crew only with the profile", renew("You are Site_PINR_002. Job: Site_PINR_002.", prof=PINR), said)
same("renew: ...and not without it", renew("You are Site_PINR_002. Job: Site_PINR_002."), silent)
same("renew: a chat that opens with a summary is known by its title", renew("x", title="Builder A_Muster_002", summary_first=True), said)
same("renew: ...but not when the title is no crew name", renew("x", title="My notes", summary_first=True), silent)
same("renew: a chat whose first line is a tool result still finds its first message",
     renew("", extra=[{"type": "user", "message": {"content": "You are Designer_Muster_001"}}]), said)
same("renew: an empty event and an unreadable transcript stay silent and never fail",
     both(RP("hooks/renew-after-summary.py"), ["renew"], "{}", env()), silent)
same("renew: input that is not JSON stays silent", both(RP("hooks/renew-after-summary.py"), ["renew"], "not json", env()), silent)
json.dump({"crew_names": ["(unclosed"]}, open(os.path.join(T, "bad.json"), "w"))
add("renew: a profile with a pattern nobody can compile says nothing (Python stops with an error, the program stays quiet)",
    all(o == "" for _, _, o in renew("You are Manager_Muster_002", prof=os.path.join(T, "bad.json"))))

# the talking rules (hooks/talk-block.txt) follow the message
rr = renew("You are Manager_Muster_002")
block = open(os.path.join(ROOT, "hooks", "talk-block.txt"), encoding="utf-8").read().rstrip()
add("renew: the message ends with the talking rules, as the file holds them", all(block in o for _, _, o in rr), repr(rr[-1][2][-200:]))

# precompact: one board entry per crew chat
GIT = lambda *a, cwd: subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True)
PROJ = os.path.join(T, "proj")
os.makedirs(os.path.join(PROJ, "muster"))
GIT("init", "-q", cwd=PROJ)
GIT("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "start", cwd=PROJ)
JOBREC = {"type": "user", "message": {"content": '{"v":1,"kind":"ORDER","job":"approval-relay","note":"ship approval-relay next"}'}}
NORM = [(re.compile(r"\d{4}-\d\d-\d\d"), "DATE"), (re.compile(r"(\[ID compact-[a-z0-9-]*-)\d{6}\]"), r"\1TIME]")]


def pre(first, which, board=True, cwd=None, prof=None, extra=(), **kw):
    """Run one copy ("python" or "rust") on its own copy of the board and transcript; return (rc, new board text, side file made)."""
    b = os.path.join(T, "board-%s-%d" % (which, len(os.listdir(T))))
    os.makedirs(os.path.join(b, "muster"))
    if board:
        open(os.path.join(b, "muster", "BOARD.md"), "w").write("# Board\n")
    tp = transcript(first, extra, **kw)
    ev = json.dumps({"transcript_path": tp, "cwd": cwd or b})
    e = env(**({"MUSTER_PROFILE": prof} if prof else {}))
    cmd = [sys.executable, os.path.join(ROOT, "hooks", "precompact-board.py")] if which == "python" else [BINX, "precompact"]
    r = subprocess.run(cmd, input=ev, capture_output=True, text=True, env=e)
    text = open(os.path.join(b, "muster", "BOARD.md")).read() if board else ""
    for rx, to in NORM:
        text = rx.sub(to, text)
    return r.returncode, r.stdout, text, os.path.exists(tp + ".muster-first")


def pre_both(name, first, check, **kw):
    runs = [("python", pre(first, "python", **kw))] + ([("rust", pre(first, "rust", **kw))] if BIN else [])
    alike = all(r[1] == runs[0][1] for r in runs)
    ok = alike and check(*runs[0][1])
    add(name, ok, "\n     ".join("%s %r" % (n, r) for n, r in runs))


pre_both("precompact: a crew chat leaves one entry naming itself, its job and its next step", "You are Builder A_Muster_002",
         lambda rc, out, board, side: rc == 0 and out == "" and "Builder A_Muster_002 -> Manager | compaction" in board and "open job approval-relay" in board
         and "ship approval-relay next" in board and "Status: done" in board and "Need:  none" in board and side, extra=[JOBREC])
pre_both("precompact: with no job in sight it says so", "You are Builder A_Muster_002",
         lambda rc, out, board, side: "none named in its last messages" in board and "read its summary and the board entries addressed to it" in board)
pre_both("precompact: the owner's own chat leaves nothing", "hello there", lambda rc, out, board, side: rc == 0 and board == "# Board\n" and not side)
pre_both("precompact: a chat with no board leaves nothing and never blocks", "You are Builder A_Muster_002", lambda rc, out, board, side: rc == 0 and out == "", board=False)
pre_both("precompact: a PINR-named chat is crew with the profile", "You are Site_PINR_002. Job: Site_PINR_002.",
         lambda rc, out, board, side: "Site_PINR_002 -> Manager | compaction" in board, prof=PINR)
pre_both("precompact: ...and not without it", "You are Site_PINR_002. Job: Site_PINR_002.", lambda rc, out, board, side: board == "# Board\n")
pre_both("precompact: a chat that opens with a summary is known by its title", "x",
         lambda rc, out, board, side: "Builder A_Muster_002 -> Manager | compaction" in board, title="Builder A_Muster_002", summary_first=True)
pre_both("precompact: a role-file-only chat is named by its role", "Read agents/designer.md", lambda rc, out, board, side: "designer -> Manager | compaction" in board)
# a git folder with a board: both copies read the same branch and version
GB = os.path.join(T, "gitboard")
os.makedirs(os.path.join(GB, "muster"))
open(os.path.join(GB, "muster", "BOARD.md"), "w").write("# Board\n")
GIT("init", "-q", cwd=GB)
GIT("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "start", cwd=GB)
GIT("checkout", "-q", "-b", "muster/some-job", cwd=GB)
got = []
for which in ["python"] + (["rust"] if BIN else []):
    shutil.copyfile(os.path.join(GB, "muster", "BOARD.md"), os.path.join(T, "gb.keep"))
    tp = transcript("You are Builder A_Muster_002", [JOBREC])
    cmd = [sys.executable, os.path.join(ROOT, "hooks", "precompact-board.py")] if which == "python" else [BINX, "precompact"]
    subprocess.run(cmd, input=json.dumps({"transcript_path": tp, "cwd": GB}), capture_output=True, text=True, env=env())
    t = open(os.path.join(GB, "muster", "BOARD.md")).read()
    for rx, to in NORM:
        t = rx.sub(to, t)
    got.append(t.split("# Board\n")[-1].replace(GIT("rev-parse", "--short", "HEAD", cwd=GB).stdout.strip(), "SHA"))
    shutil.copyfile(os.path.join(T, "gb.keep"), os.path.join(GB, "muster", "BOARD.md"))
add("precompact: in a git folder both copies write the branch and the saved version", all("branch muster/some-job at SHA." in g for g in got) and len(set(got)) == 1, "\n".join(got))
# from a linked worktree the entry goes to the main folder's board
WT = os.path.join(T, "gitboard-wt")
GIT("worktree", "add", "-q", "-b", "muster/wt-job", WT, cwd=GB)
got = []
for which in ["python"] + (["rust"] if BIN else []):
    tp = transcript("You are Builder A_Muster_002", [JOBREC])
    cmd = [sys.executable, os.path.join(ROOT, "hooks", "precompact-board.py")] if which == "python" else [BINX, "precompact"]
    subprocess.run(cmd, input=json.dumps({"transcript_path": tp, "cwd": WT}), capture_output=True, text=True, env=env())
    got.append(open(os.path.join(GB, "muster", "BOARD.md")).read().count("branch muster/wt-job at"))
add("precompact: from a linked worktree the entry goes to the main folder's board", got == [1] + ([2] if BIN else []), repr(got))

# usage line
CFG = os.path.join(T, "cfg")
U = os.path.join(CFG, "muster-usage")
os.makedirs(U)


def usage(*args, files=None, mtimes=None):
    shutil.rmtree(U)
    os.makedirs(U)
    for n, d in (files or {}).items():
        with open(os.path.join(U, n), "w") as f:
            f.write(d if isinstance(d, str) else json.dumps(d))
    for i, n in enumerate(mtimes or []):
        os.utime(os.path.join(U, n), (1000 + i, 1000 + i))
    e = env(CLAUDE_CONFIG_DIR=CFG)
    return both(RP("scripts/usage.py"), ["usage"] + list(args), "", e, py_args=args)


FULL = {"cost_usd": 0.314, "week_used_percent": 41.2, "week_resets_at": 1893456000, "saved_at": 1893400000}
same("usage: nothing saved says so and exits 0", usage(), lambda rc, o: rc == 0 and "not readable (Muster's status line is not saving usage here" in o)
same("usage: a damaged file says so", usage(files={"a.json": "{nope"}), lambda rc, o: rc == 0 and "saved usage file is damaged" in o)
same("usage: the full line", usage(files={"a.json": FULL}), lambda rc, o: o == "Usage: session $0.31 at list price; week 41%% used (resets %s); read at %s\n" % (time.strftime("%a %d %b", time.localtime(1893456000)), time.strftime("%H:%M", time.localtime(1893400000))) and rc == 0)
same("usage: no week figure says what is needed", usage(files={"a.json": {"cost_usd": 1}}), lambda rc, o: "week limit not readable" in o and rc == 0)
same("usage: no cost says so", usage(files={"a.json": {"week_used_percent": 10}}), lambda rc, o: "session cost not readable" in o and "week 10% used (resets ?)" in o and "read at %s" % time.strftime("%H:%M", time.localtime(0)) in o)
same("usage: 90% and over exits 3", usage(files={"a.json": dict(FULL, week_used_percent=90)}), lambda rc, o: rc == 3 and "week 90% used" in o)
same("usage: 89.9 does not", usage(files={"a.json": dict(FULL, week_used_percent=89.9)}), lambda rc, o: rc == 0 and "week 90% used" in o)
same("usage: --limit-percent moves the line", usage("--limit-percent", "50", files={"a.json": FULL, }), lambda rc, o: rc == 0)
same("usage: ...and 40 trips it", usage("--limit-percent=40", files={"a.json": FULL}), lambda rc, o: rc == 3)
same("usage: halves round to the even number (40.5 is 40, 41.5 is 42)", usage(files={"a.json": dict(FULL, week_used_percent=40.5)}), lambda rc, o: "week 40% used" in o)
same("usage: ...41.5", usage(files={"a.json": dict(FULL, week_used_percent=41.5)}), lambda rc, o: "week 42% used" in o)
same("usage: the newest file is read", usage(files={"old.json": dict(FULL, week_used_percent=10), "new.json": dict(FULL, week_used_percent=20)}, mtimes=["old.json", "new.json"]), lambda rc, o: "week 20% used" in o)
same("usage: --session names a file", usage("--session", "old", files={"old.json": dict(FULL, week_used_percent=10), "new.json": dict(FULL, week_used_percent=20)}, mtimes=["old.json", "new.json"]), lambda rc, o: "week 10% used" in o)
same("usage: --session that is not there says nothing is saved", usage("--session", "ghost", files={"a.json": FULL}), lambda rc, o: "not saving usage here" in o)
same("usage: a hidden file is not read", usage(files={".a.json": FULL}), lambda rc, o: "not saving usage here" in o)
same("usage: an unknown option is refused with exit 2", usage("--nope"), lambda rc, o: rc == 2)


# the program's rules check stops a new JSON order when the week is at 90% (it asks its own usage code, as scripts/usage.py exits 3).
# (The Python rules check only holds a text-form order for this; a JSON order passes it: a known difference, the program being the stricter.)
if BIN:
    RP_ = os.path.join(T, "rulesproj")
    for d in ("muster", "scripts", "agents"):
        os.makedirs(os.path.join(RP_, d))
    open(os.path.join(RP_, "muster", "BOARD.md"), "w").write("# Board\n\n## Entries\n")
    ORDER = {"v": 1, "kind": "ORDER", "id": "manager-job-1", "job": "job", "from": "manager", "to": "builder-a", "owner_words": {"item": 12}, "owns": ["board"], "out": ["site"], "action": "start", "need": "none"}
    MGR = transcript("You are Manager_Muster_002")
    for pct, want in ((95, True), (10, False)):
        shutil.rmtree(U)
        os.makedirs(U)
        json.dump({"week_used_percent": pct, "saved_at": 1}, open(os.path.join(U, "a.json"), "w"))
        ev = json.dumps({"hook_event_name": "PreToolUse", "cwd": RP_, "transcript_path": MGR, "tool_name": "SendMessage", "tool_input": {"to": "x", "message": json.dumps(ORDER)}})
        r = subprocess.run([BINX, "rules"], input=ev, capture_output=True, text=True, env=env(CLAUDE_CONFIG_DIR=CFG, MUSTER_STATE_DIR=T))
        add("rules (program): a new order is %s when the week is at %d%%" % ("held" if want else "let through", pct), ("week is at 90% or more" in r.stdout) == want, r.stdout[:200])

# the shell hooks: the program first, Python when no program is found
MP = os.path.join(T, "musterproj")
os.makedirs(os.path.join(MP, "muster"))
open(os.path.join(MP, "muster", "CLAUDE.md"), "w").write("x\n")
open(os.path.join(MP, "muster", "BOARD.md"), "w").write("# Board\n")


def shell(script, ev, plugin=PLUG):
    r = subprocess.run(["sh", os.path.join(plugin, "hooks", script)], input=json.dumps(ev), capture_output=True, text=True, env=env(), cwd=MP)
    return r.returncode, r.stdout


def put_program(plugin):
    for d, exe in (("windows-x86_64", "muster-checks.exe"), ("macos-arm64", "muster-checks"), ("macos-x86_64", "muster-checks"), ("linux-x86_64", "muster-checks"), ("linux-arm64", "muster-checks")):
        os.makedirs(os.path.join(plugin, "bin", d), exist_ok=True)
        shutil.copyfile(BIN, os.path.join(plugin, "bin", d, exe))
        os.chmod(os.path.join(plugin, "bin", d, exe), 0o755)


NOPROG = shell("renew-after-summary.sh", {"transcript_path": transcript("You are Manager_Muster_002")})
add("the summary hook runs from Python when no program is found", NOPROG[0] == 0 and "compacted in place" in NOPROG[1], repr(NOPROG))
NOPRE = shell("precompact-board.sh", {"transcript_path": transcript("You are Manager_Muster_002"), "cwd": MP})
add("the PreCompact hook runs from Python when no program is found", NOPRE[0] == 0 and "Manager_Muster_002 -> Manager | compaction" in open(os.path.join(MP, "muster", "BOARD.md")).read())
if BIN:
    PLUG2 = os.path.join(T, "p2", "plugin")
    shutil.copytree(PLUG, PLUG2)
    put_program(PLUG2)
    # a program that is present answers first: prove it by pointing the Python copy at a broken interpreter path (the program must not need Python)
    for f in ("renew-after-summary.py", "precompact-board.py"):
        open(os.path.join(PLUG2, "hooks", f), "w").write("import sys\nsys.stdout.write('PYTHON RAN')\n")
    WITH = shell("renew-after-summary.sh", {"transcript_path": transcript("You are Manager_Muster_002")}, PLUG2)
    add("the summary hook uses the program when one is found", WITH[0] == 0 and "compacted in place" in WITH[1] and "PYTHON RAN" not in WITH[1], repr(WITH))
    n = open(os.path.join(MP, "muster", "BOARD.md")).read().count("compaction")
    WP = shell("precompact-board.sh", {"transcript_path": transcript("You are Manager_Muster_002"), "cwd": MP}, PLUG2)
    add("the PreCompact hook uses the program when one is found", WP[0] == 0 and WP[1] == "" and open(os.path.join(MP, "muster", "BOARD.md")).read().count("compaction") == n + 1)
    # a program that does not know the check yet (exit 2, as an older program does) leaves it to the Python copy
    PLUG3 = os.path.join(T, "p3", "plugin")
    shutil.copytree(PLUG, PLUG3)
    for d in ("windows-x86_64", "macos-arm64", "macos-x86_64", "linux-x86_64", "linux-arm64"):
        os.makedirs(os.path.join(PLUG3, "bin", d), exist_ok=True)
        for exe in ("muster-checks", "muster-checks.exe"):
            with open(os.path.join(PLUG3, "bin", d, exe), "w") as f:
                f.write("#!/bin/sh\nexit 2\n")
            os.chmod(os.path.join(PLUG3, "bin", d, exe), 0o755)
    OLD = shell("renew-after-summary.sh", {"transcript_path": transcript("You are Manager_Muster_002")}, PLUG3)
    add("an older program that does not know the summary hook leaves it to Python", OLD[0] == 0 and "compacted in place" in OLD[1], repr(OLD))

n_ok = sum(1 for _, ok in results if ok)
print("%d of %d passed" % (n_ok, len(results)))
sys.exit(0 if n_ok == len(results) else 1)
