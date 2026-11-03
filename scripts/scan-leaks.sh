#!/usr/bin/env bash
# Fails (exit 1) if any file or commit in this repo carries private material.
# Patterns are written with bracket tricks so this file does not match itself.
# Project-specific private terms (names, handles, hosts) go one regex per line in .scan-extra (untracked, never published).
set -u
cd "$(dirname "$0")/.."

PATTERNS=(
  '/[uU]sers/[a-z]+'                     # local paths
  '/[pP]rivate/(tmp|var)'
  '\.worktrees'
  'sk-[a-zA-Z0-9_-]{16,}'                # key shapes
  'AKIA[0-9A-Z]{12,}'
  'gh[pousr]_[A-Za-z0-9]{20,}'
  'xox[bap]-[A-Za-z0-9-]{10,}'
  '-----BEGIN [A-Z ]*PRIVATE KEY'
  '0x[0-9a-fA-F]{40}'                    # EVM address
  '[1-9A-HJ-NP-Za-km-z]{43,44}'          # base58 address / key
  '[A-Za-z0-9+/]{40,}={0,2}'             # long base64-ish blob
  '[A-Fa-f0-9]{40,}'                     # long hex (hash/key)
  'local_[0-9a-f]{8}-[0-9a-f]{4}'        # session ids
  '[A-Za-z0-9._%+-]+@(gmail|outlook|yahoo|hotmail|icloud)\.'
)
[ -f .scan-extra ] && while IFS= read -r l; do [ -n "$l" ] && PATTERNS+=("$l"); done < .scan-extra

ALLOWED_HOSTS='^(localhost|github\.com|d4rthban3\.github\.io|code\.claude\.com|docs\.claude\.com|claude\.com|example\.com|example\.invalid)$'
fail=0
report() { echo "LEAK: $1"; fail=1; }

# long hex hashes are legal in git output only; files are scanned, .git is not
FILES=$(git ls-files -co --exclude-standard)
for p in "${PATTERNS[@]}"; do
  hits=$(echo "$FILES" | grep -v '^scripts/scan-leaks.sh$' | xargs grep -nIE -e "$p" 2>/dev/null | head -5)
  [ -n "$hits" ] && report "pattern /$p/" && echo "$hits"
  # file names too
  nh=$(echo "$FILES" | grep -E -e "$p")
  [ -n "$nh" ] && report "file name matches /$p/: $nh"
done

# any URL host outside the allowlist
echo "$FILES" | xargs grep -nIoE 'https?://[A-Za-z0-9.-]+' 2>/dev/null | while IFS= read -r line; do
  host=$(echo "$line" | sed -E 's#.*://##')
  echo "$host" | grep -Eq "$ALLOWED_HOSTS" || echo "LEAK: URL host not allowed: $line"
done | tee /tmp/.kitscan.$$ ; [ -s /tmp/.kitscan.$$ ] && fail=1; rm -f /tmp/.kitscan.$$

# commit metadata (author, committer, messages)
if git rev-parse HEAD >/dev/null 2>&1; then
  meta=$(git log --format='%an <%ae> | %cn <%ce> | %s%n%b')
  for p in "${PATTERNS[@]}"; do
    echo "$meta" | grep -qE -e "$p" && report "commit metadata matches /$p/"
  done
  # whole history of file contents
  for p in "${PATTERNS[@]}"; do
    git log -p --all -- . ':!scripts/scan-leaks.sh' 2>/dev/null | grep -E '^[+-]' | grep -qE -e "$p" && report "history diff matches /$p/"
  done
fi

if [ $fail -ne 0 ]; then echo "SCAN FAILED"; exit 1; fi
echo "SCAN CLEAN"
