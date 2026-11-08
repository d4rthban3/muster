#!/usr/bin/env python3
"""Set up Muster for Cursor (the full crew), with no Claude Code involved. UNTESTED in Cursor itself.

Usage:  python3 cursor/setup.py <project-folder> --name "My Project" [--vision "..."] [--builders 1] [--no-designer]
Does, never overwriting an existing file:
  1. makes the folder a git repository if it is not one, with one empty first commit (copies need a history);
  2. keeps the crew's files out of history (.git/info/exclude): muster/, the Muster rules in .cursor/rules, the hook file;
  3. writes muster/ (owner's list, decisions, board, crew, report shape, rules pages, handovers) from Muster's templates,
     and muster/tools/ (the scripts an agent runs as plain commands);
  4. writes the Muster rules to .cursor/rules/ (one always-on core + one rule per role) in the project and in each copy;
  5. makes one git worktree (copy) per worker beside the project, on its own branch;
  6. writes .cursor/hooks.json (the manager's Stop check) if there is none;
  7. writes a starting note per agent in muster/start-notes/ and prints the exact steps for the owner.
Standard library and git only.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
GIT = ["git", "-c", "user.name=Muster", "-c", "user.email=muster@localhost"]


def git(cwd, *args, check=True):
    return subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True, check=check)


def copy_new(src, dst):
    if os.path.exists(dst):
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    return True


def render(path, main):
    with open(path, encoding="utf-8") as fh:
        return fh.read().replace("{{MAIN}}", main.replace("\\", "/"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--name", required=True)
    ap.add_argument("--vision", default="")
    ap.add_argument("--builders", type=int, default=1)
    ap.add_argument("--no-designer", action="store_true")
    ap.add_argument("--join", action="store_true", help="second computer: join a project that already has muster/ (writes nothing in it)")
    ap.add_argument("--computer", default="", help="with --join: this computer's name, e.g. laptop2")
    ap.add_argument("--other", default="", help="with --join: the host computer's name, e.g. desk1")
    ap.add_argument("--workspace", default="", help="with --join: this computer's workspace folder (default: <project's parent>/<computer> Workspace)")
    ap.add_argument("--other-workspace", default="", help="with --join: the host's workspace folder (default: <project's parent>/<other> Workspace)")
    ap.add_argument("--git-name", default="", help="with --join: git name for this computer's commits (default: the computer's name)")
    ap.add_argument("--copies", choices=["none", "clone"], default="none", help="with --join: clone = a local clone per builder/designer instead of working in the shared folder")
    ap.add_argument("--copies-dir", default="", help="with --join --copies clone: where the clones go (default: ~/MusterCopies/<project>)")
    ap.add_argument("--board", default="", help="with --join: the project's board file (default: <project>/muster/BOARD.md)")
    ap.add_argument("--rules", action="append", default=[], help="with --join: a rules file the second computer must read (repeatable; default: <project>/muster/CLAUDE.md)")
    ap.add_argument("--protocol", default="", help="with --join: the protocol page (default: <project>/muster/PROTOCOL.md)")
    ap.add_argument("--builders-log", default="", help="with --join: the builders' change log (default: <project>/muster/BUILDERS-LOG.md)")
    ap.add_argument("--dry-run", action="store_true", help="with --join: say what would be read and written; write nothing at all")
    a = ap.parse_args()
    if a.join:
        return join(a)
    if not re.fullmatch(r"[^/\\:*?\"<>|.][^/\\:*?\"<>|]{0,39}", a.name):
        sys.exit("setup: the project name may not hold / \\ : * ? \" < > | , start with a dot, or pass 40 characters")
    main_dir = os.path.abspath(a.folder)
    os.makedirs(main_dir, exist_ok=True)
    if git(main_dir, "rev-parse", "--git-dir", check=False).returncode != 0:
        git(main_dir, "init", "-q", "-b", "main")
    if git(main_dir, "rev-parse", "HEAD", check=False).returncode != 0:
        subprocess.run(GIT + ["commit", "-q", "--allow-empty", "-m", "Muster: first version"], cwd=main_dir, check=True)
    gitdir = git(main_dir, "rev-parse", "--git-common-dir").stdout.strip()
    gitdir = gitdir if os.path.isabs(gitdir) else os.path.join(main_dir, gitdir)
    exclude = os.path.join(gitdir, "info", "exclude")
    os.makedirs(os.path.dirname(exclude), exist_ok=True)
    have = open(exclude, encoding="utf-8").read() if os.path.exists(exclude) else ""
    add = [l for l in ("/muster/", "/.muster-paused", "/.cursor/rules/muster-*.mdc", "/.cursor/hooks.json") if l not in have.split("\n")]
    if add:
        with open(exclude, "a", encoding="utf-8") as fh:
            fh.write(("" if have.endswith("\n") or not have else "\n") + "\n".join(add) + "\n")

    # muster/ from the templates
    T = os.path.join(PLUGIN, "templates")
    M = os.path.join(main_dir, "muster")
    for n in ("CREW.md", "DECISIONS-LOG.md", "BOARD.md", "OWNERS-LIST.md", "REPORT.md", "START-NOTE.md", "RULES-PAGE.md", "LOOK-BOOK.md", "CLAUDE.md", "PROTOCOL.md", "BUILDERS-LOG.md"):
        copy_new(os.path.join(T, n), os.path.join(M, n))
    for d in ("rules", "handovers", "start-notes", "tools"):
        os.makedirs(os.path.join(M, d), exist_ok=True)
    for d in ("rules", "handovers"):
        open(os.path.join(M, d, ".gitkeep"), "a").close()
    open(os.path.join(M, "BOARD-ARCHIVE.md"), "a").close()
    # the tools an agent runs as plain commands (the plugin's own scripts, unchanged)
    for src, dst in (("skills/board-digest/scripts/board_digest.py", "board_digest.py"), ("skills/board-digest/scripts/board_archive.py", "board_archive.py"), ("scripts/crew-plan.py", "crew-plan.py"), ("scripts/record-choice.py", "record-choice.py"),
                     ("scripts/decide.py", "decide.py"), ("scripts/check-report.py", "check-report.py"),
                     ("hooks/board-stop.py", "board-stop.py"), ("cursor/stop.py", "cursor-stop.py")):
        s = os.path.join(PLUGIN, src)
        if os.path.exists(s):
            shutil.copyfile(s, os.path.join(M, "tools", dst))
    log = os.path.join(M, "DECISIONS-LOG.md")
    txt = open(log, encoding="utf-8").read()
    if "## Standing decisions" in txt:  # the fresh template: replace its made-up entries with the real ones
        import datetime
        today = datetime.date.today().isoformat()
        entry = ("### D-001 · %s · What the crew asks the owner first\nDecision: Spending money, keys or passwords and deleting anything need the owner's yes.\n"
                 "Why: chosen at setup.\nSupersedes: none\nAffects: all\n" % today)
        if a.vision:
            entry += "\n### D-002 · %s · What we are building\nDecision: %s\nWhy: chosen at setup.\nSupersedes: none\nAffects: all\n" % (today, a.vision)
        with open(log, "w", encoding="utf-8") as fh:
            fh.write(txt.split("## Standing decisions")[0] + "## Standing decisions\n" + entry)
    if a.vision:
        lst = os.path.join(M, "OWNERS-LIST.md")
        t = open(lst, encoding="utf-8").read()
        if "## Open" in t and '1. "' + a.vision not in t:
            t = t.replace("## Open", '## Open\n1. "%s"\n   Kind: (Manager sorts it)\n   Did: (nothing yet)\n   Stands: with the manager\n   Checked: (not done yet)\n' % a.vision, 1)
            open(lst, "w", encoding="utf-8").write(t)

    # the crew
    P = a.name
    crew = [("Manager", "manager", main_dir)]
    for i in range(a.builders):
        L = chr(ord("A") + i)
        crew.append(("Builder %s" % L, "builder", None))
    if not a.no_designer:
        crew.append(("Designer", "designer", None))
    crew.append(("Inspector", "inspector", None))
    copies = os.path.join(os.path.dirname(main_dir), os.path.basename(main_dir) + "_copies")
    rows = []
    for role_name, role, folder in crew:
        chat = "%s_%s_001" % (role_name, P)
        slug = re.sub(r"[^a-z0-9]+", "-", ("%s-001" % role_name).lower()).strip("-")
        if folder is None and role != "inspector":
            folder = os.path.join(copies, slug)
            if not os.path.isdir(folder):
                os.makedirs(copies, exist_ok=True)
                git(main_dir, "worktree", "add", "-q", folder, "-b", "muster/" + slug)
        elif folder is None:
            folder = main_dir  # the inspector reads and runs checks; it never writes project files
        rows.append((chat, role, folder))
    rules_src = os.path.join(HERE, "rules")
    for folder in {r[2] for r in rows}:
        for n in sorted(os.listdir(rules_src)):
            dst = os.path.join(folder, ".cursor", "rules", n)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(render(os.path.join(rules_src, n), main_dir))
    hooks = os.path.join(main_dir, ".cursor", "hooks.json")
    wrote_hook = False
    if not os.path.exists(hooks):
        with open(hooks, "w", encoding="utf-8") as fh:
            fh.write('{\n  "version": 1,\n  "hooks": {\n    "stop": [ { "command": "python3 muster/tools/cursor-stop.py", "loop_limit": 1 } ]\n  }\n}\n')
        wrote_hook = True
    crewmd = os.path.join(M, "CREW.md")
    if "## Cursor agents" not in open(crewmd, encoding="utf-8").read():
        with open(crewmd, "a", encoding="utf-8") as fh:
            fh.write("\n## Cursor agents (written by cursor/setup.py)\n" + "".join("- %s | %s | %s\n" % r for r in rows))
    steps = []
    for chat, role, folder in rows:
        note = os.path.join(M, "start-notes", chat + ".md")
        body = ("You are %s, the %s of the Muster crew for the project \"%s\" in Cursor.\n"
                "Your folder: %s\nThe crew's shared files (owner's list, board, decisions, rules pages) live in the MAIN folder %s under muster/ : read and write them there.\n"
                "Rules: the Muster core rule is always on; also open @muster-%s. Full rules: %s/muster/CLAUDE.md.\n"
                "Start by running: python3 %s/muster/tools/board_digest.py \"%s\" and read what it prints. Your rules page: %s/muster/rules/ (the manager writes it).\n"
                "Your end-of-turn reply is a short card for the owner (title, two or three bullets); reports go on the board.\n"
                % (chat, role, P, folder, main_dir, role, main_dir, main_dir, chat, main_dir))
        with open(note, "w", encoding="utf-8") as fh:
            fh.write(body)
        steps.append((chat, folder, note))
    print("Muster for Cursor is set up in %s" % main_dir)
    print("Hook file written: %s" % ("yes (.cursor/hooks.json)" if wrote_hook else "no, one already exists; add the stop hook from cursor/README.md by hand"))
    print("\nFor each agent below: open that folder in Cursor, start a new Agent chat, open the note file and paste its whole contents as your first message.")
    for chat, folder, note in steps:
        print("  %-34s folder: %s\n  %-34s note:   %s" % (chat, folder, "", note))
    print("\nStart with the Manager. It tells you what it needs from you; the others work from the board.")
    return 0


def join(a):
    """Second computer: join a project that already has a board. Writes NOTHING in the host's files (not muster/, not .cursor,
    not .git): everything goes into this computer's own workspace folder and its own local clones. --dry-run writes nothing at all."""
    if not (a.computer and a.other):
        sys.exit("setup: --join needs --computer <this computer's name> and --other <the host computer's name>")
    main_dir = os.path.abspath(a.folder)
    board = os.path.abspath(a.board or os.path.join(main_dir, "muster", "BOARD.md"))
    if not os.path.isfile(board):
        sys.exit("setup: no board at %s. Join works on a project the host already set up (run setup without --join there first), "
                 "or pass the board's path with --board." % board)
    parent = os.path.dirname(main_dir)
    ws = os.path.abspath(a.workspace or os.path.join(parent, a.computer + " Workspace"))
    ows = os.path.abspath(a.other_workspace or os.path.join(parent, a.other + " Workspace"))
    if os.path.normcase(ws) == os.path.normcase(ows):
        sys.exit("setup: this computer's workspace and the other's are the same folder (%s)" % ws)
    gname = a.git_name or a.computer
    rules = [os.path.abspath(r) for r in (a.rules or [os.path.join(main_dir, "muster", "CLAUDE.md")])]
    protocol = os.path.abspath(a.protocol or os.path.join(main_dir, "muster", "PROTOCOL.md"))
    blog = os.path.abspath(a.builders_log or os.path.join(main_dir, "muster", "BUILDERS-LOG.md"))
    fwd = lambda x: x.replace("\\", "/")
    sub = {"{{COMPUTER}}": a.computer, "{{OTHER}}": a.other, "{{MAIN}}": fwd(main_dir), "{{WORKSPACE}}": fwd(ws),
           "{{OTHER_WORKSPACE}}": fwd(ows), "{{GIT_NAME}}": gname, "{{PROJECT}}": a.name, "{{BOARD}}": fwd(board),
           "{{RULES}}": "\n".join("   - " + fwd(r) for r in rules), "{{PROTOCOL}}": fwd(protocol), "{{BUILDERS_LOG}}": fwd(blog)}

    def fill(t):
        for k, v in sub.items():
            t = t.replace(k, v)
        return t

    made, would = [], []

    def put(path, text, exe=False):
        """Write a new file (never over an existing one); with --dry-run only say so."""
        if os.path.exists(path):
            return False
        would.append(path)
        if not a.dry_run:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8", newline="\n").write(text)
            if exe:
                os.chmod(path, 0o755)
        return True

    T = os.path.join(PLUGIN, "templates")
    if put(os.path.join(ws, "CHANGES.md"), open(os.path.join(T, "CHANGES.md"), encoding="utf-8").read().replace("<Computer name>", a.computer)):
        made.append("CHANGES.md")
    start = os.path.join(ws, "START-HERE.md")
    if put(start, fill(open(os.path.join(T, "COMPUTER2-START.md"), encoding="utf-8").read())):
        made.append("START-HERE.md")
    if put(os.path.join(ws, "git-as.sh"),
           '#!/bin/sh\n# Runs git as %s, for this computer\'s own commits; the project\'s own git settings are never changed.\n'
           'exec git -c "user.name=%s" -c "user.email=%s@localhost" "$@"\n' % (gname, gname, gname), exe=True):
        made.append("git-as.sh")
    bd = os.path.join(PLUGIN, "skills", "board-digest", "scripts", "board_digest.py")
    if os.path.exists(bd) and put(os.path.join(ws, "tools", "board_digest.py"), open(bd, encoding="utf-8").read()):
        made.append("tools/board_digest.py")
    core = open(os.path.join(HERE, "rules", "muster-core.mdc"), encoding="utf-8").read()
    two = open(os.path.join(HERE, "join", "two-computers.md"), encoding="utf-8").read()
    folders = [ws]
    clones = []
    if a.copies == "clone":
        cdir = os.path.abspath(a.copies_dir or os.path.join(os.path.expanduser("~"), "MusterCopies", a.name))
        for role_name in ["Builder A"] + ([] if a.no_designer else ["Designer"]):
            slug = re.sub(r"[^a-z0-9]+", "-", ("%s-%s" % (role_name, a.computer)).lower()).strip("-")
            dest = os.path.join(cdir, slug)
            if not os.path.isdir(dest):
                would.append(dest + " (a local clone of " + main_dir + ")")
                if not a.dry_run:
                    os.makedirs(cdir, exist_ok=True)
                    git(cdir, "clone", "-q", main_dir, dest)
                    git(dest, "config", "user.name", gname)
                    git(dest, "config", "user.email", gname + "@localhost")
                    git(dest, "checkout", "-q", "-b", "%s/%s" % (gname, slug))
            clones.append((role_name, dest))
            folders.append(dest)
    for folder in folders:
        rd = os.path.join(folder, ".cursor", "rules")
        if put(os.path.join(rd, "muster-%s-core.mdc" % a.computer), fill(core) + fill(two)):
            made.append(os.path.relpath(os.path.join(rd, "muster-%s-core.mdc" % a.computer), ws) if folder == ws else os.path.join(rd, "muster-%s-core.mdc" % a.computer))
        for role in ("builder", "designer", "inspector"):
            if role == "designer" and a.no_designer:
                continue
            put(os.path.join(rd, "muster-%s-%s.mdc" % (role, a.computer)), fill(open(os.path.join(HERE, "rules", "muster-%s.mdc" % role), encoding="utf-8").read()))
    # a clone is this computer's own git folder: keep the rules out of its history (one added line, only if missing)
    for _, dest in clones:
        exc = os.path.join(dest, ".git", "info", "exclude")
        line = "/.cursor/rules/muster-*-%s*.mdc" % a.computer
        if os.path.isdir(os.path.join(dest, ".git")):
            have = open(exc, encoding="utf-8").read() if os.path.exists(exc) else ""
            if line not in have.split("\n") and not a.dry_run:
                with open(exc, "a", encoding="utf-8") as fh:
                    fh.write(("" if have.endswith("\n") or not have else "\n") + line + "\n")
    if a.dry_run:
        print("DRY RUN: %s would join %s as the second computer. Nothing was written." % (a.computer, a.name))
        nf = lambda x: "" if os.path.exists(x) else " (not there yet)"
        print("Would read (never write): board %s, protocol %s%s, builders log %s%s" % (board, protocol, nf(protocol), blog, nf(blog)))
        for r in rules:
            print("Would read (never write): rules %s" % r)
        print("Would write only in this computer's own places (%d):" % len(would))
        for w in would:
            print("  " + w)
        print("Would write nothing inside %s or in %s ." % (main_dir, ows))
        return 0
    print("%s joined %s as the second computer." % (a.computer, a.name))
    print("Written in your workspace %s: %s" % (ws, ", ".join(made) or "nothing new (all existed)"))
    print("Nothing was written in %s or in %s ." % (main_dir, ows))
    print("\nFor each AI chat or agent you open on this computer: open its folder in Cursor, start a new Agent chat, open %s and paste its whole contents as your first message." % start)
    print("  Your workspace (rules for the agent that works from the shared files): %s" % ws)
    for role_name, dest in clones:
        print("  %-10s own local clone (branch %s/...): %s" % (role_name, gname, dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
