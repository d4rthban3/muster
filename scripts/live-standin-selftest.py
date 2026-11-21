#!/usr/bin/env python3
"""Self-test for rust-first piece 6: a project with Muster installed live (install-checks.py --live) runs each check through the ready-built program first,
told its project and given the Muster folder's live profile, and through the Python live stand-in when the program is absent or fails.
Made-up project and made-up Muster folder in a temporary folder; nothing outside it is touched. Needs sh (Git Bash on Windows) and Python 3.
With MUSTER_CHECKS_BIN set to the Rust program the real program is also run and its answers compared with the Python stand-ins'.
Prints PASS/FAIL lines; exit 1 on any failure."""
import json, os, platform, shutil, stat, subprocess, sys, tempfile, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BIN = os.environ.get("MUSTER_CHECKS_BIN")
T = tempfile.mkdtemp()
WIN = os.name == "nt"
PY = sys.executable
bad = 0
def t(name, ok, why=""):
    global bad; bad += (not ok); print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  -> " + str(why)[:300]))
def sysdir():
    s = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}.get(platform.system(), "linux")
    m = platform.machine().lower()
    a = "arm64" if m in ("arm64", "aarch64") and s != "windows" else "x86_64"
    return "%s-%s" % (s, a), "muster-checks.exe" if s == "windows" else "muster-checks"
BINDIR, EXE = sysdir()
CHECKS = [("rules-check", "rules"), ("board-stop", "board-stop"), ("talk-check", "talk"), ("worker-queue-check", "worker-queue"),
          ("idle-check", "idle-check"), ("renew-after-summary", "renew"), ("precompact-board", "precompact")]

def muster(program=None, stub=None):
    """A made-up Muster folder: the real hooks, scripts and profiles, and (when given) a program or a stand-in program script in this computer's bin folder."""
    m = os.path.join(tempfile.mkdtemp(dir=T), "muster")
    for d in ("hooks", "scripts", "profiles"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(m, d), ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(os.path.join(m, ".claude-plugin")); open(os.path.join(m, ".claude-plugin", "plugin.json"), "w").write("{}")
    if program or stub:
        os.makedirs(os.path.join(m, "bin", BINDIR))
        dst = os.path.join(m, "bin", BINDIR, EXE)
        if program:
            shutil.copyfile(program, dst)
        else:
            open(dst, "w").write(stub if stub.startswith("#!") else "#!/bin/sh\n" + stub + "\n")
        os.chmod(dst, 0o755)
    return m

def project(m):
    p = os.path.join(tempfile.mkdtemp(dir=T), "proj")
    os.makedirs(os.path.join(p, "manager")); os.makedirs(os.path.join(p, "muster")); os.makedirs(os.path.join(p, "Founder"))
    os.makedirs(os.path.join(p, "PINR-claudecode-handoff", "pinr-claude-code-starter-v2"))
    open(os.path.join(p, "PINR-claudecode-handoff", "pinr-claude-code-starter-v2", "DECISIONS-LOG.md"), "w").write("# log\n")
    open(os.path.join(p, "muster", "BOARD.md"), "w").write("# Board\n")
    r = subprocess.run([PY, os.path.join(ROOT, "scripts", "install-checks.py"), p, "--profile", "pinr", "--live", m], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    return p

def tr(first, extra=()):
    f = os.path.join(T, "t%d.jsonl" % len(os.listdir(T)))
    with open(f, "w") as fh:
        fh.write(json.dumps({"type": "user", "message": {"content": first}}) + "\n")
        for e in extra: fh.write(json.dumps(e) + "\n")
    return f

ENV = {k: v for k, v in os.environ.items() if k not in ("MUSTER_PROFILE", "MUSTER_PROJECT", "CLAUDE_PROJECT_DIR")}
ENV["MUSTER_MESSAGE_FORM"] = "text"
def run(p, name, ev, ext="sh", env=None, raw=False):
    e = dict(ENV, CLAUDE_PROJECT_DIR=p, **(env or {}))
    f = os.path.join(p, ".muster-checks", name + "." + ext)
    c = ["sh", f] if ext == "sh" else [PY, f]
    r = subprocess.run(c, input=ev if raw else json.dumps(ev), capture_output=True, text=True, encoding="utf-8", cwd=p, env=e)
    return r.returncode, r.stdout

M0 = muster()
P0 = project(M0)
LC = os.path.join(P0, ".muster-checks")
# 1. what the installer wrote
t("installer: a shell stand-in for each of the seven checks, live.env, and the Python live stand-ins still there",
  all(os.path.isfile(os.path.join(LC, n + ".sh")) and os.path.isfile(os.path.join(LC, n + ".py")) for n, _ in CHECKS) and os.path.isfile(os.path.join(LC, "live.env")) and os.path.isfile(os.path.join(LC, "live.json")))
st = json.load(open(os.path.join(P0, ".claude", "settings.json")))
cmds = [h["command"] for ev in st["hooks"].values() for g in ev for h in g["hooks"]]
t("installer: every hook command runs a .sh stand-in with sh, none runs python3", cmds and all(".sh" in c and "exec sh" in c and "python3" not in c for c in cmds), cmds[:2])
env_txt = open(os.path.join(LC, "live.env")).read()
t("installer: live.env names the Muster folder (forward slashes) and the live profile", "MUSTER_FOLDER='%s'" % M0.replace("\\", "/") in env_txt and "profiles/pinr.json" in env_txt, env_txt)
dry = subprocess.run([PY, os.path.join(ROOT, "scripts", "install-checks.py"), tempfile.mkdtemp(dir=T), "--live", M0, "--dry-run"], capture_output=True, text=True)
t("installer: --dry-run says it and writes nothing", dry.returncode == 0 and "DRY RUN" in dry.stdout)
pp = os.path.join(T, "plain"); os.makedirs(pp)
subprocess.run([PY, os.path.join(ROOT, "scripts", "install-checks.py"), pp], capture_output=True, text=True)
pst = json.load(open(os.path.join(pp, ".claude", "settings.json")))
t("installer: plain copies (no --live) stay on Python and write no .sh", not any(os.path.exists(os.path.join(pp, ".muster-checks", n + ".sh")) for n, _ in CHECKS) and "python3" in json.dumps(pst))
pl = project(muster())
subprocess.run([PY, os.path.join(ROOT, "scripts", "install-checks.py"), pl], capture_output=True, text=True)
t("installer: a plain install over a live one takes the .sh stand-ins and live.env away", not any(os.path.exists(os.path.join(pl, ".muster-checks", n + ".sh")) for n, _ in CHECKS) and not os.path.exists(os.path.join(pl, ".muster-checks", "live.env")))
pr = project(muster()); subprocess.run([PY, os.path.join(ROOT, "scripts", "install-checks.py"), pr, "--remove"], capture_output=True, text=True)
t("installer: --remove takes the stand-ins away", not os.path.exists(os.path.join(pr, ".muster-checks")))

# 2. the program is run first, told the project, given the live profile (a stand-in program that prints what it was given; a shell script cannot be a .exe, so on Windows the real program does this in part 7)
STUB = 'echo "PROGRAM $1 project=$MUSTER_PROJECT profile=$MUSTER_PROFILE"; cat >/dev/null'
Ms = muster(stub=STUB if not WIN else None); Ps = project(Ms)
for name, sub in (CHECKS if not WIN else []):
    rc, out = run(Ps, name, {})
    want_prof = os.path.join(Ms, "profiles", "pinr.json").replace("\\", "/")
    t("program first: %s.sh runs `%s`, names the project and the live profile" % (name, sub),
      rc == 0 and out.startswith("PROGRAM %s project=" % sub) and os.path.realpath(out.split("project=")[1].split(" profile=")[0]) == os.path.realpath(Ps)
      and out.strip().endswith("profiles/pinr.json"), out)
rc, out = run(Ps, "rules-check", {}, env={"MUSTER_PROFILE": os.path.join(Ms, "profiles", "muster.json")})
if not WIN:
    t("program first: a profile the caller already named is kept", out.strip().endswith("profiles/muster.json"), out)
    rc, out = run(Ps, "rules-check", {"x": 1})
    t("program first: a program with exit 0 is trusted and Python is not run beside it", out.count("PROGRAM") == 1 and "systemMessage" not in out)

# 3. the safety net: the Python live stand-in runs when the program is absent or fails, and never beside half a program answer
PYANS = None
for label, mm in ([("no program in the Muster folder", muster())] + ([] if WIN else [("a program that exits 1", muster(stub="echo PARTIAL; exit 1")), ("a crash (exit 101) after half an answer", muster(stub="echo PARTIAL; exit 101")),
                  ("an older program that exits 2", muster(stub="exit 2")), ("a program that will not start", muster(stub="#!/nonexistent/interpreter\nexit 0"))])):
    pj = project(mm)
    ev = {"hook_event_name": "PreToolUse", "cwd": pj, "tool_name": "AskUserQuestion", "tool_input": {"questions": [{"question": "Ship it?", "options": []}]}, "transcript_path": tr("You are Manager_PINR_008. Job: Manager_PINR_008.")}
    a = run(pj, "rules-check", ev); b = run(pj, "rules-check", ev, ext="py")
    t("fallback: %s -> the Python stand-in answers, alone" % label, a == b and "PARTIAL" not in a[1] and "Muster rule" in a[1], (a, b))
if not WIN:
    pj = project(muster(stub="echo PARTIAL; kill -9 $$"))
    a = run(pj, "rules-check", {}); b = run(pj, "rules-check", {}, ext="py")
    t("fallback: a program that is killed -> the Python stand-in answers, alone", a == b and "PARTIAL" not in a[1], (a, b))

# 4. a Muster folder that is gone is said plainly, and the turn goes on
gone = muster(); pg = project(gone); shutil.move(gone, gone + ".gone")
rc, out = run(pg, "rules-check", {})
t("a missing Muster folder is said plainly, never silently", rc == 0 and gone.replace("\\", "/") in json.loads(out).get("systemMessage", "").replace("\\", "/") and "decision" not in json.loads(out), out)

# 5. an older Muster folder without the program scripts still works through Python
old = muster(); os.remove(os.path.join(old, "scripts", "try-program.sh")); po = project(old)
ev = {"hook_event_name": "PreToolUse", "cwd": po, "tool_name": "AskUserQuestion", "tool_input": {"questions": [{"question": "Ship it?", "options": []}]}, "transcript_path": tr("You are Manager_PINR_008. Job: Manager_PINR_008.")}
t("an older Muster folder with no program scripts runs the Python stand-in", "Muster rule" in run(po, "rules-check", ev)[1])

# 6. the hook command the installer wrote: runs from the project, and from a builder's worktree it runs the MAIN folder's stand-in
if shutil.which("git"):
    gm = os.path.join(T, "gitmain"); os.makedirs(os.path.join(gm, ".muster-checks"))
    g = lambda *a, cwd=gm: subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=t", *a], cwd=cwd, capture_output=True, text=True)
    g("init", "-q"); open(os.path.join(gm, "x"), "w").write("x"); g("add", "x"); g("commit", "-qm", "x")
    gw = os.path.join(T, "gitwt"); g("worktree", "add", "-q", gw); os.makedirs(os.path.join(gw, ".muster-checks"), exist_ok=True)
    open(os.path.join(gm, ".muster-checks", "rules-check.sh"), "w").write("echo LIVE-MAIN\n")
    open(os.path.join(gw, ".muster-checks", "rules-check.sh"), "w").write("echo OLD-IN-WORKTREE\n")
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import importlib.util as u
    sp = u.spec_from_file_location("ic", os.path.join(ROOT, "scripts", "install-checks.py")); ic = u.module_from_spec(sp); sp.loader.exec_module(ic)
    hk = lambda proj: subprocess.run(["sh", "-c", ic.cmd_sh("rules-check")], capture_output=True, text=True, cwd=proj, env=dict(ENV, CLAUDE_PROJECT_DIR=proj)).stdout.strip()
    t("hook command: a worktree runs the main folder's .sh stand-in, not the old one in the worktree", hk(gw) == "LIVE-MAIN", hk(gw))
    t("hook command: the main folder runs its own", hk(gm) == "LIVE-MAIN", hk(gm))

# 7. the real program, when given: the same answers as the Python stand-ins, with the project's profile
if BIN:
    mr = muster(program=BIN); pr_ = project(mr)
    mgr = tr("You are Manager_PINR_008. Job: Manager_PINR_008.")
    events = [
        ("a PINR manager's choice card is refused", {"hook_event_name": "PreToolUse", "cwd": pr_, "tool_name": "AskUserQuestion", "tool_input": {"questions": [{"question": "Ship it?", "options": []}]}, "transcript_path": mgr}, "rules-check"),
        ("a plain report card at the end of a turn", {"hook_event_name": "Stop", "cwd": pr_, "last_assistant_message": "**READY · x**\n- a\n- b", "transcript_path": mgr}, "rules-check"),
        ("the owner's own chat is silent", {"hook_event_name": "PreToolUse", "cwd": pr_, "tool_name": "Bash", "tool_input": {"command": "ls"}, "transcript_path": tr("hello there")}, "rules-check"),
        ("the talk check", {"hook_event_name": "Stop", "cwd": pr_, "last_assistant_message": "Done. See /tmp/x.py", "transcript_path": mgr}, "talk-check"),
        ("the board stop", {"hook_event_name": "Stop", "cwd": pr_, "last_assistant_message": "ok", "transcript_path": mgr}, "board-stop"),
        ("the worker queue", {"hook_event_name": "Stop", "cwd": pr_, "last_assistant_message": "ok", "transcript_path": tr("You are Site_PINR_002. Job: Site_PINR_002.")}, "worker-queue-check"),
        ("the renew hook after a summary", {"transcript_path": tr("You are Site_PINR_002. Job: Site_PINR_002, builds the site.")}, "renew-after-summary"),
    ]
    for label, ev, name in events:
        a = run(pr_, name, ev); b = run(pr_, name, ev, ext="py")
        if name == "renew-after-summary":  # the program finds the talking rules (hooks/talk-block.txt) in the Muster folder, as the plugin's own hook does; the Python stand-in, sitting alone in .muster-checks/, does not
            blk = open(os.path.join(ROOT, "hooks", "talk-block.txt"), encoding="utf-8").read().rstrip()
            t("real program: %s -> %s.sh gives the Python stand-in's answer plus the talking rules" % (label, name), a[0] == b[0] == 0 and a[1].startswith(b[1].rstrip()) and blk in a[1], (a, b))
            continue
        t("real program: %s -> %s.sh answers as the Python stand-in does" % (label, name), a == b, (a, b))
    t("real program: the PINR profile is in force (the choice card is refused by the program)", "Muster rule" in run(pr_, "rules-check", events[0][1])[1])
    # PINR-shaped replies (real ones from a PINR manager chat): the program with the live profile and the Python stand-in must answer alike, block or not, word for word
    pinr_texts = [
        "**ASK \u00b7 coverage now**\n\nOn the live list 280 coins show coverage, average 45%.\n- ***A.*** Keep the order as it stands. *(my pick)*\n- ***B.*** Put the X scan ahead.",
        "**ASK \u00b7 coverage now**\n\nWhich first?\n\n***A.*** Keep the order. *(my pick)* because it is small\n\n***B.*** Put the X scan ahead.",
        "Coverage order: A (bot signs next, as ordered) or B (X scan and callouts first)?",
        "Working: Apps_PINR on ios-build-34.",
        "Working: Look Cards on the Gill Sans badge fix, and Engine on sources piece 1. The Evidence Web names question is waiting for you.",
        "Working: Engine on new-data-keys, waiting for your save.",
        "Noted.", "**YES NEEDED \u00b7 fonts**\n\nType A in its own chat.",
    ]
    for tx in pinr_texts:
        e = {"hook_event_name": "Stop", "cwd": pr_, "last_assistant_message": tx, "transcript_path": mgr}
        for nm in ("rules-check", "board-stop", "talk-check"):
            a = run(pr_, nm + "", e); b = run(pr_, nm, e, ext="py")
            t("real program: PINR reply %r, %s: same answer as the Python stand-in" % (tx[:36], nm), a == b, (a, b))
    # the idle check as an installed copy: the chat's own title decides (the program is told the project, so it is "installed" without sitting in .muster-checks)
    now = int(time.time() * 1000)
    sd = os.path.join(T, "sess", "a", "b"); os.makedirs(sd)
    cid = lambda n: "local_" + ("%d" % n) * 8 + "-1111-1111-1111-" + ("%d" % n) * 12
    pi = project(mr)
    open(os.path.join(pi, "muster", "BOARD.md"), "w").write("### 2026-01-01 | ORDER | Manager_PINR_001 -> Builder Q_PINR_001 | job1\nStatus: open\n")
    open(os.path.join(pi, "muster", "CREW.md"), "w").write("## Running now\n| Name | Model | Effort | Folder | Chat id | Started |\n|---|---|---|---|---|---|\n| Manager_PINR_001 | m | m | f | %s | d |\n| Builder Q_PINR_001 | m | m | f | %s | d |\n\n## Archived\n" % (cid(1), cid(2)))
    for i, ago in ((1, 5), (2, 600)):
        json.dump({"isArchived": False, "lastActivityAt": now - ago * 1000, "postTurnSummary": {}}, open(os.path.join(sd, cid(i) + ".json"), "w"))
    def titled(title, first):
        f = os.path.join(T, "ti%d.jsonl" % len(os.listdir(T)))
        with open(f, "w") as fh:
            fh.write(json.dumps({"type": "user", "message": {"content": first}}) + "\n")
            if title: fh.write(json.dumps({"type": "custom-title", "customTitle": title, "sessionId": "x"}) + "\n")
        return f
    ienv = {"MUSTER_SESSIONS_DIR": os.path.join(T, "sess"), "MUSTER_STATE_DIR": tempfile.mkdtemp(dir=T), "MUSTER_NO_SWEEP": "1"}
    pe = os.path.join(ROOT, "profiles", "pinr.json")
    for label, title in (("a chat titled as a manager gets the idle check", "Manager_PINR_001"), ("a worker's chat is silent", "Builder Q_PINR_001"), ("a chat with no title is silent", None)):
        ev = {"last_assistant_message": "done", "transcript_path": titled(title, "You are Manager_PINR_001")}
        ienv["MUSTER_STATE_DIR"] = tempfile.mkdtemp(dir=T); a = run(pi, "idle-check", ev, env=ienv)
        ienv["MUSTER_STATE_DIR"] = tempfile.mkdtemp(dir=T); b = run(pi, "idle-check", ev, ext="py", env=ienv)
        t("real program: idle check, %s, same as the Python stand-in" % label, a == b, (a, b))
        if title == "Manager_PINR_001": t("real program: ...and it did block (the project was told to the program)", "Builder Q_PINR_001" in a[1], a)
sys.exit(1 if bad else 0)
