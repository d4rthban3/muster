# Changelog

Each version names which workers it affects.

## 0.3.5
Affects: people who use Muster in ChatGPT or Grok Bot (new guide pages and a compatibility table, all marked untested; platform profile files in platforms/); the install page (one link line). The Claude Code crew itself is unchanged.
Owner's words: "all" (D-015), on the ChatGPT and Grok Bot editions.

## 0.3.6
Affects: every worker (reports carry a short ID; a repeat is dropped; READY shows the exact test command with pass and fail counts; a builder names any new test file; a chat with no job in progress writes no handover); the inspector (a third answer, OWNER CALL); the manager (turns each OWNER CALL into a question; the board digest reads as Manager with no name and prints a "Waiting on:" line).
Scripts: scripts/check-tests.py (test files on disk must be in muster/CHECKS.md), run in the free test.
Owner's words: "see both, update, and get it live within our weekly usage limit." (D-015)

## 0.3.4
Affects: the manager (rule notes bundled; board read on demand; never rewrites a worker's held branch); every worker
(woken only for an order, READY, PASS, FAIL, STUCK or NEED; board checked at start, before a session ends, and when
a report is on the board).
Owner's words: "Bundled rule notes, wake only when a worker must act, board check on demand, a version note naming who is affected, never rewrite a worker's held work." (D-013, wake list by D-014)

## 0.3.3
Affects: anyone running setup (Windows, Mac and Linux tested by a free GitHub test; Python found by its working name; missing git or Python installed by Claude).

## 0.3.2
Affects: new users (install and setup page wording).
