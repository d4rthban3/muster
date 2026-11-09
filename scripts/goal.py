#!/usr/bin/env python3
"""The weekly goal (owner's list item 35): one goal in his words, when it is done, the set list of work for it, and what is parked.
  goal.py set --words "<his exact words>" --done "<when it is done>" --list job-a,job-b [--parked "name one,name two"] [--folder DIR]
  goal.py show  [--folder DIR]      print the goal (or say none is set)
  goal.py check <job-code> [--folder DIR]   exit 0 if the job is on the set list or no goal is set; exit 1 and print the reminder if not
  goal.py clear [--folder DIR]      remove the goal (he can always change or drop it)
The goal lives in muster/GOAL.md of the main folder; the manager writes it. With no goal set nothing is enforced, and a goal never locks:
setting it again changes it. The coded message check (hooks and the ready-made program) refuses an ORDER whose job is not on the set list."""
import datetime
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def path(folder):
    return os.path.join(folder, "muster", "GOAL.md")


def parse(text):
    words = re.search(r'^Goal \(his words\):\s*"(.*)"\s*$', text, re.M)
    done = re.search(r"^Done when:\s*(.*)$", text, re.M)
    def block(head):
        m = re.search(r"^%s.*?:\s*\n((?:- .*\n?)*)" % re.escape(head), text, re.M)
        return [l[2:].strip() for l in (m.group(1).splitlines() if m else []) if l.startswith("- ") and l[2:].strip()]
    return {"words": words.group(1) if words else "", "done": done.group(1).strip() if done else "",
            "list": block("Set list"), "parked": block("Parked")}


def reminder(g):
    return ('The owner\'s goal for the team is: "%s" (done when: %s). This is not on its set list. '
            "He can change the goal any time: ask him, then run scripts/goal.py set." % (g["words"], g["done"] or "not said"))


def main():
    a = sys.argv[1:]
    folder = "."
    if "--folder" in a:
        i = a.index("--folder"); folder = a[i + 1]; a = a[:i] + a[i + 2:]
    opts = {}
    for k in ("--words", "--done", "--list", "--parked"):
        if k in a:
            i = a.index(k); opts[k] = a[i + 1]; a = a[:i] + a[i + 2:]
    cmd = a[0] if a else ""
    p = path(folder)
    if cmd == "set":
        if not opts.get("--words") or not opts.get("--list"):
            print("set needs --words (his exact words) and --list (the job codes)"); return 2
        jobs = [j.strip() for j in opts["--list"].split(",") if j.strip()]
        bad = [j for j in jobs if not re.fullmatch(r"[a-z0-9_-]{1,32}", j)]
        if bad:
            print("job codes are a-z, 0-9, - or _ (32 at most): %s" % ", ".join(bad)); return 2
        parked = [x.strip() for x in opts.get("--parked", "").split(",") if x.strip()]
        words = opts["--words"].replace('"', "'")
        text = ("# This week's goal\n\nSet: %s\nGoal (his words): \"%s\"\nDone when: %s\n\nSet list (job codes the crew works on for this goal):\n%s\n\n"
                "Parked (everything else, by name; it waits unless he adds it):\n%s\n"
                % (datetime.date.today().isoformat(), words, opts.get("--done", "not said"), "".join("- %s\n" % j for j in jobs).rstrip("\n"),
                   "".join("- %s\n" % x for x in parked).rstrip("\n")))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        old = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("goal %s: %d job(s) on the set list, %d parked" % ("changed" if old else "set", len(jobs), len(parked)))
        return 0
    if cmd == "clear":
        if os.path.exists(p):
            os.remove(p)
        print("no goal is set")
        return 0
    if not os.path.exists(p):
        if cmd == "check":
            return 0
        print("no goal is set"); return 0
    g = parse(open(p, encoding="utf-8").read())
    if cmd == "show":
        print('Goal: "%s"\nDone when: %s\nSet list: %s\nParked: %s' % (g["words"], g["done"], ", ".join(g["list"]) or "(none)", ", ".join(g["parked"]) or "(none)"))
        return 0
    if cmd == "check":
        job = a[1] if len(a) > 1 else ""
        if not g["list"] or job in g["list"]:
            print("on the goal" if g["list"] else "no set list")
            return 0
        print(reminder(g))
        return 1
    print(__doc__.split("\n\n")[0]); return 2


if __name__ == "__main__":
    sys.exit(main())
