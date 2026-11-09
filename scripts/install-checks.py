#!/usr/bin/env python3
"""Install Muster's coded rules into a project that does not load the Muster plugin (for example PINR).

Usage: install-checks.py <project-folder> [--profile <name or file>] [--dry-run] [--remove]
A profile (profiles/<name>.json, for example pinr) lets another project's own chat names, report shape, board path and
choice recorder be checked instead of only Muster's; without one, only Muster's own rules apply. --dry-run only says what
would be written and writes nothing.
Copies hooks/rules-check.py, hooks/board-stop.py, hooks/talk-check.py and scripts/usage.py into <project>/.muster-checks/,
and adds the hooks to <project>/.claude/settings.json (existing settings and other hooks are kept). Run it again after a
Muster update to refresh the copies; --remove takes everything it added away. The checks act only in a chat whose first
message names a crew role (Manager_<project>_001, Builder A_..., agents/<role>.md), so the owner's own chats are never touched.
Do not install it in a project that also loads the plugin: the checks would run twice. Standard library only.
"""
import json
import os
import shutil
import sys

for _s in (sys.stdout, sys.stderr):  # a project name with accents must print on any computer, whatever its console encoding
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FILES = [("hooks/rules-check.py", "rules-check.py"), ("hooks/board-stop.py", "board-stop.py"),
         ("hooks/talk-check.py", "talk-check.py"), ("scripts/usage.py", "usage.py")]
MARK = ".muster-checks/"


def cmd(name):
    return 'python3 "$CLAUDE_PROJECT_DIR/.muster-checks/%s"' % name


def main():
    argv = sys.argv[1:]
    profile = None
    if "--profile" in argv:
        i = argv.index("--profile")
        profile = argv[i + 1] if i + 1 < len(argv) else ""
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith("--")]
    remove = "--remove" in argv
    dry = "--dry-run" in argv
    pfile = None
    if profile is not None:
        pfile = profile if os.path.isfile(profile) else os.path.join(ROOT, "profiles", profile + ".json")
        if not os.path.isfile(pfile):
            print("STOP: no profile %r (looked for %s)" % (profile, pfile))
            return 1
        try:
            json.load(open(pfile, encoding="utf-8"))
        except ValueError:
            print("STOP: %s is not valid JSON" % pfile)
            return 1
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(__doc__.split("\n\n")[0])
        return 2
    proj = os.path.abspath(args[0])
    sfile = os.path.join(proj, ".claude", "settings.json")
    settings = {}
    if os.path.exists(sfile):
        try:
            settings = json.load(open(sfile, encoding="utf-8"))
        except ValueError:
            print("STOP: %s is not valid JSON; fix it by hand first" % sfile)
            return 1
    if dry:
        dest = os.path.join(os.path.abspath(args[0]), ".muster-checks")
        if remove:
            print("DRY RUN: would remove %s and the hooks pointing at it from %s. Nothing was written." % (dest, sfile))
        else:
            print("DRY RUN: would copy %s into %s%s and add the Stop and PreToolUse hooks to %s. Nothing was written."
                  % (", ".join(n for _, n in FILES), dest, (" with the profile " + os.path.basename(pfile)) if pfile else "", sfile))
        return 0
    hooks = settings.setdefault("hooks", {})
    for ev in list(hooks):
        hooks[ev] = [g for g in hooks[ev] if not any(MARK in h.get("command", "") for h in g.get("hooks", []))]
        if not hooks[ev]:
            del hooks[ev]
    if remove:
        shutil.rmtree(os.path.join(proj, ".muster-checks"), ignore_errors=True)
        if not hooks:
            settings.pop("hooks", None)
    else:
        dest = os.path.join(proj, ".muster-checks")
        os.makedirs(dest, exist_ok=True)
        for src, name in FILES:
            shutil.copyfile(os.path.join(ROOT, src), os.path.join(dest, name))
        if pfile:
            shutil.copyfile(pfile, os.path.join(dest, "profile.json"))
        elif os.path.exists(os.path.join(dest, "profile.json")):
            os.remove(os.path.join(dest, "profile.json"))
        hooks.setdefault("Stop", []).append({"hooks": [{"type": "command", "command": cmd(n)} for n in ("board-stop.py", "talk-check.py", "rules-check.py")]})
        hooks.setdefault("PreToolUse", []).append({"matcher": "SendMessage|Write|Edit|NotebookEdit|Bash",
                                                   "hooks": [{"type": "command", "command": cmd("rules-check.py")}]})
    os.makedirs(os.path.dirname(sfile), exist_ok=True)
    with open(sfile, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2)
        fh.write("\n")
    print("%s the coded rules in %s" % ("Removed" if remove else "Installed", proj))
    return 0


if __name__ == "__main__":
    sys.exit(main())
