---
name: held-work
description: Keep held work off the shared main line and check what else is waiting before any push. Use whenever work is finished but must not go out yet, and before every push or deploy. Prevents held commits riding out on another chat's push.
---

# held-work

**The slip this prevents:** commits that were meant to be held sat on the shared main line, and another chat's push
sent them out with its own.

## Rules
1. **Held work stays on a branch**, never on the shared main line. If a piece is finished but must wait (an inspector's
   read, an owner's yes, a release window), it lives on `builder/<name>`.
2. **Merge to main only what is going out now.** Nothing waiting rides on main.
3. **Before any push, look at what is waiting:**
   ```
   bash "${CLAUDE_PLUGIN_ROOT}/skills/held-work/scripts/push_check.sh" <commits-you-expect-to-push>
   ```
   It lists every commit the push would send, every other branch with unpushed work, and uncommitted files. It exits 1
   when the count is not what you expected. Then find the extra commits (yours? someone's held work?) before pushing.
   It also stops (exit 1) if the push would carry anything in `muster/`: the crew's files stay on this computer only.
4. **Deploys come from a fresh clone** (skill `deploy-rules`), so a stray local commit cannot ride along.
5. Push your branch too, so held work is saved; held is not the same as unsaved.
6. If held commits do land on main by mistake, tell the manager at once; do not rewrite shared history on your own.
7. **Never rewrite someone else's held branch.** The manager never rebases, resets or force-pushes a worker's held
   branch; only the worker who owns it changes it (owner, D-013).
