#!/usr/bin/env python3
# MUSTER-LIVE-STANDIN: a small stand-in installed by install-checks.py --live <Muster folder> (item 90).
"""Runs the live check of this name straight from the Muster folder, so a new Muster version reaches this project with no re-install.

It reads live.json beside it (the Muster folder, and which file of that folder stands behind this name), reads that file's
source from the Muster folder every time, and runs it as if it sat here: the profile beside it, the project's own settings and
the message form all apply exactly as for an installed copy. If the Muster folder or the file is missing it says so
plainly (a hook shows the message and lets the turn go on; a recorder stops with the message); it never fails silently.
Standard library only. Written by install-checks.py; do not edit by hand."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ME = os.path.abspath(__file__)
NAME = os.path.basename(ME)


def find_live_json():
    for cand in (os.path.join(HERE, "live.json"), os.path.join(os.path.dirname(HERE), ".muster-checks", "live.json")):
        if os.path.isfile(cand):
            return cand
    return None


def problem(text, recorder):
    if recorder:
        sys.stderr.write("Muster live check: " + text + "\n")
        sys.exit(1)
    sys.stdout.write(json.dumps({"systemMessage": "Muster live check (%s) is not running: %s" % (NAME, text)}) + "\n")
    sys.exit(0)


def main():
    lj = find_live_json()
    recorder = NAME in ("decide.py",)
    if not lj:
        problem("live.json is missing beside %s. Run install-checks.py --live <the Muster folder> again, or without --live for plain copies." % NAME, recorder)
    try:
        cfg = json.load(open(lj, encoding="utf-8"))
    except (OSError, ValueError) as err:
        problem("cannot read %s (%s). Run install-checks.py --live <the Muster folder> again." % (lj, err), recorder)
    recorder = NAME in cfg.get("recorders", [])
    folder = cfg.get("muster", "")
    rel = (cfg.get("files") or {}).get(NAME)
    if not folder or not os.path.isdir(folder):
        problem("the Muster folder %s is missing, so this check cannot run. Put the folder back there, or run install-checks.py without --live to install plain copies." % (folder or "(none named)"), recorder)
    if not rel or not os.path.isfile(os.path.join(folder, rel)):
        problem("%s has no %s (this stand-in runs it from there). Update the Muster folder to a version that has it." % (folder, rel or NAME), recorder)
    prof = cfg.get("profile")
    if prof and os.path.isfile(os.path.join(folder, prof)):
        os.environ.setdefault("MUSTER_PROFILE", os.path.join(folder, prof))  # the live profile, unless the caller named another
    try:
        src = open(os.path.join(folder, rel), encoding="utf-8").read()
    except OSError as err:
        problem("cannot read %s (%s)." % (os.path.join(folder, rel), err), recorder)
    code = compile(src, ME, "exec")  # named as this file, so the check sees itself installed here
    exec(code, {"__name__": "__main__", "__file__": ME, "__builtins__": __builtins__})


main()
