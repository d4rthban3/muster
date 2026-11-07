#!/usr/bin/env python3
"""Checks that a worker's report has the six-line shape: python3 check-report.py <file>.
First line: FIRST WORD: job name [ID role-job-number]; then What, Where (with "touches:"), Why, How, Need, in order.
A READY must also show a test result on its How line (a count such as 12/12 or "12 passed"). Exit 1 and say why if not.
"""
import re
import sys

FIRST = r"(DONE|READY|PASS|FAIL|OWNER CALL|STUCK|NEED)"


def check(text):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    usage = None
    if len(lines) == 7 and lines[6].startswith("Usage:"):
        usage = lines.pop()
    if len(lines) != 6:
        return "expected 6 lines (and a Usage line on DONE and READY), found %d" % len(lines)
    m = re.match(r"^%s: .+ \[ID [^\]]+-\d+\]$" % FIRST, lines[0])
    if not m:
        return "first line must be 'FIRST WORD: job name [ID role-job-number]'"
    for line, label in zip(lines[1:], ["What:", "Where:", "Why:", "How:", "Need:"]):
        if not line.startswith(label):
            return "expected a line starting %s" % label
    if "touches:" not in lines[2]:
        return "Where line lacks 'touches:'"
    if m.group(1) in ("DONE", "READY") and usage is None:
        return "a DONE or READY needs a Usage line (scripts/usage.py prints it)"
    if m.group(1) == "READY" and not re.search(r"\d+\s*(/|of)\s*\d+|\d+ passed", lines[4]):
        return "READY's How line shows no test count"
    return None


if __name__ == "__main__":
    problem = check(open(sys.argv[1], encoding="utf-8").read())
    print("OK" if problem is None else "BAD: " + problem)
    sys.exit(0 if problem is None else 1)
