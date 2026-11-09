#!/bin/sh
# Prints the path of the ready-built muster-checks program for this computer, or prints nothing and exits 1 (then the
# Python copies run). It looks in this plugin's bin/ folder AND in the newest Muster version installed beside it, so a chat
# that was started on an older version picks up a newer check on its next hook call, with no restart.
root=${1:-$(cd "$(dirname "$0")/.." && pwd)}
case "$(uname -s 2>/dev/null)" in
  Darwin) os=macos ;; Linux) os=linux ;; MINGW*|MSYS*|CYGWIN*|Windows*) os=windows ;; *) exit 1 ;;
esac
case "$(uname -m 2>/dev/null)" in
  arm64|aarch64) arch=arm64 ;; x86_64|amd64|AMD64) arch=x86_64 ;; *) arch=x86_64 ;;
esac
exe=muster-checks; [ "$os" = windows ] && exe=muster-checks.exe
newest="$root"
parent=$(dirname "$root")
for d in $(ls -d "$parent"/*/ 2>/dev/null | sed 's#/$##' | sort -V); do
  [ -f "$d/.claude-plugin/plugin.json" ] && [ -f "$d/bin/$os-$arch/$exe" ] && newest="$d"
done
for d in "$newest" "$root"; do
  [ -f "$d/bin/$os-$arch/$exe" ] && { echo "$d/bin/$os-$arch/$exe"; exit 0; }
done
exit 1
