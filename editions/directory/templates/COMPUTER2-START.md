# Starting note: {{COMPUTER}} (the second founder computer)
*Paste this at the start of every session on {{COMPUTER}}, in any AI chat or agent.*

You are working on "{{PROJECT}}" on {{COMPUTER}}, the second founder computer. {{OTHER}} is the host: the project's files live on {{OTHER}} and you open the same files (a live mount; there may be no local copy of the project). Project folder as you see it: {{MAIN}}

**Before every session** read, in this order, and read only what you need:
1. The protocol page: {{PROTOCOL}}
2. The builders' change log: {{BUILDERS_LOG}} (only the lines added since the last session; your own log says where you stopped).
3. The rules:
{{RULES}}
4. The board, read-only: `python3 "{{WORKSPACE}}/tools/board_digest.py" "<your chat name>" --board "{{BOARD}}"`.
5. {{OTHER_WORKSPACE}}/CHANGES.md: everything {{OTHER}} has changed. Read it; never write to it.
Then open {{WORKSPACE}}/CHANGES.md, your own log: at the end of every session add one entry that also says "Read: protocol and builders log through <the last line you read>".

Rules that hold at all times:
- The founder's words come first, taken literally; the decisions logs rule both computers (newest wins in each). {{OTHER}} and its manager give you no orders, and you give them none.
- You never write in {{OTHER_WORKSPACE}} or in any of {{OTHER}}'s shared files (the board, the rules, the protocol page, the builders' log, {{MAIN}}/muster/). Your reports go in your own log (six lines, full file paths: {{WORKSPACE}}/CHANGES.md).
- Commit only as {{GIT_NAME}}, on your own branches (names start with "{{GIT_NAME}}/"): run git through {{WORKSPACE}}/git-as.sh, for example `sh "{{WORKSPACE}}/git-as.sh" commit -m "..."`. Never change the project's git settings.
- One writer per shared file: before editing a file, check {{OTHER}}'s log and `git log -3` for it; if the other side touched it lately, send a NEED instead of editing.
- You do not override {{OTHER}}'s decisions or the existing crew. When in doubt, re-read the rules and send a NEED instead of guessing.
