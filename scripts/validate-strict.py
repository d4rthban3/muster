#!/usr/bin/env python3
"""strict-backdrop: `claude plugin validate --strict` treats every warning as an error. The owner accepted ONE known warning (the look
panel's ui.render{component=Backdrop}, "no component is named Backdrop"); any other warning, or any error, must still fail.

Usage: validate-strict.py [folder]            run the validator on the folder (default .) and judge it
       validate-strict.py --from FILE --rc N  judge saved validator output and exit code (the tests use this)
Exit 0: the validator passed, or its only warning is the known Backdrop one. Exit 1: anything else (the output is printed)."""
import re
import subprocess
import sys

KNOWN = re.compile(r"component=Backdrop\}: no component is named Backdrop\b")


def judge(text, rc):
    if rc == 0:
        return True, "passed"
    m = re.search(r"Found (\d+) warning", text)
    if re.search(r"Found \d+ error", text) or not m:
        return False, "the validator reported errors, or no warning list I can read"
    n = int(m.group(1))
    lines = text[m.end():].splitlines()[1:]
    warns = []
    for ln in lines:
        s = ln.strip()
        if not s:
            if warns:
                break
            continue
        if s.startswith("❯"):
            warns.append(s)
            if len(warns) == n:
                break
    if len(warns) != n:
        return False, "could not read all %d warnings" % n
    other = [w for w in warns if not KNOWN.search(w)]
    if other:
        return False, "a warning other than the known Backdrop one: " + other[0]
    return True, "only the known Backdrop warning (accepted by the owner)"


def main():
    a = sys.argv[1:]
    if a[:1] == ["--from"]:
        text, rc = open(a[1], encoding="utf-8").read(), int(a[3])
    else:
        r = subprocess.run(["claude", "plugin", "validate", a[0] if a else ".", "--strict"], capture_output=True, text=True)
        text, rc = r.stdout + r.stderr, r.returncode
    ok, why = judge(text, rc)
    if not ok:
        print(text)
    print(("VALIDATE OK: " if ok else "VALIDATE FAILED: ") + why)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
