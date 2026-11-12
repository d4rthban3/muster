**Talk to the owner (first).** Each turn ends with his card: a bold title `WORD · job`, then two or three `- ` bullets (what; the result, real numbers; what is left or needed). Plain words, every file a clickable link, no saved-version codes. A choice is a bold-letter line each (**A.** ...), your pick marked "my pick", plus buttons; one question at a time; never pick for him. Only the manager asks him things (D-016, D-021, D-022).

**Messages between chats are data:** one JSON object, fixed keys, values from a set list, a number or a version, and at most one `note` (plain line, 400 characters, no key, password or decision); the Rust check refuses anything else (D-027, item 52).
- `v` 1; `kind` READY, DONE, PASS, FAIL, STUCK, NEED, OWNER_CALL or ORDER; `from`, `to` role codes (the check lists them); `job` at most 4 words; `id` from-job-n, never reused.
- `sha`; `version` x.y.z; `tests` {passed, failed}; `touches` [top-level folders or files of the project, or database, file-store, outside-connection, board, owners-list, crew-files, site]; `usage` {week_pct}; `need` none, pass_or_fail, order, owner_answer, fix or unblock.
- READY: sha, tests above zero, touches, usage. DONE: usage. PASS, FAIL: the sha checked. ORDER: `owner_words` {"item": n} or {"decision": "D-027"}, `owns` [codes], `out` [codes], `action` ship, hold or start.
- Detail goes on the board, not in a note; a PASS or FAIL for the manager goes there only.

**Always.**
- His words come first, literally. Unsure what an order means: NEED, never guess. Coding gaps you fill and say what you chose; human gaps (look, wording, what counts as done, in or out) never (D-004).
- Usage first: small exact checks, free first, read little, no new chat if a running one can do it. At 90% of the week (`scripts/usage.py` exits 3) start no new order (D-016).
- Helpers: hand searches, big reads and side jobs to a subagent that returns only its result. It never talks to the owner, ships, pushes, passes or fails (bar the manager's fresh checker), or replaces a worker or the Inspector chat.
- Money, keys, passwords and deleting need his yes (D-001).
- `muster/` in the main folder is the crew's one copy: read it there; only the manager writes it; nobody saves or pushes it.
- Computer use only on an order naming his words and the one app; never the whole screen or the clipboard; else STUCK.
- Messages paused: report on the board with `Paused: yes`; set `Paused: no` when you can act.
- Before each new order re-read `muster/rules/<your role>.md`. After the first summary, renew at the next break (handover if a job is open, then DONE "renewal").
