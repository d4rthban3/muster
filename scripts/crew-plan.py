#!/usr/bin/env python3
"""Small helpers for starting and checking the crew (D-025). Standard library and git only.

  crew-plan.py inspectors <number of builders> [--project NAME]
      How many inspectors the crew needs (one for every three builders, at least one) and which builder's READYs go to which.
  crew-plan.py copy-name "<Role>_<project>_<N>"
      The short name of that chat's own copy of the project (made-up example: "Builder A_Shop_002" -> builder-a-002).
  crew-plan.py check-copy "<Role>_<project>_<N>" <folder>
      Exit 1 if the folder is not named for that chat's role (a renewed chat never runs in another role's old copy).
  crew-plan.py size <base> <head> [--repo DIR]
      SMALL or BIG for a piece of work: small = at most 3 files and 60 changed lines, nothing in engine, data, database or
      deploy folders, nothing a visitor sees (site pages, styles, scripts, pictures), no rules or protocol file. Anything else, or
      anything it cannot tell, is BIG. Small pieces are checked in the manager's chat by a fresh checker; big ones go to an inspector chat.
"""
import math
import os
import re
import subprocess
import sys


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def parse_chat(name):
    m = re.match(r"^(.+?)_(.+)_(\d{3})$", name.strip())
    if not m:
        sys.exit("crew-plan: '%s' is not <Role>_<project>_<three digits>" % name)
    return m.group(1), m.group(2), m.group(3)


def inspectors(n, project):
    k = max(1, math.ceil(n / 3))
    letters = [chr(ord("A") + i) for i in range(k)]
    names = ["Inspector_%s_001" % project] + ["Inspector %s_%s_001" % (l, project) for l in letters[1:]]
    print("builders=%d inspectors=%d" % (n, k))
    for i, nm in enumerate(names):
        lo, hi = i * 3 + 1, min(n, i * 3 + 3)
        bs = ", ".join("Builder %s" % chr(ord("A") + j - 1) for j in range(lo, hi + 1)) or "(none yet)"
        print("%s <- %s" % (nm, bs))


def size(base, head, repo):
    out = subprocess.run(["git", "-C", repo, "diff", "--numstat", base, head], capture_output=True, text=True)
    if out.returncode != 0:
        print("BIG: cannot read the change (%s)" % out.stderr.strip()[:80])
        return
    files, lines = [], 0
    for l in out.stdout.strip().splitlines():
        a, b, p = l.split("\t", 2)
        if a == "-" or b == "-":
            print("BIG: a binary or picture file changed (%s)" % p)
            return
        files.append(p)
        lines += int(a) + int(b)
    if not files:
        print("BIG: nothing differs, so nothing to call small")
        return
    if len(files) > 3 or lines > 60:
        print("BIG: %d files, %d changed lines (small = at most 3 files and 60 lines)" % (len(files), lines))
        return
    for p in files:
        q = p.replace("\\", "/")
        if re.search(r"(^|/)(engine|data|db|database|migrations|deploy|docs|site|public|static|assets|agents|templates|skills|commands|hooks|\.claude-plugin|muster)/", "/" + q) \
           or re.search(r"\.(sql|html?|css|jsx?|tsx?|svg|png|jpe?g|gif|webp)$", q, re.I):
            print("BIG: %s is engine, data, deploy, something a visitor sees, or a rules file" % p)
            return
    print("SMALL: %d files, %d changed lines, nothing in engine, data, deploy, visible or rules files" % (len(files), lines))


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "inspectors":
        proj = a[a.index("--project") + 1] if "--project" in a else "<project>"
        inspectors(int(a[1]), proj)
    elif len(a) == 2 and a[0] == "copy-name":
        role, _p, n = parse_chat(a[1])
        print("%s-%s" % (slug(role), n))
    elif len(a) == 3 and a[0] == "check-copy":
        role, _p, n = parse_chat(a[1])
        want = slug(role)
        base = os.path.basename(os.path.normpath(a[2])).lower()
        if base.startswith(want + "-"):
            print("OK: %s is named for %s" % (a[2], role))
        else:
            print("REFUSED: %s is not named for %s (expected a folder starting '%s-'); a renewed chat gets its own new copy, never another role's old one" % (a[2], role, want))
            sys.exit(1)
    elif len(a) >= 3 and a[0] == "size":
        size(a[1], a[2], a[a.index("--repo") + 1] if "--repo" in a else ".")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
