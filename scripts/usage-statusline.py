#!/usr/bin/env python3
"""Claude Code status line for Muster: saves what a chat can know about its own usage, and prints one short line.

Claude Code runs this after each reply and sends session data as JSON on stdin (cost, tokens, and, for claude.ai
Pro/Max/Ultra, the 5-hour and weekly limits). It writes <config folder>/muster-usage/<session id>.json for
scripts/usage.py to read, and prints e.g. "Muster usage: week 41%, session $0.31". No network. Standard library only.
"""
import json
import os
import sys
import time

try:
    d = json.load(sys.stdin)
except ValueError:
    print("Muster usage: unreadable")
    sys.exit(0)
base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
rl = d.get("rate_limits") or {}
week = (rl.get("seven_day") or {})
five = (rl.get("five_hour") or {})
out = {
    "session_id": d.get("session_id"),
    "saved_at": int(time.time()),
    "cost_usd": (d.get("cost") or {}).get("total_cost_usd"),
    "context_tokens": (d.get("context_window") or {}).get("total_input_tokens"),
    "week_used_percent": week.get("used_percentage"),
    "week_resets_at": week.get("resets_at"),
    "five_hour_used_percent": five.get("used_percentage"),
}
sid = str(d.get("session_id") or "unknown")
if all(c.isalnum() or c in "-_" for c in sid):
    try:
        os.makedirs(os.path.join(base, "muster-usage"), exist_ok=True)
        with open(os.path.join(base, "muster-usage", sid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh)
    except OSError:
        pass
parts = []
if out["week_used_percent"] is not None:
    parts.append("week %d%%" % round(out["week_used_percent"]))
if out["cost_usd"] is not None:
    parts.append("session $%.2f" % out["cost_usd"])
print("Muster usage: " + (", ".join(parts) or "no data yet"))
