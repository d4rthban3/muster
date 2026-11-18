# Changelog

Each version names which workers it affects.

## 0.3.155
Affects: the manager and every worker.
rust-first-2-all-five: the automatic run now runs the full self-tests against the shipped program of all five systems, the older-Mac (Intel) one included; the record fuzz can print why the program refuses each odd record that the Python copy lets through (every one is a field that breaks the written record rules: wrong type, empty, unknown key, wrong id form). No program or rule changed

## 0.3.154
Affects: the manager and every worker.
rust-first-1-parity: the Rust program now answers the way the Python checks do where it differed: it finds the choice recorder and the usage script from where the plugin keeps its programs, the board check remembers what the manager was told under the same fingerprint, a profile that only names managers still knows a summary-first manager chat by its title, and a hook field or profile switch that Python reads as true or false is read the same way; four parity scripts compare the two copies. Python stays as the fallback; nothing is removed

## 0.3.153
Affects: the owner's chat (the look).
background-loads-light: the glass background is built once per chat and kept, so a redraw no longer reads the stored settings, the picture file and rebuilds the 130,000-character scene each time; the scene is applied before the /look command is registered; the picture itself is unchanged

## 0.3.152
Affects: the manager and every worker.
manager-known-by-title: a chat whose file opens with a compaction summary is now known by its own title (a title naming a crew chat, such as Manager_PINR) in the rules check, talk check, board stop, worker queue, renewal and pre-compact hooks, Python and Rust, so the ?? play-back and the refusal of ask and buttons in the wrap-up call reach it; a worker's first message that names its manager still does not make it a manager (a worker title decides)

## 0.3.151
Affects: the owner's chat (the look).
answer-box-yellow: words sent from the box under the choices are his answer (as before 0.3.150): the choices lock and the box fills yellow with his words, in every copy of the question and after a reload; words from the main message box still leave the choices live; undo clears it

## 0.3.150
Affects: the owner's chat (the look).
choices-stay-live-2: words sent from the card's own type-your-own-answer box are the owner's message and answer nothing, so the choices stay live and unfilled; only a click or a lone letter (there or in the chat box) fills and locks; an old stored typed answer is dropped so it cannot deaden the choices, and the 'Your answer' line is gone

## 0.3.149
Affects: the manager.
play-back-shortcut: when the owner's own typed message ends with two question marks (??), a prompt hook tells the manager to play back what it heard, order nothing, message no worker, start no chat and change no file, and ask one lettered yes-or-off question; the pre-tool and end-of-turn checks refuse an order, a message, a file change or a reply without the question until his yes; one ?, ?? mid-message, a peer's message and a letter pick do not trigger it; the manager page, manager-details, the crew template and the README say so

## 0.3.148
Affects: the owner's chat (the look).
choices-stay-live: only a real pick answers a question (a click then Enter, or a reply that is just one of its letters); other words the owner sends leave the choices live and unfilled; a pick fills the choice and locks the question everywhere it is drawn and after a reload; an older question stays live (its option line picks it) once a newer one appears; a locked question takes no second pick; undo still returns it to live

## 0.3.147
Affects: the manager.
idle-card-manager-only: in an installed project the idle card is asked for only in the chat whose own title names the manager; a worker whose first message names its manager no longer gets it, and a chat whose title cannot be read stays silent

## 0.3.146
Affects: the manager.
worker-news-line: on a turn a worker's message starts, the manager's reply to the owner is now a bold badge ('READY · login screen') and one plain line saying who did what, never the empty "needs nothing from you" line; the end-of-turn check allows that shape and refuses the empty line, a second news line, bullets, a saved-version code, a version number, a bare path and a repeat of a report he already had a line for; the manager page, manager-details and the crew template say so with a made-up example

## 0.3.145
Affects: the manager.
idle-card-when-changed: the manager's idle card is asked for only when something changed since its last one: a new owner message, a new report, a ship or a board change; background, other-chat and repeat-report turns with nothing new pass without it; a first card, or a transcript that cannot be read, is still asked for

## 0.3.144
Affects: the owner's chat (the look).
choice-click-whole-row-2: the press region of a lettered option now takes its line count from the card (a generous estimate of the wrapped lines, clipped to the row) instead of its own height, so every line of a wrapped choice, the gaps and the padding take the press; hover and fill unchanged

## 0.3.140
Affects: the owner's chat (the look).
choice-click-whole-row: the press region of a lettered option is now as tall as the whole highlight (one blank line per laid-out row), so a wrapped choice, the gaps between its lines and the padding all take the press, not only the first line; hover and fill unchanged

## 0.3.142
Affects: every worker.
compact-at-250k: every crew chat now compacts in place at 250k tokens (was 200k for workers, 250k for the manager): worker pages, the before-compact note, crew-plan trim default and both profiles. Sonnet 5.5 runs a 1M window, so 250k is reached unless CLAUDE_CODE_DISABLE_1M_CONTEXT is set.

## 0.3.139
Affects: the manager, builders and inspectors.
order-acceptance-contract-risks: every order now carries an Accept line (what counts as passed, in his words) that the inspector reads one by one; a Contract line for a hand-off between workers (what is handed over and its shape); and one risk page, muster/RISKS.md (owner, what would go wrong, what closes it), kept by the manager. The end-of-turn check refuses a To/Job order with no filled Accept line, and an empty Contract line; a Contract line may be left out when nothing is handed over

## 0.3.138
Affects: the owner's chat (the look).
choice-click-area: the whole highlighted row of a lettered option takes the press: the click region is painted almost clear and set to full width and height, so no strip of the highlight is dead; hover and fill unchanged; nothing else visible changes

## 0.3.137
Affects: the owner's chat (the look).
pick-name-every-chat: the project's name is now read in every kind of chat: a worktree copy found even when git does not answer (the folders above are walked five up, not two), names with accents kept whole, a name read from a compacted chat's summary, and the other crew roles listed in the crew file; a folder with no crew keeps (Claude pick)

## 0.3.136
Affects: the owner's chat (the look).
fast-cards: a card redraw waits on nothing: the project name, look settings and saved picks are read once per chat and kept (updated on this chat's own save or setting change), and the conversation is read once per new message, and again by the next redraw once the kept copy is 1.5 seconds old (so a rewind unpicks at once), one read for all cards, not one per card; nothing visible changes

## 0.3.135
Affects: the owner's chat (the look).
pick-marker-back: a click's filled text always keeps the pick marker, '(<project> pick)' or '(Claude pick)' with no name, and a marker with a reason keeps the reason; the project name is also read from the chat's own first message

## 0.3.134
Affects: Manager.
idle-card-required: when no worker holds an open order on the board, the manager's turn must end with the idle card or a Working line, even with no text

## 0.3.133
Affects: see .claude-plugin/releases/0.3.133.json.
pick-fallback: when no project name can be read, a click fills the option text with the (my pick) marker left out; never a folder or remote name

## 0.3.132
Affects: see .claude-plugin/releases/0.3.132.json.
badge-position: the Working and Idle badges sit where a card's title badge sits, on their own line with clear air above, and the rest of the line is laid out below like card text

## 0.3.131
Affects: see .claude-plugin/releases/0.3.131.json.
fill-pick-name: when a click fills the chat box, the option's (my pick) reads (<project name> pick), for example (Muster pick); the card itself is unchanged

## 0.3.130
Affects: see .claude-plugin/releases/0.3.130.json.
working-badge: a reply line starting Working: shows a Working badge, and one starting The crew is idle shows an Idle badge, in the ORDER title badge colour; the rest of the line stays plain text

## 0.3.129
Affects: Manager.
idle-needs-choices: the manager's reply check refuses a bare 'The crew is idle'; the idle card must carry at least two lettered next steps

## 0.3.128
Affects: see .claude-plugin/releases/0.3.128.json.
click-whole-row and click-fill: a press on a choice row lights it at once and the whole row is the click target; a click puts that option's full text in the chat box (prompt.fill) and sends nothing, the owner presses Enter

## 0.3.127
Affects: see .claude-plugin/releases/0.3.127.json.
ship-mod-version: version-check refuses a changed second plugin (a mod) whose version stayed and ship.sh raises it; publish-only now stops with a clear line when the folder changed after the version GitHub holds

## 0.3.126
Affects: Manager.
working-status-line: while the crew works and nothing needs the owner, the manager may end with one status line naming who works on what

## 0.3.125
Affects: see .claude-plugin/releases/0.3.125.json.
a click on a card drawn while its question was still streaming now sends the finished question text

## 0.3.124
Affects: see .claude-plugin/releases/0.3.124.json.
the look is folded into the main plugin (look/ with the click-live fixes); the separate look plugin is removed

## 0.3.123
Affects: see .claude-plugin/releases/0.3.123.json.
ask once: waiting questions are not re-asked

## 0.3.122
Affects: see .claude-plugin/releases/0.3.122.json.
click sends only the option text

## 0.3.121
Affects: see .claude-plugin/releases/0.3.121.json.
compact: managers 250K, workers 200K

## 0.3.120
Affects: see .claude-plugin/releases/0.3.120.json.
Smoother glass background, and one look per project crew

## 0.3.119
Affects: see .claude-plugin/releases/0.3.119.json.
Glass background settings stay with their own group

## 0.3.118
Affects: see .claude-plugin/releases/0.3.118.json.
Choice clicks answer at once, follow a rewind, and each names its own question

## 0.3.117
Affects: see .claude-plugin/releases/0.3.117.json.
Optional glass background: two soft glows, adjustable in the look settings

## 0.3.116
Affects: see .claude-plugin/releases/0.3.116.json.
Heading chips get a clear gap above them after text or a list

## 0.3.115
Affects: see .claude-plugin/releases/0.3.115.json.
One-line questions: every letter gets its own clickable circle

## 0.3.114
Affects: see .claude-plugin/releases/0.3.114.json.
Look fixes: choice gap, even circles, picked choice stays, colour code box left, pill colours, cleaner look page, own-answer box, dead clicks

## 0.3.113
Affects: see .claude-plugin/releases/0.3.113.json.
no-next-step-box: Muster chats ask only with Muster choices (item 119)

## 0.3.112
Affects: see .claude-plugin/releases/0.3.112.json.
look-settings: per-group colour pickers with live samples (item 118)

## 0.3.111
Affects: see .claude-plugin/releases/0.3.111.json.
plugin-live: keep Muster live in every chat (item 117)

## 0.3.110
Affects: see .claude-plugin/releases/0.3.110.json.
Choice chips: whole perfect circles, centred letter, purple hover fill (item 118)

## 0.3.109
Affects: see .claude-plugin/releases/0.3.109.json.
Guard reads a project's own profile guard too, so PINR's protected folders block (item 117)

## 0.3.108
Affects: see .claude-plugin/releases/0.3.108.json.
Muster look 0.2.0: picker, balanced and clickable choices, even gaps reach installs (item 118)

## 0.3.107
Affects: see .claude-plugin/releases/0.3.107.json.
Even gaps under the title and above the first choice; left line ends at the last choice (item 118)

## 0.3.106
Affects: see .claude-plugin/releases/0.3.106.json.
Clickable choices: clicking a choice chip or row sends that letter (item 118)

## 0.3.105
Affects: see .claude-plugin/releases/0.3.105.json.
Choice chips balanced: one chip width, even row spacing, left line sized to the real rows (item 118)

## 0.3.104
Affects: see .claude-plugin/releases/0.3.104.json.
Look picker: font dropdown with Other, colour swatches with hue bar, live chip preview (item 118)

## 0.3.103
Affects: see .claude-plugin/releases/0.3.103.json.
Look mod comes with the normal Muster install; Change your look help and portable style block (item 118)

## 0.3.102
Affects: see .claude-plugin/releases/0.3.102.json.
Muster look mod: Pump-style chips in Anthropic Sans, yellow-to-purple left line, user font and colour settings (item 116)

## 0.3.101
Affects: see .claude-plugin/releases/0.3.101.json.
Blocking hooks: guard against git reset/stash in protected folders, key leaks, and pushes to non-allowed public repos (item 117)

## 0.3.100
Affects: see .claude-plugin/releases/0.3.100.json.
Item 116: chips with a clean thin border like the launchpad filters; one unbroken left rule that stops at the question's end

## 0.3.99
Affects: see .claude-plugin/releases/0.3.99.json.
Item 116: Muster look mod (smaller chips, mixed-case headings, thin left rule on questions) and a tracked top-level CHECKS.md

## 0.3.98
Affects: see .claude-plugin/releases/0.3.98.json.
Item 115: a question from the owner gets an answer; orders from his question are blocked unless they cite his choice

## 0.3.97
Affects: see .claude-plugin/releases/0.3.97.json.
PINR rule 21: decide-pinr.py says the founder, never he/him/his

## 0.3.96
Affects: see .claude-plugin/releases/0.3.96.json.
Item 114: the manager speaks to the owner after a worker's message only for a new question or a blocker; repeated questions blocked

## 0.3.95
Affects: see .claude-plugin/releases/0.3.95.json.
Compact at 200k (D-041): chats compact in place at 200k

## 0.3.94
Affects: see .claude-plugin/releases/0.3.94.json.
Manager after compact (item 112): a manager keeps its rights after its chat compacts

## 0.3.93
Affects: see .claude-plugin/releases/0.3.93.json.
Phone menu (item 7): a Menu button at the top right of every page on a phone

## 0.3.92
Affects: see .claude-plugin/releases/0.3.92.json.
Memory rule check (item 108, D-027): a crew chat cannot write crew rules into its own memory

## 0.3.91
Affects: see .claude-plugin/releases/0.3.91.json.
Slim it all (D-040, items 106-108): no renewal or handover code, names without numbers, ask before choosing how, no crew rules in a chat's own memory

## 0.3.90
Affects: see .claude-plugin/releases/0.3.90.json.
Compact in place (D-039, item 105): no size renewals; chats compact at 300k and write their open job to the board first

## 0.3.89
Affects: see .claude-plugin/releases/0.3.89.json.
Approval relay (items 103, 104): the manager carries his yes to the worker, idle card once per idle stretch, ship.sh skips a needless rebase

## 0.3.88
Affects: see .claude-plugin/releases/0.3.88.json.
Handover quiet (items 95, 101): idle card once, old manager goes quiet, reports go to the manager in force

## 0.3.87
Affects: see .claude-plugin/releases/0.3.87.json.
Renew line 300k and trimmed start load (item 102): renew at 300k; crew chats start without unused tools

## 0.3.86
Affects: see .claude-plugin/releases/0.3.86.json.
Always your pick (item 100): the manager's reply check refuses lettered choices with no marked pick

## 0.3.85
Affects: see .claude-plugin/releases/0.3.85.json.
Renew by size: any crew chat over the size line renews; crew names from the profile (item 99)

## 0.3.84
Affects: see .claude-plugin/releases/0.3.84.json.
Quiet manager: silent end after a worker message, no news to the owner, no repeated reports (item 97)

## 0.3.83
Affects: see .claude-plugin/releases/0.3.83.json.
Idle report card and daily crew sweep (items 95, 96)

## 0.3.82
Affects: see .claude-plugin/releases/0.3.82.json.
Muster crew runs its checks live from the Muster folder; checks find the current manager (items 93, 94)

## 0.3.81
Affects: Builder, Designer, Manager.
Ship blocked: a worker whose push the app refuses for the owner's yes never asks him; it sends the manager a NEED and the manager asks in his own chat and runs ship.sh

## 0.3.80
Affects: Manager.
Letters are the question: two or more lettered choice lines count as the manager's question with or without a question mark

## 0.3.79
Affects: see .claude-plugin/releases/0.3.79.json.
Report check also accepts the app's send_message tool (item 65 follow-up)

## 0.3.78
Affects: Manager, Builder, Inspector, Designer.
Group check (item 79): the manager's stop refuses a started chat with no move_sessions and list_sessions read-back. Report to manager always (item 65): PASS/FAIL copies to the manager are allowed and a worker's report card needs a message to the manager

## 0.3.77
Affects: Manager.
Pictures first only for looks (item 88): the check reads only the sentences that end in a question mark and skips lettered choice lines, so layout or look in a list or choice no longer fires; a real look question still blocks

## 0.3.76
Affects: Manager, Builder.
Live checks: install-checks --live runs the checks and PINR's recorder from the Muster folder; ship moves the main folder to the new main

## 0.3.75
Affects: Manager, Builder.
Setup lettered: every question setup asks is lettered lines, never a choice card or buttons

## 0.3.74
Affects: Designer.
Tidy folder: muster-icon.png moves into brand/

## 0.3.73
Affects: Manager, Builder.
Answer his question: a reply to a question of his without a question mark passes; pictures-first fires only on on-screen look questions

## 0.3.72
Affects: Manager, Builder.
No repeat after a stop: every Stop-check block says the reply already reached the owner and must not be written again

## 0.3.71
Affects: Manager, Builder.
PINR's decide.py: his typed letter and a handover line are recorded; install-checks --profile pinr installs it

## 0.3.70
Affects: Manager.
No repeat: an open item, a waiting chat or a hold is said once and a worker's next message ends silent when unchanged; decide.py reads his typed letter

## 0.3.69
Affects: Manager, Builder, Designer, Inspector.
No locking card: questions to the owner are lettered lines with bold-italic letters he answers by typing; the manager's choice card is refused; a typed letter must be recorded

## 0.3.68
Affects: Manager.
Manager name: the rules check sees a PINR manager whose start note reads 'Job: You are Manager_PINR_N' (Python and Rust copies, programs rebuilt)

## 0.3.67
Affects: manager.
Start title: a started chat's card title is its final name; the check refuses a Start prefix

## 0.3.66
Affects: manager, builder, designer, inspector.
Founder orders: a coded rule, the manager cannot refuse, argue with or reinterpret an order he typed

## 0.3.65
Affects: Manager.
No filler: a short routine reply to another chat's message is not bounced for wording (Python and Rust copies, programs rebuilt)

## 0.3.64
Affects: Manager, Builder, Designer, Inspector.
No hold above his word: manager page line; the manager's stop flags a hold that names no decision or item of his

## 0.3.63
Affects: Manager, Builder, Designer, Inspector.
Manager-wait: a worker may not end a turn waiting on the manager with nothing sent; the manager's stop names chats that wait on him

## 0.3.62
Affects: Builder, Designer, Inspector.
Queue check --list: say what to give when --worker is missing, with a self-test

## 0.3.61
Affects: Builder, Designer, Inspector.
Worker queue check reads PINR's line-style board and is installed there by install-checks.py

## 0.3.60
Affects: Builder, Designer, Inspector.
Worker queue check: a Stop hook refuses a worker's idle stop while open work is addressed to it

## 0.3.59
Affects: manager, builder, designer, inspector.
Show first: a question about how something looks needs the pictures shown in the same turn

## 0.3.58
Affects: Manager.
Idle-crew check: a Stop hook refuses a silent manager stop while an idle chat has an open item

## 0.3.57
Affects: manager, builder, designer, inspector.
Stop check fix: once per turn, plain answers pass, routed items handled, no-pick record

## 0.3.56
Affects: manager, builder, designer, inspector.
Note field: any record may carry one plain-text note, 400 characters, no key or password

## 0.3.55
Affects: manager, builder, designer, inspector.
Ready package: ship script wording, leak scan skips diff headers, directory edition checks every review rule, resubmit routine

## 0.3.54
Affects: manager, builder, designer, inspector.
Directory edition: Markdown, JSON and image only copy for the plugin directory review

## 0.3.53
Affects: manager, builder, designer, inspector.
Order action field

## 0.3.52
Affects: manager, builder, designer, inspector.
Helpers in each chat

## 0.3.51
Affects: Manager, Builder, Designer, Inspector.
weekly goal: the owner names one goal and when it is done; the manager records the set list and the parked work; off-list orders wait with his words, and he can change or drop it any time

## 0.3.50
Affects: Manager, Builder, Designer, Inspector.
lean rebuild: checks in Rust with ready-made programs for five systems, one page per worker, messages between chats as data records with set lists only

## 0.3.49
Affects: Manager, Builder, Designer, Inspector.
accented project names (D-011): manager names with accents are read, hooks read UTF-8 input, printing never fails on a console encoding, and the free test covers Pâtisserie

## 0.3.48
Affects: Manager, Builder, Designer, Inspector.
manager test: a chat is the manager only by its own name (Job, You are, I am), so workers that mention the manager are no longer held to the manager's reply rule

## 0.3.47
Affects: Manager, Builder, Designer, Inspector.
PINR guard: a worker's shell write into PINR's manager-only files is denied, as for Muster's files

## 0.3.46
Affects: Manager, Builder, Designer, Inspector.
PINR check gaps: social-only messages refused; the profile carries PINR's manager-only paths

## 0.3.45
Affects: Manager, Builder, Designer, Inspector.
message checks: a refused or pending send keeps its ID; a manager's direct answer to his typed question passes in the turn he started

## 0.3.44
Affects: Manager, Builder, Designer, Inspector.
PINR install fixes: board path from the folder holding .muster-checks; the plugin's hooks stand down where a project has its own copy

## 0.3.43
Affects: Manager, Builder, Designer, Inspector.
project profile for the coded checks (PINR): chat names, report shape, decide.py, board path, no second talk check

## 0.3.42
Affects: Manager, Builder.
Version number only (owner's list item 31, owner: "Bump to 0.3.42"): no other change from 0.3.41.

## 0.3.41
Affects: Manager, Builder.
Computer 2 in step (owner's list item 31, owner: "i need computer 2 to be informed of the protocol and to stay in step with our builders"): the second computer's join, run there, sets itself up from the shared files, takes the project's board, rules, protocol page, builders' log and workspace paths as options, can be dry-run, and writes nothing in the host's files; a protocol page and a builders' change log are kept with the crew files (ship.sh adds a line at each ship, the manager adds ready-but-not-live work), and the second computer reads both before every session.

## 0.3.40
Affects: Manager, Builder, Designer, Inspector (Claude Code and Cursor).
Crew chats open detached and filed in the project group as a required, checked step (D-026); every rule a script can check is enforced by code (D-027, owner: "code every rule"): chat messages, replies, recorded choices, who may write the shared files, the usage block, and shipping only with the inspector's PASS; a check script and plain page wording for the Cursor, Grok Bot and ChatGPT editions; projects without the plugin install the checks with scripts/install-checks.py.

## 0.3.39
Affects: Manager.
The start-the-crew text now says an inspector may work in the main folder or in its own copy; either works.

## 0.3.38
Affects: Manager, Builder, Inspector.
Four scaling changes (D-025): one inspector for every three builders, started and archived automatically; small checks run as a fresh checker inside the manager's chat while big pieces go to an inspector chat; a renewed chat gets its own new copy named for its role; finished board entries move to the archive by themselves. The owner picked all four after asking what to improve in Muster itself.

## 0.3.37
Affects: Designer.
Pointer glow: a deep purple spotlight follows the mouse or finger behind the cards, shown only after the first move (site and setup page)

## 0.3.36
Affects: Designer.
Remove the haze: no glow layer, solid header, no blur, full-colour divider dots (site and setup page)

## 0.3.35
Affects: Cursor users reading Muster Lite.
Cursor is no longer listed under Muster Lite: Lite's table now points Cursor users to the full-crew Cursor guide (the owner chose the full crew for Cursor).

## 0.3.34
Affects: Designer.
Install page: Cursor gets its own full-crew card and leaves the Muster Lite picker (untested)

## 0.3.33
Affects: Designer.
Cursor guide: second computer join steps; copy-block wrap in style.css (untested)

## 0.3.32
Affects: Manager, Builder, Designer, Inspector (a new section 9c in the core rules; applies only to projects with a second computer).
Two founder computers: the Cursor edition can join a project that already has muster/ as a second computer (setup.py --join) without writing in the host's files, with its own workspace, change log, git name and branches, and the two-computer rules in the core rules. The owner: "computer 2 is connected to the files themselves... i want it integrated."

## 0.3.31
Affects: Designer.
Cursor guide: plain-words page, Cursor column in the compatibility table, link on the install page (untested)

## 0.3.30
Affects: nobody; only Muster's own free test.
The free test no longer fails when it reads the published version just as a new one goes live: it reads it again and retries.

## 0.3.29
Affects: nobody on Claude Code; Cursor users only.
Muster for Cursor, full crew (untested in Cursor): cursor/setup.py builds the crew (manager, builder, designer, inspector) as separate Cursor agents in their own copies, with Muster's rules as Cursor rules, the same board and owner's list, and a manager Stop check. The owner: "computer 2 is on cursor and needs muster catered to it."

## 0.3.28
Affects: Manager, Builder, Designer, Inspector.
The talking rules are locked in: a short "How to talk to the owner" block at the top of the crew rules, put back by a hook after every summary, and a light check that flags once a crew reply with a bare file path or saved-version code. The owner: "its reverting back to claude style conversation and not locking in muster communication rules."

## 0.3.27
Affects: Manager, Builder, Designer, Inspector.
Four usage savers (D-023): no "noted" replies and the inspector's copies go to the board only; the inspector re-runs only changed tests plus one full run, one dark and one light picture; a hook reminds a chat to hand over and renew right after its conversation is summarized; passed site branches ship in one batch (ship.sh --with), jobs wait for the owner's notes, and read-only data is read directly. The owner picked all four.

## 0.3.26
Affects: Manager, Builder, Designer, Inspector.
A paused chat clears when it resumes (D-020): a worker closes its own "Paused: yes" entries as its first act after the owner types in it, and the board digest and Stop hook count a chat paused only while its last board entry says so; a worker that cannot write the main board leaves a .muster-paused file the hook reads. The owner (via PINR): "im tired of this happening. i dont know why its happening but get with muster manager an fix the hole".

## 0.3.25
Affects: Manager.
A manager never picks for the owner (D-022): decisions are written only by scripts/decide.py, which needs his recorded click or his own words naming the choice, and the Stop hook blocks a manager turn that says it is choosing or recording for him with no choice card answered. The owner: "the ill go ahead with it even though you didnt pick an option in a click box."

## 0.3.24
Affects: Manager.
A Stop hook in the plugin makes the manager's board check enforced, not remembered: it blocks the manager from stopping while a paused chat or an open NEED, STUCK or OWNER CALL sits on the board unnamed. The owner: "engine paused and i didnt get a queue with click box".

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
