#!/usr/bin/env python3
"""Prints the Usage line for a DONE or READY report, from what this computer can actually read. No invented numbers.

Usage: usage.py [--session <id>] [--limit-percent 90]
Reads <config folder>/muster-usage/*.json (written by scripts/usage-statusline.py; the newest file, or the session named).
Prints:  Usage: session $0.31 at list price; week 41% used (resets <date>); read at <time>
or, when a part cannot be read, says so: "week limit not readable (only claude.ai Pro/Max/Ultra with Muster's status line)".
Exit 3 when the weekly figure is at or above --limit-percent (default 90): the crew should pause and the manager tell the owner.
"""
import argparse
import glob
import json
import os
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--session")
ap.add_argument("--limit-percent", type=float, default=90.0)
a = ap.parse_args()
base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
files = glob.glob(os.path.join(base, "muster-usage", (a.session or "*") + ".json"))
if not files:
    print("Usage: not readable (Muster's status line is not saving usage here; run /muster:setup or ask the manager to turn it on)")
    sys.exit(0)
f = max(files, key=os.path.getmtime)
try:
    d = json.load(open(f, encoding="utf-8"))
except (OSError, ValueError):
    print("Usage: not readable (the saved usage file is damaged)")
    sys.exit(0)
bits = []
bits.append("session $%.2f at list price" % d["cost_usd"] if d.get("cost_usd") is not None else "session cost not readable")
wk = d.get("week_used_percent")
if wk is None:
    bits.append("week limit not readable (only claude.ai Pro/Max/Ultra with Muster's status line)")
else:
    when = time.strftime("%a %d %b", time.localtime(d["week_resets_at"])) if d.get("week_resets_at") else "?"
    bits.append("week %d%% used (resets %s)" % (round(wk), when))
bits.append("read at " + time.strftime("%H:%M", time.localtime(d.get("saved_at", 0))))
print("Usage: " + "; ".join(bits))
sys.exit(3 if wk is not None and wk >= a.limit_percent else 0)
