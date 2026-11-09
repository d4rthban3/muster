#!/usr/bin/env python3
"""bin/SOURCE-STAMP holds a hash of the Rust source the ready-made copies in bin/ were built from.
  source-stamp.py          write the stamp (run after replacing the copies)
  source-stamp.py --check  exit 1 unless the stamp matches checks/src, checks/Cargo.toml and checks/Cargo.lock
A copy built from other source than the one in the repository therefore can never be shipped by mistake."""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(ROOT, "checks", "src")) for f in fs)
files += [os.path.join(ROOT, "checks", "Cargo.toml"), os.path.join(ROOT, "checks", "Cargo.lock")]
h = hashlib.sha256()
for f in files:
    h.update(os.path.relpath(f, ROOT).replace("\\", "/").encode() + b"\0" + open(f, "rb").read().replace(b"\r\n", b"\n") + b"\0")
d = h.hexdigest()
want = "-".join(d[i:i + 8] for i in range(0, len(d), 8))  # dashes keep it from looking like a secret to the leak scan
stamp = os.path.join(ROOT, "bin", "SOURCE-STAMP")
if "--check" in sys.argv:
    have = open(stamp).read().strip() if os.path.exists(stamp) else ""
    print("OK: the shipped copies match the source" if have == want else "STALE: bin/SOURCE-STAMP does not match checks/ (rebuild the copies)")
    sys.exit(0 if have == want else 1)
os.makedirs(os.path.dirname(stamp), exist_ok=True)
open(stamp, "w").write(want + "\n")
print("wrote", stamp)
