# The message every worker sends (a data record)

Between chats there are no sentences (owner's list item 34, D-027: "communicate with code... english is not"). A message is one JSON
object with fixed keys. Every value is a number, a version, a hash, a code from a set list, or a list of codes. The program
`muster-checks` (ready-made for Windows, Mac and Linux, in the plugin's `bin/` folder) refuses anything else, so there is no room to
misread one.

| Key | Value |
|---|---|
| `v` | 1 |
| `kind` | READY, DONE, PASS, FAIL, STUCK, NEED, OWNER_CALL or ORDER |
| `from`, `to` | a role code: manager, builder-a (b, c ...), inspector, inspector-b, designer, design-inspector, sketchpad, ai-socket, agent-teacher or board |
| `job` | a code of at most 4 words (a-z, 0-9, `-`, `_`; 32 characters at most) |
| `id` | exactly `from-job-n` (n a number); never sent twice, a repeat is dropped |
| `sha` | the saved version, 7 to 40 lowercase hex characters, or null |
| `version` | `x.y.z`, or null |
| `tests` | `{"passed": n, "failed": n}`, or null |
| `touches` | list of codes (at most 3 words, 24 characters each): the shared things the change touches (empty if none) |
| `usage` | `{"week_pct": n}` from `scripts/usage.py`, `null` inside it when it cannot be read; never an invented number |
| `need` | none, pass_or_fail, order, owner_answer, fix or unblock |
| `owner_words` | ORDER only: `{"item": n}` (his list) or `{"decision": "D-027"}`; his words are read there, not retyped |
| `owns`, `out` | ORDER only: lists of codes |

Required by kind: **READY** has sha, tests above zero, touches and usage. **DONE** has usage. **PASS** and **FAIL** name the sha they
checked. **ORDER** has owner_words, owns and out. Any other key, or any value with a space in it, is refused.

Made-up example (a READY):

```
{"v":1,"kind":"READY","id":"builder-a-card-fix-1","job":"card-fix","from":"builder-a","to":"inspector","sha":"d082303","version":"0.3.49","tests":{"passed":12,"failed":0},"touches":["site-header"],"need":"pass_or_fail","usage":{"week_pct":41}}
```

Detail never goes in a record: it goes on the board (a PASS or FAIL for the manager goes there only) or in a file. What the owner
reads is the card each worker posts in its own window (see the page for your role); that stays in plain words.

Projects whose profile says `"message_form": "text"` (PINR) and the Cursor, Grok Bot and ChatGPT editions, where the program cannot
run, keep the older six-line report (What, Where with `touches:`, Why, How, Need); `scripts/check-report.py` checks that shape.
