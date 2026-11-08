#!/usr/bin/env bash
# One-command shipping, from a branch whose work the inspector passed.
# Usage: scripts/ship.sh "one-line note" [--roles Manager,Builder] [--platforms claude-code] [--with branch] [--dry-run] [--no-wait]
# It: fetches; rebases THIS branch only on origin/main; takes main's version plus one; writes the release file and the
# CHANGELOG entry from your note; runs version-check, the leak scan and a push look; pushes this branch under a new name
# (never forced), waits for the free test to go green, pushes to main fast-forward only; waits for the free test on
# main and the site's rebuild; proves the new content is served (published version, and a changed line of the site). It stops at the first failure and says why. It never
# force-pushes, never touches another branch, and never pushes anything in muster/.
# --with <branch> (repeatable): ship several passed branches as one release. Batch only branches that do not touch the same files.
# --dry-run: do everything on this computer, push nothing. --no-wait: push, but do not wait on GitHub (used by the test).
set -u
export MSYS2_ARG_CONV_EXCL='*'   # Git Bash on Windows must not rewrite 'origin/main:file' as a path list
note=""; roles=""; platforms="claude-code"; dry=0; wait=1; with=""
while [ $# -gt 0 ]; do case "$1" in
  --roles) roles=$2; shift 2;; --platforms) platforms=$2; shift 2;;
  --with) with="$with $2"; shift 2;; --dry-run) dry=1; shift;; --no-wait) wait=0; shift;;
  *) note=$1; shift;; esac; done
stop() { echo "SHIP STOPPED: $*"; exit 1; }
[ -n "$note" ] || stop "give a one-line note: scripts/ship.sh \"what changed\""
cd "$(git rev-parse --show-toplevel)" || stop "not in a git folder"
branch=$(git rev-parse --abbrev-ref HEAD)
[ "$branch" != main ] && [ "$branch" != HEAD ] || stop "run it from your own branch, not main"
[ -z "$(git status --porcelain --untracked-files=no)" ] || stop "uncommitted changes; save them first"
git fetch -q origin || stop "could not fetch origin"
orig=$(git rev-parse HEAD)
# a dry run leaves the branch exactly as it was, even if it stops early
[ $dry = 1 ] && trap 'git reset -q --hard "$orig" 2>/dev/null' EXIT
git rebase origin/main >/dev/null 2>&1 || { git rebase --abort >/dev/null 2>&1; stop "rebasing $branch on origin/main hit a conflict; fix it by hand and run again"; }
# a batch: merge each other passed branch into this one, so one version, one free test and one live proof cover them all
for w in $with; do
  git rev-parse -q --verify "$w" >/dev/null || stop "--with $w: no such branch"
  git merge -q --no-edit "$w" >/dev/null 2>&1 || { git merge --abort >/dev/null 2>&1; stop "merging $w into $branch hit a conflict; ship them one after the other"; }
  echo "== batch: merged $w"
done
py=$(sh "$(dirname "$0")/find-python.sh") || stop "no working Python 3"
ver=$(git show origin/main:.claude-plugin/plugin.json | $py -c 'import json,sys;print(json.load(sys.stdin)["version"])')
new=$($py -c 'import sys;a=sys.argv[1].split(".");a[-1]=str(int(a[-1])+1);print(".".join(a))' "$ver")
have=$($py -c 'import json;print(json.load(open(".claude-plugin/plugin.json"))["version"])')
files=$(git diff --name-only origin/main HEAD | paste -sd, -)
[ -n "$files" ] || stop "nothing differs from origin/main"
echo "== main is $ver; shipping $new ($files)"
keep=0
if [ "$have" = "$new" ] && [ -f ".claude-plugin/releases/$new.json" ] && grep -q "^## $new\$" CHANGELOG.md; then keep=1; echo "== the branch already carries version $new, its release file and its changelog entry: keeping them"
elif [ "$have" != "$ver" ]; then stop "the branch says version $have; main is $ver, so it should be $ver (to be replaced) or $new (complete); fix by hand"; fi
if [ $keep = 0 ]; then
$py - "$new" "$note" "$roles" "$platforms" "$files" <<'PY' || stop "could not write the release files"
import json, os, re, sys
os.makedirs(".claude-plugin/releases", exist_ok=True)
v, note, roles, plat, files = sys.argv[1:6]
for p in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
    t = open(p, encoding="utf-8").read()
    open(p, "w", encoding="utf-8").write(re.sub(r'"version": "[0-9.]+"', '"version": "%s"' % v, t, count=1))
r = {"version": v, "changed_files": files.split(","), "affected_roles": [x for x in roles.split(",") if x],
     "affected_platforms": plat.split(","), "records_change": False, "note": note}
open(".claude-plugin/releases/%s.json" % v, "w", encoding="utf-8").write(json.dumps(r, indent=2) + "\n")
c = open("CHANGELOG.md", encoding="utf-8").read()
i = c.index("\n## ") + 1
entry = "## %s\nAffects: %s.\n%s\n\n" % (v, ", ".join(x for x in roles.split(",") if x) or "see .claude-plugin/releases/%s.json" % v, note)
open("CHANGELOG.md", "w", encoding="utf-8").write(c[:i] + entry + c[i:])
PY
git add -A .claude-plugin CHANGELOG.md
git commit -q -m "Version $new: $note" || stop "could not save the version commit"
fi
bash scripts/version-check.sh || stop "version-check failed"
bash scripts/scan-leaks.sh >/dev/null 2>&1 || { bash scripts/scan-leaks.sh 2>&1 | tail -5; stop "the leak scan failed"; }
n=$(git rev-list --count origin/main..HEAD)
echo "== the push carries $n commit(s):"; git log --format='  %h %s' origin/main..HEAD
crew=$(git log --format= --name-only origin/main..HEAD -- ':(top)muster/' | sort -u)
[ -z "$crew" ] || stop "the push would carry crew files (muster/): $crew"
# a changed line of a site page, so the live check can prove the new page (not the old one) is served
proof_file=""; proof_line=""
for f in $(git diff --name-only origin/main HEAD -- docs | grep '\.html$'); do
  l=$(git diff -U0 origin/main HEAD -- "$f" | grep '^+' | grep -v '^+++' | sed 's/^+//' | awk 'length($0)>=25 && length($0)<=200' | head -1)
  if [ -n "$l" ]; then proof_file=$f; proof_line=$l; break; fi
done
if [ $dry = 1 ]; then echo "SHIP DRY RUN OK: would push $new; nothing was pushed"; exit 0; fi
tmp="ship/$new"
git push -q origin "HEAD:refs/heads/$tmp" || stop "could not push the branch copy $tmp"
if [ $wait = 1 ]; then
  command -v gh >/dev/null || stop "gh is not installed, cannot wait for the free test"
  sha=$(git rev-parse HEAD); echo "== waiting for the free test on $tmp"
  for _ in $(seq 1 60); do
    r=$(gh run list --branch "$tmp" --limit 1 --json headSha,status,conclusion --jq '.[0]|[.headSha,.status,.conclusion]|@tsv' 2>/dev/null)
    case "$r" in "$sha	completed	success") break;; "$sha	completed	"*) stop "the free test on $tmp did not pass: $r";; esac; sleep 15; done
  [ "${r%%	*}" = "$sha" ] && case "$r" in *completed*success) ;; *) stop "the free test on $tmp did not finish in time";; esac
fi
git push -q origin "HEAD:refs/heads/main" || stop "main refused the push (not a fast-forward, or not allowed); nothing was forced"
echo "== pushed $new to main"
git push -q origin ":refs/heads/$tmp" 2>/dev/null
if [ $wait = 1 ]; then
  echo "== waiting for the free test on main and the site rebuild"
  for _ in $(seq 1 60); do
    s=$(gh run list --branch main --limit 4 --json headSha,status,conclusion --jq '[.[]|select(.headSha=="'"$(git rev-parse HEAD)"'")]|map(.status+"/"+(.conclusion//""))|join(" ")' 2>/dev/null)
    case "$s" in *in_progress*|*queued*|"") sleep 15;; *failure*) stop "a run on main failed: $s";; *) break;; esac; done
  echo "== proving the new content is served (the published version, and a changed line of the site if the site changed)"
  bash scripts/live-check.sh "$new" $proof_file "$proof_line" || stop "the new content is not being served yet; run scripts/live-check.sh \"$new\" again in a few minutes"
fi
echo "SHIPPED $new"
