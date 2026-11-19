#!/bin/sh
# try-program.sh <plugin folder> <check>: runs the ready-built program's <check> on this script's standard input and prints its answer, exit 0.
# Exit 1 with nothing printed when there is no program for this computer, it will not start, or it ends with any exit code but 0 (a crash, an
# older program that does not know the check, a killed run): the hook then runs the Python copy, the safety net. A hook's own answers
# (allow, or a refusal as JSON) are always exit 0. The answer is held until the program has finished, so a program that dies half way
# never leaves half an answer beside the Python one.
bin=$(sh "$(dirname "$0")/find-binary.sh" "$1" 2>/dev/null) || exit 1
out=$("$bin" "$2") || exit 1
[ -z "$out" ] || printf '%s\n' "$out"
exit 0
