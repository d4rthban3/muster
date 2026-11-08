#!/usr/bin/env python3
"""SessionStart hook (matcher "compact"): fires once, right after a chat's conversation was summarized.
Tells a CREW chat to hand over and renew at its next natural break. Silent for any other chat, including the owner's
own chats in the same folder: it acts only if the chat's FIRST user message (in the transcript) names a crew definition
(agents/<role>.md) or a crew chat name (<Role>_<project>_<digits>). It is an event, not a stop, so it cannot loop.
Reads only the hook's JSON from stdin and that transcript; writes nothing; any error means silence.
"""
import json
import re
import sys

CREW = r"(?:Manager|Builder [A-Za-z]|Designer|Design Inspector|Inspector|Sketchpad|AI Socket|Agent Teacher)"
ROLE_FILE = re.compile(r"agents[/\\](manager|builder|designer|inspector|design-inspector|sketchpad|ai-socket|agent-teacher)\.md")
CHAT_NAME = re.compile(r"\b%s_[^\s_][^_\n]*_\d{3}\b" % CREW)


def first_message(path):
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") != "user":
                    continue
                c = (d.get("message") or {}).get("content", "")
                if isinstance(c, list):
                    c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                return str(c)[:6000]
    except OSError:
        pass
    return ""


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    first = first_message(data.get("transcript_path") or "")
    role = ROLE_FILE.search(first)
    name = CHAT_NAME.search(first)
    if not role and not name:
        return 0  # not a crew chat (the owner's own chat, or another project)
    # a role file in the note decides alone; without one, only "You are Manager_..." makes it the manager (a worker's note
    # also names the manager, so a name alone proves nothing)
    if role:
        is_manager = role.group(1) == "manager"
    else:
        is_manager = bool(re.search(r"You are (?:the )?Manager_", first))
    if is_manager:
        msg = ("Muster: your conversation was just summarized, so you need a fresh chat (muster/CLAUDE.md section 9). At your "
               "next natural break write a short handover to muster/handovers/<your chat name>.md (what is open, the files "
               "that matter, the next step), then tell the owner in one line that you need a fresh manager chat, linked. "
               "Do this once.")
    else:
        msg = ("Muster: your conversation was just summarized, so it is time to renew (muster/CLAUDE.md section 9). At your "
               "next natural break, if a job is in progress write a short handover to muster/handovers/<your chat name>.md in "
               "the main project folder (what is open, the files that matter, the next step); then send the manager "
               "\"DONE: renewal <your chat name>\". Do this once, then carry on until the manager starts your fresh chat.")
    print(msg)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
