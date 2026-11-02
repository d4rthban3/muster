---
name: start-the-crew
description: How to start the crew's chats (manager, builders, designer, inspector, outside helpers) in Claude Code. Use when setting up a project, adding a builder, or renewing a long chat. Covers one chat per role, how to give each its role, and handover.
---

# start-the-crew

## One chat per role
Open a separate Claude Code chat for each role (manager, builder A, inspector; add builders as needed). Each chat runs
in the same project folder (or its own git worktree if two builders edit at once).

## Starting a role
1. In the new chat, run `/muster:role <role>` (manager, builder, inspector, helper). It loads that role's rules, tells it
   what it owns and does not touch, and has it read the board.
2. Alternatively, in a terminal: `claude --agent muster:<role>` starts the session with that role's agent definition.
3. Give the manager the owner's goal; the manager writes orders (skill `one-order-per-piece`).
4. Keep `muster/CREW.md`'s roster table current: role, chat, model, branch.

## Isolation
Two builders at once → `git worktree add ../<name> -b builder/<name>` per builder, and files must not overlap.

## Outside helpers
Another AI chat or contractor gets a public or exported copy, never keys or private files. What comes back is a lead:
the manager checks it before it becomes an order.

## Renewing a long chat
At a natural break the chat writes a handover note (see `usage-habits`, habit 7), posts one board line, and the manager
starts a fresh chat for the role.
