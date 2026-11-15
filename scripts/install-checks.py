#!/usr/bin/env python3
"""Install Muster's coded rules into a project that does not load the Muster plugin (for example PINR).

Usage: install-checks.py <project-folder> [--profile <name or file>] [--live <Muster folder>] [--dry-run] [--remove]
A profile (profiles/<name>.json, for example pinr) lets another project's own chat names, report shape, board path and
choice recorder be checked instead of only Muster's; without one, only Muster's own rules apply. --dry-run only says what
would be written and writes nothing.
--live <Muster folder> puts small stand-ins (scripts/live-standin.py) in <project>/.muster-checks/ and <project>/manager/ instead of copies: each one
runs the check of its name straight from that Muster folder every time, so a new Muster version reaches the project with no re-install
(its profile and message form still apply; a missing Muster folder is said plainly, never silently).
Copies hooks/rules-check.py, hooks/board-stop.py, hooks/talk-check.py, scripts/usage.py, scripts/worker-queue-check.py and scripts/idle-check.py into <project>/.muster-checks/,
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
         ("hooks/talk-check.py", "talk-check.py"), ("scripts/usage.py", "usage.py"),
         ("scripts/worker-queue-check.py", "worker-queue-check.py"), ("scripts/idle-check.py", "idle-check.py")]
MARK = ".muster-checks/"


def cmd(name):
    """Item 94: a builder's linked worktree runs the MAIN folder's live copy of the check, never an older copy carried in the worktree; with no main folder
    (not a git folder, or git too old to say) it runs the project's own copy as before."""
    return ("sh -c 'r=$(git -C \"$CLAUDE_PROJECT_DIR\" rev-parse --path-format=absolute --git-common-dir 2>/dev/null); m=${r%/.git}; "
            "[ -f \"$m/.muster-checks/NAME\" ] || m=$CLAUDE_PROJECT_DIR; exec python3 \"$m/.muster-checks/NAME\"'").replace("NAME", name)


def install_recorder(proj, dest, prof, live=False):
    """A profile may name its own choice recorder (item 86): copy it over the project's, keeping the old one once."""
    src, to = prof.get("recorder_script"), prof.get("recorder_dest")
    if not src or not to:
        return
    target = os.path.join(proj, to)
    keep = os.path.join(dest, "recorder.before")
    if os.path.isfile(target) and not os.path.exists(keep) and not any(m in open(target, encoding="utf-8").read() for m in ("Muster's decide.py for PINR's layout", "MUSTER-LIVE-STANDIN")):
        shutil.copyfile(target, keep)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(os.path.join(HERE, "live-standin.py") if live else os.path.join(ROOT, src), target)


def restore_recorder(proj, dest):
    """Put back the project's own recorder that install_recorder replaced (nothing to do if it never did)."""
    keep, pfile = os.path.join(dest, "recorder.before"), os.path.join(dest, "profile.json")
    try:
        to = json.load(open(pfile, encoding="utf-8")).get("recorder_dest")
    except (OSError, ValueError):
        return
    if to and os.path.isfile(keep):
        shutil.copyfile(keep, os.path.join(proj, to))
        os.remove(keep)


def main():
    argv = sys.argv[1:]
    profile = None
    if "--profile" in argv:
        i = argv.index("--profile")
        profile = argv[i + 1] if i + 1 < len(argv) else ""
        argv = argv[:i] + argv[i + 2:]
    live = None
    if "--live" in argv:
        i = argv.index("--live")
        live = os.path.abspath(argv[i + 1]) if i + 1 < len(argv) else ""
        argv = argv[:i] + argv[i + 2:]
        need = [src for src, _ in FILES] + ["scripts/live-standin.py"]
        if not live or not os.path.isdir(live) or any(not os.path.isfile(os.path.join(live, n)) for n in need):
            print("STOP: --live needs the Muster folder (one that holds hooks/, scripts/ and the checks); %r is not one" % live)
            return 1
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
        if live and not remove:
            print("DRY RUN: would put small stand-ins for %s in %s that run the live checks from %s, and add the Stop and PreToolUse hooks to %s. Nothing was written."
                  % (", ".join(n for _, n in FILES), dest, live, sfile))
            return 0
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
        restore_recorder(proj, os.path.join(proj, ".muster-checks"))
        shutil.rmtree(os.path.join(proj, ".muster-checks"), ignore_errors=True)
        if not hooks:
            settings.pop("hooks", None)
    else:
        dest = os.path.join(proj, ".muster-checks")
        os.makedirs(dest, exist_ok=True)
        for src, name in FILES:
            shutil.copyfile(os.path.join(HERE, "live-standin.py") if live else os.path.join(ROOT, src), os.path.join(dest, name))
        livefile = os.path.join(dest, "live.json")
        if live:
            files = dict((n, src) for src, n in FILES)
            prof_rel = None
            pdata = json.load(open(pfile, encoding="utf-8")) if pfile else {}
            if pfile and os.path.isfile(os.path.join(live, "profiles", os.path.basename(pfile))):
                prof_rel = "profiles/" + os.path.basename(pfile)
            recorders = []
            if pdata.get("recorder_script") and pdata.get("recorder_dest"):
                files[os.path.basename(pdata["recorder_dest"])] = pdata["recorder_script"]
                recorders.append(os.path.basename(pdata["recorder_dest"]))
            with open(livefile, "w", encoding="utf-8") as fh:
                json.dump({"muster": live, "profile": prof_rel, "files": files, "recorders": recorders}, fh, indent=2)
                fh.write("\n")
        elif os.path.exists(livefile):
            os.remove(livefile)
        if pfile:
            shutil.copyfile(pfile, os.path.join(dest, "profile.json"))
            install_recorder(proj, dest, json.load(open(pfile, encoding="utf-8")), live=bool(live))
        elif os.path.exists(os.path.join(dest, "profile.json")):
            restore_recorder(proj, dest)
            os.remove(os.path.join(dest, "profile.json"))
        hooks.setdefault("Stop", []).append({"hooks": [{"type": "command", "command": cmd(n)} for n in ("board-stop.py", "talk-check.py", "rules-check.py", "worker-queue-check.py", "idle-check.py")]})
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
