#!/usr/bin/env python3
"""Bring a project's copied crew files up to this Muster version.

Usage: muster-update.py <project-folder> [--apply]
Without --apply it only prints what it would do. With --apply it:
  * replaces the project's copies of the rule files (muster/CLAUDE.md, REPORT.md, START-NOTE.md, RULES-PAGE.md) with
    this version's templates, first moving each old copy to muster/superseded/<name>.<old version>.md;
  * never touches the project's own records (OWNERS-LIST.md, DECISIONS-LOG.md, BOARD.md, CREW.md, LOOK-BOOK.md,
    rules/, handovers/, setup-choices.json, anything else);
  * copies a template the project does not have yet (for example LOOK-BOOK.md) when it is new;
  * writes muster/.muster-version;
  * prints one note per worker the release manifests say is affected.
Release manifests are .claude-plugin/releases/<version>.json. Only the standard library is used; no network.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, ".."))
RULE_FILES = ["CLAUDE.md", "REPORT.md", "START-NOTE.md", "RULES-PAGE.md", "PROTOCOL.md"]
NEW_IF_MISSING = ["LOOK-BOOK.md", "BUILDERS-LOG.md"]


def vkey(v):
    return tuple(int(x) for x in v.split(".") if x.isdigit())


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def main():
    args = [a for a in sys.argv[1:] if a != "--apply"]
    apply = "--apply" in sys.argv
    if len(args) != 1 or not os.path.isdir(os.path.join(args[0], "muster")):
        print("usage: muster-update.py <project-folder that holds muster/> [--apply]")
        return 2
    project = os.path.abspath(args[0])
    crew = os.path.join(project, "muster")
    new_version = json.loads(read(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")))["version"]
    old_version = (read(os.path.join(crew, ".muster-version")) or "0.0.0").strip()
    print("Project at Muster %s; this Muster is %s%s" % (old_version, new_version, "" if apply else " (dry run, nothing changed)"))
    if vkey(old_version) >= vkey(new_version) and old_version != "0.0.0":
        print("Already up to date.")
        return 0

    todo = []
    for name in RULE_FILES:
        new = read(os.path.join(PLUGIN, "templates", name))
        old = read(os.path.join(crew, name))
        if new is None:
            continue
        if old is None:
            todo.append(("add", name))
        elif old != new:
            todo.append(("replace", name))
    for name in NEW_IF_MISSING:
        if read(os.path.join(crew, name)) is None and read(os.path.join(PLUGIN, "templates", name)) is not None:
            todo.append(("add", name))
    for kind, name in todo:
        print("  %s muster/%s%s" % (kind, name, " (old copy goes to muster/superseded/)" if kind == "replace" else ""))
    if not todo:
        print("  no rule files differ")

    roles, records = set(), False
    rdir = os.path.join(PLUGIN, ".claude-plugin", "releases")
    notes = []
    for f in sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []:
        if not f.endswith(".json"):
            continue
        m = json.loads(read(os.path.join(rdir, f)))
        if vkey(old_version) < vkey(m["version"]) <= vkey(new_version):
            roles.update(m.get("affected_roles", []))
            records = records or bool(m.get("records_change"))
            notes.append("%s: %s" % (m["version"], m.get("note", "")))

    if apply:
        sup = os.path.join(crew, "superseded")
        for kind, name in todo:
            src = os.path.join(PLUGIN, "templates", name)
            dst = os.path.join(crew, name)
            if kind == "replace":
                os.makedirs(sup, exist_ok=True)
                stem, ext = os.path.splitext(name)
                shutil.copyfile(dst, os.path.join(sup, "%s.%s%s" % (stem, old_version, ext)))
            shutil.copyfile(src, dst)
        with open(os.path.join(crew, ".muster-version"), "w", encoding="utf-8") as fh:
            fh.write(new_version + "\n")
        print("Updated to %s. Your records were not touched." % new_version)

    for n in notes:
        print("Release " + n)
    if records:
        print("This update changes what a project's records should say: ask the manager to review them.")
    for role in sorted(roles):
        print("Note for %s: read the new muster/CLAUDE.md and re-read your rules page; see CHANGELOG.md for what changed." % role)
    if not roles:
        print("No worker is named as affected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
