#!/usr/bin/env python3
"""Fallback plugin check: the plugin, marketplace and release files parse, and the versions agree. Exit 1 if not."""
import glob
import json
import sys

try:
    for f in [".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"] + glob.glob(".claude-plugin/releases/*.json"):
        json.load(open(f, encoding="utf-8"))
    p = json.load(open(".claude-plugin/plugin.json", encoding="utf-8"))
    m = json.load(open(".claude-plugin/marketplace.json", encoding="utf-8"))
    assert p["name"] and p["version"], "plugin.json lacks name or version"
    assert m["plugins"][0]["version"] == p["version"], "plugin and marketplace versions differ"
except Exception as err:
    print("BAD:", err)
    sys.exit(1)
print("json and fields ok", p["version"])
