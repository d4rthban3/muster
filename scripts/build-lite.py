#!/usr/bin/env python3
"""Builds Muster Lite's outputs from MUSTER-LITE.md, the one source of its two prompts:
the two skill zips in dist/lite/ (not in the plugin folder: attach them to the GitHub release tagged "lite", which the install
page links to) and the two prompt boxes on the install page."""
import html, io, os, re, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, "MUSTER-LITE.md"), encoding="utf-8").read()


def prompt(kind):
    m = re.search(r"<!-- lite:%s -->\n```\n(.*?)\n```\n<!-- /lite:%s -->" % (kind, kind), SRC, re.S)
    if not m:
        sys.exit("MUSTER-LITE.md: no %s prompt" % kind)
    return m.group(1)


def skill(kind, text):
    desc = ("Muster Lite for a new project: Muster's way of working in one chat. Use at the start of a project."
            if kind == "new" else
            "Muster Lite for an existing project: read what is there first, then work Muster's way. Use when joining a project.")
    body = "---\nname: muster-lite-%s\ndescription: %s\n---\n\n%s\n" % (kind, desc, text)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo("muster-lite-%s/SKILL.md" % kind, date_time=(2026, 1, 1, 0, 0, 0))
        z.writestr(info, body)
    return buf.getvalue()


os.makedirs(os.path.join(ROOT, "dist", "lite"), exist_ok=True)
page_path = os.path.join(ROOT, "docs", "index.html")
page = open(page_path, encoding="utf-8").read()
for kind in ("new", "existing"):
    text = prompt(kind)
    with open(os.path.join(ROOT, "dist", "lite", "muster-lite-%s.zip" % kind), "wb") as fh:
        fh.write(skill(kind, text))
    page, n = re.subn(r'(<pre class="lite" id="prompt-%s"[^>]*>).*?(</pre>)' % kind,
                      lambda m: m.group(1) + html.escape(text) + m.group(2), page, flags=re.S)
    if n != 1:
        sys.exit("docs/index.html: no prompt box for %s" % kind)
open(page_path, "w", encoding="utf-8").write(page)
print("built: 2 zips in dist/lite/, 2 prompt boxes")
