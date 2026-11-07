---
name: deploy-rules
description: How a builder or designer deploys its own work safely. Use before any deploy or release step. Front-end/site work may be merged and deployed by its own builder after a dry run; engine, data or back-end changes never are. Covers the lock, the dry run, and deploying from a fresh clone.
---

# deploy-rules

For a branch the inspector passed, `scripts/ship.sh` does the version, release file, changelog, checks, push and waiting in one command; the steps below are what it replaces.

## Who deploys what
- **Site / front-end work** (what people see): its own builder or designer may merge and deploy it, after the dry run
  below and after the two checks (skill `ready-checks`). The inspector reads it live afterwards.
- **Engine, data, database or back-end changes**: never deployed by the builder. They go to the inspector first; the
  manager orders the deploy once the inspector has read them.
- Edit this split in `muster/DECISIONS-LOG.md` if your project draws the line elsewhere; the log wins.

## Steps
1. **Dry run first.** Your project's deploy command must have a mode that shows what it would do and changes nothing.
   Read the output. Stop if it lists anything you did not intend.
2. **Take the lock** so two deploys cannot overlap, and **deploy from a fresh clone**, never from a working copy:
   ```
   bash "${CLAUDE_PLUGIN_ROOT}/skills/deploy-rules/scripts/fresh_clone.sh" <repo> <ref> <dir>
   cd <dir>
   bash "${CLAUDE_PLUGIN_ROOT}/skills/deploy-rules/scripts/with_lock.sh" site <your deploy command>
   ```
   If it prints `LOCKED` (exit 75), another deploy is running: wait and rerun. Do not delete the lock by hand; a lock
   whose process is gone is cleared automatically.
3. **Check what else is waiting before any push** (skill `held-work`).
4. **Verify live**: fetch the live page or asset yourself and confirm the change is there before saying "live".
5. Tell the manager in one message: what, where, how it was checked.

## Do not
- Deploy engine or data changes.
- Deploy from a dirty working copy, or without the dry run.
- Say "live" without having looked at the live thing.
