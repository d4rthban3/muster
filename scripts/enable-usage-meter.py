#!/usr/bin/env python3
"""Turn on Muster's usage meter: set Claude Code's status line to scripts/usage-statusline.py in the user's own settings.

Usage: enable-usage-meter.py <python command>      (the one scripts/find-python.sh printed, e.g. python3)
Copies usage-statusline.py to <config folder>/muster-usage/statusline.py (so the path survives plugin updates) and sets
"statusLine" in <config folder>/settings.json, keeping every other setting and saving settings.json.muster-backup first.
It never replaces a status line the person already has (exit 4, nothing changed). Exit 0 done or already on.
Run only after the person pressed the button that asks for it.
"""
import json
import os
import shutil
import sys

py = sys.argv[1] if len(sys.argv) > 1 else "python3"
base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
path = os.path.join(base, "settings.json")
try:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
except FileNotFoundError:
    data = {}
except (OSError, ValueError) as err:
    print("Could not read %s (%s). Nothing changed." % (path, err))
    sys.exit(3)
dest = os.path.join(base, "muster-usage", "statusline.py")
cmd = '%s "%s"' % (py, dest.replace("\\", "/"))
cur = data.get("statusLine")
if isinstance(cur, dict) and cur.get("command") == cmd:
    print("The usage meter is already on.")
    sys.exit(0)
if cur:
    print("A status line is already set; Muster leaves it alone, so the weekly figure stays unreadable.")
    sys.exit(4)
os.makedirs(os.path.dirname(dest), exist_ok=True)
shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "usage-statusline.py"), dest)
if os.path.exists(path):
    shutil.copyfile(path, path + ".muster-backup")
data["statusLine"] = {"type": "command", "command": cmd}
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
print("The usage meter is on (old settings kept as settings.json.muster-backup).")
