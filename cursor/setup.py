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
    a = ap.parse_args()
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
    for n in ("CREW.md", "DECISIONS-LOG.md", "BOARD.md", "OWNERS-LIST.md", "REPORT.md", "START-NOTE.md", "RULES-PAGE.md", "LOOK-BOOK.md", "CLAUDE.md"):
        copy_new(os.path.join(T, n), os.path.join(M, n))
    for d in ("rules", "handovers", "start-notes", "tools"):
        os.makedirs(os.path.join(M, d), exist_ok=True)
    for d in ("rules", "handovers"):
        open(os.path.join(M, d, ".gitkeep"), "a").close()
    open(os.path.join(M, "BOARD-ARCHIVE.md"), "a").close()
    # the tools an agent runs as plain commands (the plugin's own scripts, unchanged)
    for src, dst in (("skills/board-digest/scripts/board_digest.py", "board_digest.py"), ("scripts/record-choice.py", "record-choice.py"),
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
    print("\nFor each agent below: open that folder in Cursor, start a new Agent chat, paste the starting note's contents as your first message.")
    for chat, folder, note in steps:
        print("  %-34s folder: %s\n  %-34s note:   %s" % (chat, folder, "", note))
    print("\nStart with the Manager. It tells you what it needs from you; the others work from the board.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
