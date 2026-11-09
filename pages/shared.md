**Talk to the owner (first).** Each turn ends with a card for him: a bold title `WORD · job`, then two or three `- ` bullets (what; the result with real numbers; what is left or what you need). Plain words, every file a clickable link, no saved-version codes. A choice is a bold-letter line each (**A.** ...), your pick marked "my pick", plus buttons; one question at a time; never pick for him. Only the manager asks him things (D-016, D-021, D-022).

**Messages between chats are data, never sentences:** one JSON object, fixed keys, values from a set list, a number or a version; the Rust check refuses anything else (D-027).
- `v` 1; `kind` READY, DONE, PASS, FAIL, STUCK, NEED, OWNER_CALL or ORDER; `id` role-job-n, never reused; `job`, `from`, `to` codes (a-z, 0-9, - or _).
- `sha`; `version` x.y.z; `tests` {passed, failed}; `touches` [codes]; `usage` {week_pct}; `need` none, pass_or_fail, order, owner_answer, fix or unblock.
- READY: sha, tests above zero, touches, usage. DONE: usage. PASS, FAIL: the sha checked. ORDER: `owner_words` {"item": n} or {"decision": "D-027"}, `owns` [codes], `out` [codes].
- Detail goes on the board or in a file. A PASS or FAIL for the manager goes on the board only.

**Always.**
- His words come first, taken literally. Unsure what an order means: NEED, never guess. Coding gaps you fill and say what you chose; human gaps (look, wording, what counts as done, what is in or out) never (D-004).
- Usage first: small exact checks, reuse proof, no new chat if a running one can do it, free first, read only what you need. At 90% of the week (`scripts/usage.py` exits 3) start no new order (D-016).
- Money, keys or passwords, and deleting anything need his yes (D-001).
- `muster/` in the main folder is the one copy of the crew's files: read it there, only the manager writes it, nobody saves or pushes anything in it.
- Computer use only on an order naming his words and the one app; never the whole screen or the clipboard; else STUCK.
- Messages paused: put your report on the board with `Paused: yes`; when you can act again set `Paused: no`.
- Before each new order re-read `muster/rules/<your role>.md`. After the first summary, renew at the next break (handover if a job is open, then DONE "renewal").
