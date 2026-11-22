# look-fast-load: what the look costs from chat open to the first drawn card

Method: the look's own hooks (session start, then one question card with a saved pick) are called in the test kit
with a host whose every store, file, process and session read takes 20 ms (test "look-fast-load" in look/look.test.tsx).
Before = main at 0.3.176, after = this branch. Machine load average was about 85 while measuring, so every figure
includes that noise; two runs each.

| chat | before: chat open | before: first card drawn | after: chat open | after: first card drawn |
| --- | --- | --- | --- | --- |
| short (3 messages), pick saved | 139-158 ms | 561-648 ms | 1-3 ms | 70-203 ms |
| 6000 messages, pick saved | 139-156 ms | 465-481 ms | 0.1 ms | 65-92 ms |
| 6000 messages, nothing picked | 135-146 ms | 221 ms | 0.1-2 ms | 64-94 ms |

Of the "after" first draw, 40 ms is the two chained 20 ms reads it has to wait on (the group's id, then its look beside
the saved picks); the rest is the loaded machine plus a few ms of the look's own work. On a quiet machine the same
test is about 45-50 ms.

Reads the first draw waited on before: 20 (short chat) / 9 to 20: the migration check, the glass setting, the app font
file, the command, the whole chat history, a git process, CREW.md and parent folders, then the look and picks.
After: the id, the look and the picks only; the history, the process and every file read start later or never
(the history is read after the draw only to check a saved answer was not rewound).

What changed: session start no longer waits on anything (the glass background, the old-plugin copy, the /look command
and the app font load beside it); a saved answer is drawn at once and checked against the chat after the draw (a rewound
answer goes back to unpicked and the card redraws); the id, the look and the picks are asked once, together.

Not measured: the live app (it cannot be driven from here), the real cost of reading a 6,500-message history (the test
gives it one 20 ms read, so the true saving is larger), and the real app font file read. One thing the owner may see:
for a moment after the chat opens the letter chips can draw in the fallback font until the app font is in, then redraw.
