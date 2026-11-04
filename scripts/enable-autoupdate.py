#!/usr/bin/env python3
"""Turn on Claude Code's auto-update for the Muster marketplace in the user's own settings file.

Usage: enable-autoupdate.py
Reads ~/.claude/settings.json (or $CLAUDE_CONFIG_DIR/settings.json), finds extraKnownMarketplaces.muster-kit and sets
"autoUpdate": true on it, keeping every other setting. Saves the old file next to it as settings.json.muster-backup first.
Run only after the person pressed the button that asks for it. Exit 0 done or already on; 3 muster-kit not declared.
Auto-update is a per-marketplace switch that only the user's settings (or the /plugin screen) can set: a marketplace
or plugin file cannot turn it on (claude plugin validate calls such a field unknown).
"""
import json
import os
import shutil
import sys

base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
path = os.path.join(base, "settings.json")
try:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
except (OSError, ValueError) as err:
    print("Could not read %s (%s). Nothing changed." % (path, err))
    sys.exit(3)
entry = (data.get("extraKnownMarketplaces") or {}).get("muster-kit")
if not isinstance(entry, dict):
    print("muster-kit is not declared in %s. Nothing changed." % path)
    sys.exit(3)
if entry.get("autoUpdate") is True:
    print("Auto-update is already on for muster-kit.")
    sys.exit(0)
shutil.copyfile(path, path + ".muster-backup")
entry["autoUpdate"] = True
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
print("Auto-update is on for muster-kit (old file kept as settings.json.muster-backup).")
