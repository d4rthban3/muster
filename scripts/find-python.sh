#!/bin/sh
# Prints the command that runs Python 3 on this computer, or prints nothing and exits 1.
# On Windows, "python3" is often only a Microsoft Store stub that opens the Store and fails, so each name is
# tried for real (it must print "Python 3.x"), in this order: python3, python, py -3.
for c in "python3" "python" "py -3"; do
  out=$($c --version 2>&1) || continue
  case "$out" in "Python 3"*) echo "$c"; exit 0 ;; esac
done
exit 1
