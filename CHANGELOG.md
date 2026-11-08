# Changelog

Each version names which workers it affects.

## 0.3.23
Affects: Manager, Builder, Designer, Inspector.
The manager tells the owner only a question, a yes he must give, "<worker> is waiting for you: type in <chat>", or that the crew is idle; each worker posts its own update as a short card in its own window (D-021). The owner: "i only need the manager to tell me what it needs from me."

## 0.3.22
Affects: Manager, Builder, Designer, Inspector.
Paused chats reach the owner (D-020): a paused worker writes its board report with "Paused: yes" and sends the owner a notification; the board digest prints OWNER QUESTIONS and names a paused chat as "waiting for you: type in <chat>"; the manager asks the owner the top one before ending any turn. The owner: "engine paused and i didnt get a queue with click box".

## 0.3.21
Affects: every builder and the designer (when they ship with scripts/ship.sh it now proves the NEW content is served, not only that the page answers: the published plugin.json version, and a changed line of the live page if the site changed, retrying until both match or about ten minutes pass).
Owner's words: "A. ...picks the next free version number, writes the release note, runs every check, uploads, waits for the site to rebuild and confirms it's live." (D-019)

## 0.3.20
Affects: the manager (starts Builder B only when two open pieces touch different files, and archives it automatically when its work has run out; the rule and the overlap test are in skill start-the-crew and the manager's checklist).
Owner's words: "D. Two builders when the work allows. Builder B is started only when two pieces touch different files, and stopped when the work runs out." (D-019)

## 0.3.19
Affects: every worker (a DONE or READY carries a seventh Usage line from scripts/usage.py; nothing is invented when a figure cannot be read); the manager (pauses the crew and tells the owner what is left when the week is at 90% or more); setup (one new question, with two buttons, to turn on the status line that saves usage).
Owner's words: "E. A usage meter. Each job reports roughly what it cost, and the crew pauses itself, saying what's left, before your weekly limit." (D-019)

## 0.3.18
Affects: the manager (records every choice the owner makes word for word under his list item with scripts/record-choice.py; reads the open "Report a snag" issues at a session's start with scripts/snags and turns each into a list item and an order).
Owner's words: "B. Your choices recorded automatically. When you click a button, your exact words and the option's text go straight onto your list." (D-019)

## 0.3.17
Affects: Builder, Designer.
One-command shipping: scripts/ship.sh takes main's version plus one, writes the release file and changelog, runs the checks, pushes without forcing and waits for the site

## 0.3.16
Affects: the inspector (reads one green free-test run instead of repeating the leak scan, plugin check and test-file check); every builder and the designer (their READY is judged on that run). The leak scan now looks at the branch's own history only.
Owner's words: "C. Checks moved onto GitHub's free test computers. The leak scan, the plugin check and the report checker run on every change, so the inspector reads one green result instead of repeating them." (D-019)

## 0.3.15
Affects: anyone doing a first run in the Claude desktop app (a one-page checklist on the site, linked from the install page, with a "Report a snag" button that opens a short GitHub form); the crew itself is unchanged.
Owner's words: "F. Your desktop run, made easy. A one-page checklist, plus a "report a snag" button that turns anything confusing into a fix." (D-019)

## 0.3.14
Affects: everyone using Muster Lite (every route on the install page now has the AI read Muster Lite from Muster's live GitHub page each time, so nothing is added to a project and it updates by itself; adding the file to a repository is a one-line option; the paste route stays for an AI that cannot open web addresses); everyone running setup (one new question, with two buttons, to keep Muster up to date by itself). No worker is affected.
Owner's words: "it should just read the active repository (users shouldnt have to set up their own repo unless they want to) and muster should automatically update for users when we update the github." (D-018)

## 0.3.13
Affects: anyone who installs or reads about the plugin (the plugin now carries the Muster logo in its manifest and the README shows it at the top); no worker is affected. The marketplace file has no icon field in Claude Code, so only the plugin carries it.
Owner's words: "make sure the plugin itself and the domain carry the logo image." (D-017)

## 0.3.12
Affects: every worker and the manager (a short "Usage first" rule at the top of muster/CLAUDE.md, pointed to by a line at the top of every agent definition; usage-habits and spend-diligence now overlap less).
Owner's words: "whatever you just did to be hyper vigilant with conserving my usage... that needs to be at the core of muster." (D-016)

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
