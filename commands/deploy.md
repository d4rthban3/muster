---
description: Builder/designer: deploy your own site work safely (dry run, lock, fresh clone, push check, verify live)
argument-hint: <branch or piece>
---

Use the `deploy-rules` skill for: $ARGUMENTS.
First decide: is this site / front-end work only? If it touches engine, data or back-end code, stop and say it goes to
the inspector first; do not deploy. Otherwise follow the skill's steps in order and stop at the first failure.
