#!/bin/sh
# MUSTER-LIVE-STANDIN-SH: a small shell stand-in written by install-checks.py --live <Muster folder> (rust-first piece 6).
# Installed as <project>/.muster-checks/<check name>.sh. It runs the ready-built program's check from the Muster folder FIRST, telling the program
# which project it runs for (MUSTER_PROJECT) and giving it the Muster folder's live profile (MUSTER_PROFILE), and runs the Python live stand-in
# beside it (<check name>.py) when the program is missing, will not start, crashes, is killed or ends with any exit code but 0.
# live.env beside it (written by the installer) names the Muster folder and the live profile. Written by install-checks.py; do not edit by hand.
here=$(cd "$(dirname "$0")" && pwd)
name=$(basename "$0" .sh)
ev=$(cat)
case "$name" in
  rules-check) sub=rules ;; board-stop) sub=board-stop ;; talk-check) sub=talk ;; worker-queue-check) sub=worker-queue ;;
  idle-check) sub=idle-check ;; renew-after-summary) sub=renew ;; precompact-board) sub=precompact ;; *) sub="" ;;
esac
MUSTER_FOLDER=""; MUSTER_LIVE_PROFILE=""
[ -f "$here/live.env" ] && . "$here/live.env"
if [ -n "$sub" ] && [ -n "$MUSTER_FOLDER" ] && [ -f "$MUSTER_FOLDER/scripts/try-program.sh" ]; then
  project=$(cd "$here/.." && { pwd -W 2>/dev/null || pwd; })
  if [ -z "$MUSTER_PROFILE" ] && [ -n "$MUSTER_LIVE_PROFILE" ] && [ -f "$MUSTER_FOLDER/$MUSTER_LIVE_PROFILE" ]; then MUSTER_PROFILE="$MUSTER_FOLDER/$MUSTER_LIVE_PROFILE"; export MUSTER_PROFILE; fi
  MUSTER_PROJECT="$project"; export MUSTER_PROJECT
  out=$(printf '%s' "$ev" | sh "$MUSTER_FOLDER/scripts/try-program.sh" "$MUSTER_FOLDER" "$sub") && { [ -z "$out" ] || printf '%s\n' "$out"; exit 0; }
  unset MUSTER_PROJECT
fi
# the safety net: the Python live stand-in (it says plainly when the Muster folder is missing)
py=""
for c in "python3" "python" "py -3"; do
  o=$($c --version 2>&1) || continue
  case "$o" in "Python 3"*) py="$c"; break ;; esac
done
if [ -z "$py" ]; then
  printf '%s\n' "{\"systemMessage\": \"Muster live check ($name) is not running: no program ran and Python 3 was not found.\"}"
  exit 0
fi
printf '%s' "$ev" | $py "$here/$name.py"
