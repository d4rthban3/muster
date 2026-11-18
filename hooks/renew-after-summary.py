#!/usr/bin/env python3
"""SessionStart hook (matcher "compact"): fires once, right after a chat's conversation was summarized.
Tells a CREW chat it was compacted in place (D-039, item 105): no renewal; the rules come back. Silent for any other chat, including the owner's
own chats in the same folder: it acts only if the chat's FIRST user message (in the transcript) names a crew definition
(agents/<role>.md) or a crew chat name (<Role>_<project>_<digits>). It is an event, not a stop, so it cannot loop.
Reads only the hook's JSON from stdin and that transcript; writes nothing; any error means silence.
"""
import json
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):  # print on any computer, whatever its console encoding
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CREW = r"(?:Manager|Builder [A-Za-z]|Designer|Design Inspector|Inspector|Sketchpad|AI Socket|Agent Teacher)"
ROLE_FILE = re.compile(r"agents[/\\](manager|builder|designer|inspector|design-inspector|sketchpad|ai-socket|agent-teacher)\.md")
CHAT_NAME = re.compile(r"\b%s_[^\s_][^_\n]*?(?:_\d{3})?\b" % CREW)


def load_profile():
    """The project's profile (item 99): beside an installed copy (.muster-checks/profile.json), or MUSTER_PROFILE; its chat-name patterns decide who is crew."""
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.environ.get("MUSTER_PROFILE"), os.path.join(here, "profile.json")):
        if cand and os.path.isfile(cand):
            try:
                d = json.load(open(cand, encoding="utf-8"))
                return d if isinstance(d, dict) else {}
            except (OSError, ValueError):
                return {}
    return {}


PROFILE = load_profile()
PROFILE_CREW = [re.compile(x) for x in (PROFILE.get("crew_names") or []) + (PROFILE.get("manager_names") or [])]
PROFILE_MANAGER = (PROFILE.get("manager_names") or [])


def remember_first(path, first):
    """Keep a crew chat's own first message beside its transcript so it still knows who it is after a compaction (D-039)."""
    side = path + ".muster-first"
    try:
        if path and not os.path.exists(side):
            with open(side, "w", encoding="utf-8") as fh:
                fh.write(first[:6000])
    except OSError:
        pass


def chat_title(path):
    """The chat's own title: the last custom-title record in its transcript. "" when it cannot be read."""
    title = ""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if "custom-title" not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") == "custom-title" and isinstance(d.get("customTitle"), str):
                    title = d["customTitle"]
    except OSError:
        return ""
    return title.strip()


def first_message(path):
    # D-039: after a compaction the file may open with the summary; the chat's own first message is kept beside it
    try:
        with open(path + ".muster-first", encoding="utf-8") as fh:
            kept = fh.read()
        if kept.strip():
            return kept[:6000]
    except OSError:
        pass
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") != "user" or d.get("isCompactSummary"):
                    continue
                c = (d.get("message") or {}).get("content", "")
                if isinstance(c, list):  # only the text blocks: a line holding only tool results is not the chat's first message
                    c = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
                if not str(c).strip():
                    continue
                return str(c)[:6000]
    except OSError:
        pass
    return ""


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except Exception:
        return 0
    first = first_message(data.get("transcript_path") or "")
    if not (ROLE_FILE.search(first) or CHAT_NAME.search(first) or any(p.search(first) for p in PROFILE_CREW)):
        t = chat_title(data.get("transcript_path") or "")  # a summary opens the file: the chat's own title says who it is
        if t and (CHAT_NAME.match(t) or any(p.match(t) for p in PROFILE_CREW)):
            first = "You are " + t
    role = ROLE_FILE.search(first)
    name = CHAT_NAME.search(first)
    named_in_profile = any(p.search(first) for p in PROFILE_CREW)
    if not role and not name and not named_in_profile:
        return 0  # not a crew chat (the owner's own chat, or another project)
    # a role file in the note decides alone; without one, only "You are Manager_..." makes it the manager (a worker's note
    # also names the manager, so a name alone proves nothing)
    if role:
        is_manager = role.group(1) == "manager"
    else:
        is_manager = bool(re.search(r"You are (?:the )?Manager_", first)) or any(re.search(r"You are (?:the )?(?:%s)" % x, first) for x in PROFILE_MANAGER)
    # D-039 (item 105): chats compact in place; nobody renews because of a summary or a size
    msg = ("Muster: your conversation was just compacted in place (D-039); carry on, no renewal. Your open job, branch and saved version were written "
           "to the board just before it. Re-read your rules page (muster/rules/<your role>.md) and the board entries addressed to you.")
    print(msg)
    try:  # the talking rules fade in a long or summarized chat: put them back, once per summary
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "talk-block.txt"), encoding="utf-8") as fh:
            print(fh.read().rstrip())
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
