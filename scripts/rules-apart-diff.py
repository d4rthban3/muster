#!/usr/bin/env python3
"""The difference run for right-hand part 4 (safety stops and house rules kept apart): a project (PINR) must get the same answers before and after.
Replays every call the rules-check self-test makes (it keeps them when MUSTER_CALLS_OUT names a file) under the project's profile, once with the
older copies of the checks and once with these, and prints every call where the two answers differ. The group label the newer copies add to a
refusal is left out of the comparison. Exit 1 on any difference. Writes only in a temporary folder. Standard library only.
usage: rules-apart-diff.py --calls FILE --before-hooks DIR [--profile profiles/pinr.json] [--before-bin FILE --after-bin FILE]
  DIR holds the older hooks/rules-check.py and hooks/board-stop.py; the two programs are the older and the newer muster-checks."""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LABEL = re.compile(r' \[(?:safety stop|house rule) \\?"[a-z-]+\\?"[^\]]*?\]')


def go(cmd, inp, env, profile, state):
    for f in glob.glob(os.path.join(tempfile.gettempdir(), "tmp*", "*.muster-notes")):  # a note kept by the first run must not reach the second
        try:
            os.remove(f)
        except OSError:
            pass
    e = dict(os.environ, **env, MUSTER_PROFILE=profile, MUSTER_STATE_DIR=state)
    return LABEL.sub("", subprocess.run(cmd, input=inp, capture_output=True, text=True, env=e).stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calls", required=True)
    ap.add_argument("--before-hooks", required=True)
    ap.add_argument("--profile", default=os.path.join(ROOT, "profiles", "pinr.json"))
    ap.add_argument("--before-bin")
    ap.add_argument("--after-bin")
    a = ap.parse_args()
    calls = json.load(open(a.calls))
    py = lambda d, name: [sys.executable, os.path.join(d, "board-stop.py" if name == "board-stop" else "rules-check.py")]
    sets = [("python copies", lambda n: py(a.before_hooks, n), lambda n: py(os.path.join(ROOT, "hooks"), n))]
    if a.before_bin and a.after_bin:
        sets.append(("program", lambda n: [a.before_bin, n], lambda n: [a.after_bin, n]))
    diffs = 0
    for label, before, after in sets:
        same = 0
        for _kind, sub, inp, env in calls:
            name = "board-stop" if os.path.basename(sub).startswith("board-stop") else "rules"
            o1 = go(before(name), inp, env, a.profile, tempfile.mkdtemp())
            o2 = go(after(name), inp, env, a.profile, tempfile.mkdtemp())
            if o1 == o2:
                same += 1
            else:
                diffs += 1
                print("DIFFERENT (%s): %s\n  before: %s\n  after:  %s" % (label, inp[:160], o1[:240], o2[:240]))
        print("%s: %d calls replayed under %s, %d answered the same before and after" % (label, len(calls), os.path.basename(a.profile), same))
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
