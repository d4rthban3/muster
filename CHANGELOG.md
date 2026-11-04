# Changelog

Each version names which workers it affects.

## 0.3.11
Affects: everyone who visits the site or the setup page (the owner's redesign of the install page and the three guide pages, and the new Muster logo in the site's header, favicon, home-screen icon and share card, and in the setup page's header and favicon). The crew itself is unchanged.
Owner's words: "site update in and make sure the plugin itself and the domain carry the logo image." (D-017)

## 0.3.10
Affects: whoever pushes a site with SVG pictures (the leak scan now allows the standard SVG namespace, www.w3.org; nothing else changes).
Owner's words: "site update in and make sure the plugin itself and the domain carry the logo image." (D-017)

## 0.3.9
Affects: the manager (runs `scripts/muster-update.py` to bring a project's copied crew files up to a new version; gets one note per affected worker to pass on); every project already set up (its muster/ rule files can now be updated without touching its records). Each version now has a manifest in .claude-plugin/releases/ (changed files, affected roles, affected platforms, whether records change).
Also: the free test now plays a pretend order, READY and PASS on a scratch project (scripts/check-report.py) and runs the update on it; it fails if any of that breaks.
Owner's words: "see both, update, and get it live within our weekly usage limit." (D-015)

## 0.3.8
Affects: the manager (its definition is now a short "Manager checklist", 3.5 KB instead of 12 KB, read every turn; the full rules moved unchanged to skill manager-details, read only when needed; keeps muster/LOOK-BOOK.md); the designer and the design inspector (read muster/LOOK-BOOK.md for the owner's approved looks); setup (copies the look book into new projects).
Owner's words: "see both, update, and get it live within our weekly usage limit." (D-015)

## 0.3.7
Affects: people who use Muster in ChatGPT or Grok Bot (the guides and the Grok Bot profile now list the inspector's third answer, OWNER CALL); the Claude Code crew is unchanged.
Owner's words: "inspector gets a third answer, OWNER CALL, for taste questions" (D-015)

## 0.3.5
Affects: people who use Muster in ChatGPT or Grok Bot (new guide pages and a compatibility table, all marked untested; platform profile files in platforms/); the install page (one link line). The Claude Code crew itself is unchanged.
Owner's words: "all" (D-015), on the ChatGPT and Grok Bot editions.

## 0.3.7
Affects: the manager (a short "Manager checklist" at the top of its definition, linking to the unchanged details; keeps muster/LOOK-BOOK.md); the designer and the design inspector (read muster/LOOK-BOOK.md for the owner's approved looks); setup (copies the look book into new projects).
Owner's words: "see both, update, and get it live within our weekly usage limit." (D-015)

## 0.3.6
Affects: every worker (reports carry a short ID; a repeat is dropped; READY shows the exact test command with pass and fail counts; a builder names any new test file; a chat with no job in progress writes no handover); the inspector (a third answer, OWNER CALL); the manager (turns each OWNER CALL into a question; the board digest reads as Manager with no name and prints a "Waiting on:" line, and with --write-waiting keeps that one line at the top of BOARD.md).
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
