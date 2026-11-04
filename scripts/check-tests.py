#!/usr/bin/env python3
"""Fails if a test file on disk is not listed in muster/CHECKS.md.

Usage: check-tests.py [project-folder]   (default: the current folder)
A test file is test_*.py, *_test.py, *.test.* or *.spec.* anywhere in the project, outside .git, node_modules, .claude
and muster. A file counts as listed when its name appears in muster/CHECKS.md. No test files: passes. No CHECKS.md but
test files: fails. Prints what it found; changes nothing.
"""
import fnmatch
import os
import sys

PATTERNS = ("test_*.py", "*_test.py", "*.test.*", "*.spec.*")
SKIP = {".git", "node_modules", ".claude", "muster"}


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
    found = []
    for here, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for f in files:
            if any(fnmatch.fnmatch(f, p) for p in PATTERNS):
                found.append(os.path.relpath(os.path.join(here, f), root))
    checks = os.path.join(root, "muster", "CHECKS.md")
    try:
        with open(checks, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        text = None
    missing = [f for f in found if text is None or os.path.basename(f) not in text]
    print("%d test file(s) on disk, %d missing from muster/CHECKS.md" % (len(found), len(missing)))
    for f in missing:
        print("  not in CHECKS.md: " + f)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
