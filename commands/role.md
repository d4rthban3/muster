---
description: Take on a crew role in this chat (manager, builder, designer, inspector, helper) and read the board
argument-hint: manager | builder | designer | inspector | helper
---

You are taking the role: **$ARGUMENTS**.

1. If no role was given, ask which of manager, builder, designer, inspector, helper.
2. Read `CLAUDE.md` and `muster/CREW.md`. Read your role's definition: `${CLAUDE_PLUGIN_ROOT}/agents/<role>.md`
   (helper → `outside-helper.md`). Follow it for the rest of this chat.
3. Read the decisions log to the end, then run the `board-digest` skill with your role name.
4. Say in two lines: your role, what you own, and the open entries addressed to you. Then wait for an order, or act
   on one already on the board.
