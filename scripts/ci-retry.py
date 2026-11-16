#!/usr/bin/env python3
"""Item 121: when GitHub's free test fails only because a job never got a machine ("not acquired by Runner", a cancelled or startup-failed
job whose steps never ran), rerun just the failed jobs instead of calling it a failure. A job that ran a step and failed is a real failure.

Usage: ci-retry.py <branch> <sha> [--done N] [--max M]
Looks at the newest finished, not-successful run of <sha> on <branch>. Exit 0 and a line "RERAN <id>" if every failed job never ran and
fewer than M (default 3) reruns were already done (N); exit 1 with the reason otherwise (a real failure, nothing to rerun, or out of tries)."""
import json
import subprocess
import sys

BAD = ("failure", "cancelled", "timed_out", "startup_failure")


def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True)
    return r.returncode, r.stdout


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        return 2
    branch, sha = a[0], a[1]
    done = int(a[a.index("--done") + 1]) if "--done" in a else 0
    mx = int(a[a.index("--max") + 1]) if "--max" in a else 3
    rc, out = gh("run", "list", "--branch=" + branch, "--limit=10", "--json=databaseId,headSha,status,conclusion")
    try:
        runs = json.loads(out) if rc == 0 else []
    except ValueError:
        runs = []
    runs = [r for r in runs if r.get("headSha") == sha and r.get("status") == "completed" and r.get("conclusion") != "success"]
    if not runs:
        print("no finished unsuccessful run of this version to rerun")
        return 1
    rid = str(runs[0]["databaseId"])
    if done >= mx:
        print("already reran %d times; giving up" % done)
        return 1
    rc, out = gh("run", "view", rid, "--json", "jobs")
    try:
        jobs = json.loads(out)["jobs"] if rc == 0 else None
    except (ValueError, KeyError):
        jobs = None
    if not jobs:
        print("could not read the jobs of run %s" % rid)
        return 1
    failed = [j for j in jobs if j.get("conclusion") in BAD]
    if not failed:
        print("run %s has no failed job to rerun" % rid)
        return 1
    ran = [j for j in failed if any(s.get("conclusion") in ("success", "failure") for s in (j.get("steps") or []))]
    if ran:
        print("a real failure: %s ran and failed" % ", ".join(j.get("name", "?") for j in ran))
        return 1
    rc, _ = gh("run", "rerun", rid, "--failed")
    if rc != 0:
        print("could not rerun run %s" % rid)
        return 1
    print("RERAN %s (%d job(s) never got a machine)" % (rid, len(failed)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
