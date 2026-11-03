---
description: Take on a Muster worker's job in this chat, if it was not started by the setup
argument-hint: Manager_<project>_001 | Builder A_<project>_001 | Designer_<project>_001 | Inspector_<project>_001 | ...
---

You are taking the job: **$ARGUMENTS**.

1. If no name was given, ask which worker (one question naming the workers in `muster/CREW.md`, each a button).
2. Read your definition in `${CLAUDE_PLUGIN_ROOT}/agents/` (manager, builder, designer, inspector, design-inspector,
   sketchpad, ai-socket, agent-teacher) and follow it for the rest of this chat.
3. Read `muster/CLAUDE.md` in the main project folder and your rules page in `muster/rules/`. Not the whole decisions log.
4. Run skill `board-digest` with your name, then wait for an order from the manager.
