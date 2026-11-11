#!/usr/bin/env python3
"""The directory edition (owner's list item 37, "Two editions"): a copy of Muster made only of Markdown, JSON and PNG images,
for the plugin directory's review. No hooks, no scripts, no programs, no html/zip/font files. The full edition (GitHub) stays as is.
  build-directory.py            write directory/
  build-directory.py --check    exit 1 if directory/ is out of date (the version number is not compared: a ship raises it)
  build-directory.py --verify   check every file of directory/ against the review's rules and print the counts
What goes in: agents/ (the role pages, each with a one-line notice that coded checks and scripts are not in this edition), skills/,
commands/ (except setup, which opens the setup page), templates/*.md, the logo, LICENSE, a README that points to the full edition."""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "directory")
FULL = "https://github.com/d4rthban3/muster"
ALLOWED = {".md", ".json", ".png"}
NOTICE = ("> Directory edition: this copy holds the rules only. The coded checks, scripts and ready-made programs named below are "
          "in the full edition (" + FULL + "); here, do by hand what a page says a script does, and say so.\n\n")
SKIP_COMMANDS = {"setup.md"}
# what the review warned about: reading credentials, or redirecting a package source
BAD = re.compile(r"(\.ssh|\.aws|\.netrc|id_rsa|api[_-]?key\s*=|password\s*=|BEGIN [A-Z ]*PRIVATE KEY|sk-[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{12,})", re.I)


def read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


def files():
    """{relative path in the edition: text or bytes}"""
    out = {}
    plugin = json.loads(read(".claude-plugin/plugin.json"))
    plugin["description"] = plugin["description"] + " Directory edition: rules only; the full edition with coded checks is on GitHub."
    out[".claude-plugin/plugin.json"] = json.dumps(plugin, indent=2) + "\n"
    out[".claude-plugin/marketplace.json"] = json.dumps({
        "name": "muster-kit", "description": "The crew method for Claude Code, directory edition (rules only).",
        "owner": {"name": "Muster contributors"},
        "plugins": [{"name": "muster", "version": plugin["version"], "source": "./", "description": plugin["description"]}]}, indent=2) + "\n"
    for fn in sorted(os.listdir(os.path.join(ROOT, "agents"))):
        t = read("agents/" + fn)
        m = re.match(r"^(---\n.*?\n---\n)\n?(.*)$", t, re.S)
        out["agents/" + fn] = (m.group(1) + "\n" + NOTICE + m.group(2)) if m else NOTICE + t
    for dp, _, fs in os.walk(os.path.join(ROOT, "skills")):
        for f in fs:
            if os.path.splitext(f)[1] in ALLOWED:
                rel = os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/")
                out[rel] = read(rel)
    for fn in sorted(os.listdir(os.path.join(ROOT, "commands"))):
        if fn.endswith(".md") and fn not in SKIP_COMMANDS:
            out["commands/" + fn] = read("commands/" + fn)
    for fn in sorted(os.listdir(os.path.join(ROOT, "templates"))):
        if fn.endswith(".md"):
            out["templates/" + fn] = read("templates/" + fn)
    out["assets/muster-logo.png"] = open(os.path.join(ROOT, "assets", "muster-logo.png"), "rb").read()
    out["LICENSE.md"] = read("LICENSE")
    out["README.md"] = ("# Muster (directory edition)\n\nA crew of Claude Code chats: a manager you talk to, builders, a designer and inspectors.\n\n"
                        "This edition holds only the rules (role pages, skills, commands and templates) as Markdown and JSON. It has no hooks, "
                        "scripts or programs.\n\nThe **full edition**, with the coded checks that refuse a wrong message or a skipped rule, "
                        "the setup page and the ready-made programs, installs from GitHub: " + FULL + "\n")
    return out


def strip_version(t):
    return re.sub(r'"version": "[0-9.]+"', '"version": "x"', t)


def write():
    shutil.rmtree(OUT, ignore_errors=True)
    for rel, data in files().items():
        p = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(data if isinstance(data, bytes) else data.encode("utf-8"))
    print("wrote %d files to directory/" % len(files()))


def listing():
    found = {}
    for dp, _, fs in os.walk(OUT):
        for f in fs:
            found[os.path.relpath(os.path.join(dp, f), OUT).replace(os.sep, "/")] = open(os.path.join(dp, f), "rb").read()
    return found


def check():
    want, have = files(), listing()
    bad = 0
    for rel in sorted(set(want) | set(have)):
        w, h = want.get(rel), have.get(rel)
        if h is None or w is None:
            print("OUT OF DATE (%s): %s" % ("missing" if h is None else "extra", rel)); bad += 1; continue
        w = w if isinstance(w, bytes) else w.encode("utf-8")
        if rel.endswith(".json"):
            w, h = strip_version(w.decode()).encode(), strip_version(h.decode()).encode()
        if w != h:
            print("OUT OF DATE:", rel); bad += 1
    print("directory edition: %d files, %d out of date" % (len(want), bad))
    return 1 if bad else 0


def verify():
    have, bad, counts = listing(), 0, {}
    if not have:
        print("no directory/ yet"); return 1
    for rel, data in sorted(have.items()):
        ext = os.path.splitext(rel)[1]
        counts[ext] = counts.get(ext, 0) + 1
        if ext not in ALLOWED:
            print("NOT ALLOWED (%s): %s" % (ext or "no extension", rel)); bad += 1; continue
        if os.path.basename(rel) == "hooks.json" or rel.startswith("hooks/"):
            print("HOOK FILE: " + rel); bad += 1
        if ext == ".png":
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                print("NOT A PNG: " + rel); bad += 1
            continue
        if data.startswith(b"#!"):
            print("STARTS WITH #!: " + rel); bad += 1
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            print("NOT UTF-8: " + rel); bad += 1; continue
        if ext == ".json":
            try:
                j = json.loads(text)
            except ValueError:
                print("BAD JSON: " + rel); bad += 1; continue
            if "hooks" in j:
                print("HOOKS KEY: " + rel); bad += 1
        m = BAD.search(text)
        if m:
            print("CREDENTIAL-LIKE TEXT (%s) in %s" % (m.group(1)[:20], rel)); bad += 1
    print("directory edition: %d files (%s); %d problem(s)" % (len(have), ", ".join("%d %s" % (n, e) for e, n in sorted(counts.items())), bad))
    return 1 if bad else 0


if "--check" in sys.argv:
    sys.exit(check())
if "--verify" in sys.argv:
    sys.exit(verify())
write()
sys.exit(verify())
