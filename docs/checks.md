# Muster's checks: safety stops and house rules

Every check Muster runs is on this page, in one of two groups. When a check stops a chat, its message ends with its group and its name, for example `[house rule "pick-marked" of Muster; a project's profile can switch it off]` or `[safety stop "guard": on for every project, no switch]`, so it is plain whose rule it is.

- **Safety stops** are on for every project. There is no switch. They guard money, keys and passwords, deleting, publishing and committing.
- **House rules** are about how a chat talks, asks, reports and orders. Each has its own switch per project: a project's profile (the file in `profiles/`) may carry `"house_rules": {"<name>": false}`. A house rule switched off never reaches that project: no refusal and no note. A rule not named in the profile stays as it is today.
- A **new** house rule, made after this page, starts **off** for every project but Muster until that project's manager, with the owner's yes, turns it on. (`NEW_HOUSE` in the checks; empty today.)
- A project's profile is changed only on that project's manager's request, with the owner's yes. Muster's manager never changes another project's profile alone. Which house rules PINR keeps is for the owner with Manager_PINR; `profiles/pinr.json` names none, so PINR keeps every one, as before.

Kinds: refuses = the tool call or the end of the turn is refused; note = the reply is let through and the chat is told once at its next prompt.

| Name | Group | Kind | What it checks |
| --- | --- | --- | --- |
| `guard` | safety stop | refuses | The project's own guard (item 117): protected folders and files, and which public repos may be pushed to. |
| `helper-ships` | safety stop | refuses | A helper never ships, pushes, messages other chats or talks to the owner. |
| `note-secret` | safety stop | refuses | A note in a message between chats never carries a key, password or token. |
| `usage-limit` | safety stop | refuses | At 90% of the week no new order or report goes out. |
| `muster-not-saved` | safety stop | refuses | Nothing under `muster/` is ever saved or committed. |
| `helper-stand-in` | house rule | refuses | A helper never stands in for a worker or the Inspector chat. |
| `playback` | house rule | refuses | After the owner asked for a playback, the manager answers it first. |
| `start-title` | house rule | refuses | A started chat's card title is its final name. |
| `wrapup-box` | house rule | refuses | No question or buttons in the app's wrap-up call. |
| `choice-card` | house rule | refuses | No choice card for the owner; lettered lines in the chat. |
| `no-thanks` | house rule | refuses | No "noted" or "thanks" messages between chats. |
| `record-form` | house rule | refuses | A message between chats is one data record with fixed keys. A refusal names every fault found in one answer (item 132), so the record is rewritten once. |
| `note-shape` | house rule | refuses | A record's note is one plain line of 1 to 400 characters (the program's record check carries this under `record-form`). |
| `order-action` | house rule | refuses | An ORDER names its action: ship, hold or start (the program's record check carries this under `record-form`). |
| `order-goal` | house rule | refuses | An order is checked against the project's goal. |
| `question-order` | house rule | refuses | An order in a turn the owner's question started needs his recorded choice, a decision in the log or a `Serves:` line (item 115). |
| `dup-report` | house rule | refuses | The same report is not sent twice. |
| `dup-id` | house rule | refuses | A report id already sent is dropped. |
| `report-shape` | house rule | refuses | A message between chats is a six-line report or an order (text form). |
| `memory-rules` | house rule | refuses | Crew rules are not written into memory files. |
| `protected-files` | house rule | refuses | Only the manager changes the owner's list, decisions, crew list, rules pages and `muster/CLAUDE.md`. |
| `manager-only-files` | house rule | refuses | Only the manager changes a project's manager-only files. |
| `owner-order` | house rule | refuses | An order the owner typed is done, not refused or argued with (item 76). |
| `idle-card` | house rule | refuses | When no worker holds an open order, the manager's turn ends with the idle card (item 125). |
| `file-started-chat` | house rule | refuses | A chat started this turn is filed into the project's group. |
| `record-answer` | house rule | refuses | The owner's answer to a lettered question or a choice card is recorded. |
| `pick-marked` | house rule | refuses | Every lettered question carries the manager's pick (item 100). |
| `no-send-owner` | house rule | refuses | Never send the owner to type in a worker's chat (item 103). |
| `asked-twice` | house rule | refuses | A question he has not answered is not put to him again (item 114). |
| `news-repeat` | house rule | refuses | The owner gets one line per report, not two. |
| `empty-line` | house rule | refuses | No empty "needs nothing from you" line. |
| `no-news` | house rule | refuses | No PASS, DONE or progress news to the owner (item 97). An ANSWER about a thing the owner asked to be told about ("tell me when ...", "let me know when ...", "ping me when ...") passes once, on any turn. |
| `news-with-question` | house rule | refuses | News does not ride along with a question (item 114). |
| `pictures-first` | house rule | refuses | A question about how something looks comes after the pictures. |
| `manager-says` | house rule | refuses | To the owner the manager says only a question, a yes he must give, or the idle card. An ANSWER about a thing the owner asked to be told about passes once, on any turn. |
| `report-to-manager` | house rule | refuses | A report reaches the manager as a message as well as the board (item 65). A READY is the exception in Muster: it goes to the inspector, who copies the manager (see `ready-to-inspector`). |
| `ready-to-inspector` | house rule | refuses | A builder's or designer's READY is never sent to the manager's chat; it goes to the inspector, who sends the manager its copy with the verdict, so each piece of news reaches each chat once. On in Muster by default; another project switches it on in its profile. |
| `verdict-from-inspector` | house rule | refuses | A PASS or FAIL is sent only by an inspector (or the manager); a builder's or designer's PASS or FAIL, including a relay of the inspector's, is refused. On in Muster by default. |
| `crew-records` | house rule | refuses | Several crews in one project (item 134): a crew's records live in `muster/crews/<crew>/`; a chat writes only its own crew's records, and only the main crew writes the shared ones (decisions, rules pages, `muster/CLAUDE.md`, the main board). A chat's crew is the crew whose own list (`muster/crews/<crew>/CREW.md`, "Running now") names it, by chat name, whatever the owner called it (`Shapes_MyProject`), else the crew word in its name (`Builder A Evidence_Muster`); a chat in no crew list is main crew. The lists are read live each turn. Off for a project with one crew. On in Muster by default. |
| `board-open-items` | house rule | refuses | The manager tells the owner of open board items before it stops. |
| `board-pick-claim` | house rule | refuses | The manager does not say it chose or recorded for the owner before he picked. |
| `queue-waiting` | house rule | refuses | A worker who says it waits on the manager has sent the manager a message. |
| `queue-idle` | house rule | refuses | A worker does not go idle while open work is addressed to it. |
| `idle-sweep` | house rule | refuses | The manager's crew sweep: each quiet member gets its next order. |
| `idle-silent` | house rule | refuses | The manager does not end a turn silently while a chat is idle with an open item. |
| `note-letters` | house rule | note | Choice letters are bold and italic (`***A.***`). |
| `note-heading` | house rule | note | A question to the owner opens with a bold heading line. |
| `note-badge-line` | house rule | note | A worker's news is the bold badge and one plain line. |
| `note-card` | house rule | note | A worker's end-of-turn reply is a card: bold title, two or three bullets. |
| `talk-note` | house rule | note | The owner's replies carry no bare file path or saved-version code (older switch name: `"talk_check": false`). |
| `other-computer-news` | turn-start hook | prints | Only where `muster/computers.txt` names two computers (item 133): at the start of a chat turn, the other computer's new `CHANGES.md` lines, once per chat, at most 12 lines (it says how many were left out). Reads only; never refuses or fails a turn. A Python script (`scripts/other-computer-changes.py`), no program copy. |

Not on this page, because no check carries them: rules that live on the rules pages only, for example that a worker never passes its own work. They are not switches.
