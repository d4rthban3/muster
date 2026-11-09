#!/usr/bin/env python3
"""Each worker loads ONE page: agents/<role>.md = its front matter + pages/shared.md (the talk-to-you block first, then the message
record and the always-rules) + pages/<role>.md (its job). Edit the parts in pages/, then run this to write the pages.
  build-pages.py           write agents/*.md
  build-pages.py --check   exit 1 if a page is out of date or longer than WORD_CAP words (the free test runs this)"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORD_CAP = 700
shared = open(os.path.join(ROOT, "pages", "shared.md"), encoding="utf-8").read().strip()
bad = 0
for fn in sorted(os.listdir(os.path.join(ROOT, "pages"))):
    role = fn[:-3]
    if fn == "shared.md" or not fn.endswith(".md"):
        continue
    page = os.path.join(ROOT, "agents", fn)
    old = open(page, encoding="utf-8").read()
    m = re.match(r"^(---\n.*?\n---\n)", old, re.S)
    if not m:
        print("no front matter in", page)
        bad += 1
        continue
    new = m.group(1) + "\n" + shared + "\n\n---\n\n" + open(os.path.join(ROOT, "pages", fn), encoding="utf-8").read().strip() + "\n"
    words = len(re.sub(r"^---\n.*?\n---\n", "", new, flags=re.S).split())
    if words > WORD_CAP:
        print("TOO LONG: %s is %d words (cap %d)" % (page, words, WORD_CAP))
        bad += 1
    if "--check" in sys.argv:
        if new != old:
            print("OUT OF DATE:", page)
            bad += 1
    else:
        open(page, "w", encoding="utf-8", newline="\n").write(new)
    print("%-22s %4d words" % (role, words))
sys.exit(1 if bad else 0)
