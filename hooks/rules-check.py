#!/usr/bin/env python3
"""Muster's rules as code (D-027): one self-contained file, so a project that does not load the plugin can copy just this.

It reads one hook event from standard input and acts only in a crew chat (the chat's FIRST message names agents/<role>.md
or <Role>_<project>_<digits>); it is silent in the owner's own chats and on any error. It writes nothing and sends nothing.

PreToolUse (a chat is about to act):
  SendMessage    a message between chats must be a six-line report (FIRST WORD, What, Where with touches:, Why, How, Need,
                 and a Usage line on DONE and READY; a READY shows a test count) or an order (To, Job, Owner's words with
                 his words in quotes, Owns, Out, Done); no "noted/thanks" replies; no ID sent twice; no new order while the week is at 90% (usage.py).
  Write/Edit/Bash  only the manager changes the owner's list, the decisions log, the crew list, the rules pages and
                 muster/CLAUDE.md; nobody saves or pushes anything under muster/.
Stop (a chat is about to end its turn; blocks at most once, never loops):
  manager        the reply to the owner is a question with its choices, a yes he must give, or "The crew is idle"; and an answer to a choice card is recorded (record-choice.py).
  other workers  the reply is a card: a bold "WORD . job" title, then two or three bullets; a card headed DONE, READY, PASS, FAIL, STUCK or NEED
                 needs a message to the manager in the same turn (item 65).
Exit 0 always; a refusal is printed as the hook's JSON.
"""
import json
import os
import re
import subprocess
import sys

ROLE = (r"(?:Manager|Builder [A-Za-z]|Designer|Design Inspector|Inspector|Sketchpad|AI Socket|Agent Teacher)")
CREW_RE = re.compile(r"agents[/\\](?:manager|builder|designer|inspector|design-inspector|sketchpad|ai-socket|agent-teacher)\.md|\b%s_[^\s_][^_\n]*?(?:_\d{3})?\b" % ROLE)
MANAGER_RE = re.compile(r"agents[/\\]manager\.md|\bManager_[^_\n]*?(?:_\d{3})?\b")


def load_profile():
    """A project profile (profile.json beside this file, or the file named in MUSTER_PROFILE) lets another project's chat
    names, report shape, board path and choice recorder be checked. No profile means exactly Muster's own rules."""
    for cand in (os.environ.get("MUSTER_PROFILE"), os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile.json")):
        if cand and os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as fh:
                    d = json.load(fh)
                return d if isinstance(d, dict) else {}
            except (OSError, ValueError):
                return {}
    return {}


PROFILE = load_profile()
if PROFILE.get("crew_names"):
    CREW_RE = re.compile(CREW_RE.pattern + "|" + "|".join("(?:%s)" % x for x in PROFILE["crew_names"]))
if PROFILE.get("manager_names"):
    MANAGER_RE = re.compile(MANAGER_RE.pattern + "|" + "|".join("(?:%s)" % x for x in PROFILE["manager_names"]))
REPORT_ID = PROFILE.get("report", {}).get("require_id", True)
REPORT_USAGE = PROFILE.get("report", {}).get("require_usage", True)
ORDERS_FREE = PROFILE.get("orders") == "free"
RECORDER = PROFILE.get("record_choice", "record-choice.py")
# Between chats a message is a data record (muster-checks, the ready-made program, checks every key). This older Python copy only
# runs where no ready-made program exists; it still refuses plain sentences. "text" keeps the older six-line report.
TEXT_FORM = (os.environ.get("MUSTER_MESSAGE_FORM") or PROFILE.get("message_form") or "records") == "text"
FIRST = r"(DONE|READY|PASS|FAIL|OWNER CALL|STUCK|NEED)"
LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")


# ---- the report shape (same rules as scripts/check-report.py) -------------------------------------------------
def report_problem(text):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    usage = None
    if len(lines) == 7 and lines[6].startswith("Usage:"):
        usage = lines.pop()
    if len(lines) != 6:
        return "expected 6 lines%s, found %d" % (" (and a Usage line on DONE and READY)" if REPORT_USAGE else "", len(lines))
    if REPORT_ID:
        m = re.match(r"^%s: .+ \[ID [^\]]+-\d+\]$" % FIRST, lines[0])
    else:
        m = re.match(r"^%s: .+$" % FIRST, lines[0])
    if not m:
        return "first line must be 'FIRST WORD: job name%s'" % (" [ID role-job-number]" if REPORT_ID else "")
    for line, label in zip(lines[1:], ["What:", "Where:", "Why:", "How:", "Need:"]):
        if not line.startswith(label):
            return "expected a line starting %s" % label
    if "touches:" not in lines[2]:
        return "Where line lacks 'touches:'"
    if REPORT_USAGE and m.group(1) in ("DONE", "READY") and usage is None:
        return "a DONE or READY needs a Usage line (scripts/usage.py prints it)"
    if m.group(1) == "READY" and not re.search(r"\d+\s*(/|of)\s*\d+|\d+ passed", lines[4]):
        return "READY's How line shows no test count"
    return None


def order_problem(text):
    """An order: lines To, Job, Owner's words (his words in quotes), Owns, Out, Accept, Done, each starting its label.
    A Contract line is optional (a hand-off between workers) but, when it is there, it must be filled."""
    labels = {}
    for l in text.splitlines():
        m = re.match(r"^\s*(To|Job|Owner'?s words|Owns|Out|Accept|Contract|Done)\s*:\s*(.*)$", l, re.I)
        if m:
            labels.setdefault(m.group(1).lower().replace("owners", "owner's"), m.group(2))
    for need in ("to", "job", "owner's words", "owns", "out", "accept", "done"):
        if need not in labels or not labels[need].strip():
            return "an order needs a filled '%s:' line" % need.capitalize()
    if "contract" in labels and not labels["contract"].strip():
        return "the Contract line is empty: name what is handed over and its shape, or leave the line out"
    if not re.search(r"[\"“][^\"”]{3,}[\"”]", labels["owner's words"]):
        return "the Owner's words line must quote his words in quotation marks"
    return None


def _token_is_manager(tok):
    """tok is a crew name or an agents/<role>.md path, as CREW_RE matched it."""
    if re.match(r"agents[/\\]", tok):
        return re.search(r"agents[/\\]manager\.md$", tok) is not None
    return re.fullmatch(r"Manager_[^_\n]*?(?:_\d{3})?", tok) is not None or any(
        re.fullmatch(x, tok) for x in PROFILE.get("manager_names", []))


def _own_token(first):
    """The chat's own crew name (or agents/<role>.md) in its starting note, or None (see is_manager)."""
    best = None
    for lead in (r"\bJob:\s*[*`]{0,2}", r"\b(?:you are|i am|i'm)\s+(?:the\s+)?[*`]{0,2}"):
        for m in re.finditer(lead, first, re.I):
            c = CREW_RE.match(first, m.end())
            if c and (best is None or m.start() < best[0]):
                best = (m.start(), re.sub(r"^(?:you are|i am|i'm)\s+(?:the\s+)?[*`]{0,2}", "", c.group(0), flags=re.I))  # a profile pattern may swallow "You are " before the name
                break
    return best[1] if best else None


def is_manager(first):
    """Only the chat's OWN name makes it the manager. Its own name is the first crew name that follows 'Job:', 'You are' or 'I am' (a summary says "I am **Manager_X_001**") in
    its starting note (every such place is tried: 'You are operating in a git worktree' holds no name). Else the first
    agents/<role>.md it names, else a Job line that says 'go-between' or 'record keeper'. A crew name that is merely
    mentioned ("report to Manager_X_002", "Manager_X_001 gives every order") never makes a chat the manager."""
    tok = _own_token(first)
    if tok:
        return _token_is_manager(tok)
    m = re.search(r"agents[/\\](?:manager|builder|designer|inspector|design-inspector|sketchpad|ai-socket|agent-teacher)\.md", first)
    if m:
        return _token_is_manager(m.group(0))
    return re.search(r"\bJob:[^\n]*(go-between|record keeper)", first, re.I) is not None


# ---- reading the event ----------------------------------------------------------------------------------------
def remember_first(path, first):
    """Keep a crew chat's own first message beside its transcript so it still knows who it is after a compaction (D-039)."""
    side = path + ".muster-first"
    try:
        if path and not os.path.exists(side):
            with open(side, "w", encoding="utf-8") as fh:
                fh.write(first[:6000])
    except OSError:
        pass


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


def compact_summary(path):
    """The compaction summary's text (item 113/box-check-pinr): when no .muster-first file was kept, it is the one place left that names the chat."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") == "user" and d.get("isCompactSummary"):
                    c = (d.get("message") or {}).get("content", "")
                    if isinstance(c, list):
                        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
                    return str(c)[:6000]
    except OSError:
        pass
    return ""


def first_or_summary(path, crew=None):
    """The chat's first message; but when that names no crew chat (a compaction rewrote it and no .muster-first was kept), the compaction
    summary if it says who the chat is ('I am Builder A_X', 'Job: ...')."""
    first = first_message(path)
    if not (crew or CREW_RE).search(first):
        summ = compact_summary(path)
        if summ and _own_token(summ) is not None:
            return summ
    return first


def turn_blocks(path):
    """(tool_use blocks, results text) of the current turn: everything after the last real user message."""
    uses, texts = [], []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                c = (d.get("message") or {}).get("content", "")
                if d.get("type") == "user":
                    if isinstance(c, str) or any(isinstance(b, dict) and b.get("type") == "text" for b in c):
                        uses, texts = [], []
                    continue
                if d.get("type") == "assistant" and isinstance(c, list):
                    for b in c:
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            uses.append(b)
    except OSError:
        pass
    return uses


def all_sent_pairs(path):
    """The (recipient, text) of messages that were really sent: a SendMessage whose result came back without an error. A call still
    waiting for its result (this one, or a sibling sent in the same turn) and a call a hook refused do not count, so a
    refused send does not use up its ID."""
    calls, failed, done = {}, set(), set()
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                c = (d.get("message") or {}).get("content", "")
                if not isinstance(c, list):
                    continue
                for b in c:
                    if not isinstance(b, dict):
                        continue
                    if d.get("type") == "assistant" and b.get("type") == "tool_use" and b.get("name") == "SendMessage":
                        calls[b.get("id")] = (str((b.get("input") or {}).get("to", "")), str((b.get("input") or {}).get("message", "")))
                    elif d.get("type") == "user" and b.get("type") == "tool_result":
                        done.add(b.get("tool_use_id"))
                        rc = b.get("content", "")
                        rc = " ".join(x.get("text", "") for x in rc if isinstance(x, dict)) if isinstance(rc, list) else str(rc)
                        if b.get("is_error") or rc.lstrip().startswith("Muster rule:") or "Muster rule:" in rc[:200]:
                            failed.add(b.get("tool_use_id"))
    except OSError:
        pass
    return [c for i, c in calls.items() if i in done and i not in failed]


def all_sent_text(path):
    return [t for _, t in all_sent_pairs(path)]


DUP_WHY = "this report (same job and first word) was already sent to this chat with nothing changed; send it again only when something changed (item 97)"


def same_report(a, b):
    """Item 97: two reports of the same job and first word with nothing changed (only the ID differs)."""
    def norm(m):
        try:
            d = json.loads(m)
            if isinstance(d, dict):
                d.pop("id", None)
                return json.dumps(d, sort_keys=True)
        except ValueError:
            pass
        mm = re.match(r"^\s*%s: (.+?) \[ID [^\]]+\]\s*\n(.*)$" % FIRST, m, re.S)
        return None if not mm else "%s|%s|%s" % (mm.group(1), mm.group(2), re.sub(r"\s+", " ", mm.group(3).strip()))
    na, nb = norm(a), norm(b)
    return na is not None and na == nb


def dup_report(to, msg, path):
    return any(t == to and same_report(m, msg) for t, m in all_sent_pairs(path))


ENDS_TURN = re.compile(r"<cross-session-message|<task-notification|<side-sessions-event|<ci-monitor-event|\[SYSTEM NOTIFICATION", re.I)
NEUTRAL = re.compile(r"^\s*(<system-reminder|Stop hook feedback)", re.I)


def bounced_this_turn(path):
    """True when a Stop hook already bounced a reply in this turn (the turn starts at the last message that is not hook feedback);
    a check bounces at most once per turn (item 57)."""
    bounced = False
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
                    if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                        continue
                    c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                t = str(c).strip()
                if not t:
                    continue
                if t.startswith("Stop hook feedback") or t.startswith("Stop hook blocking error"):
                    bounced = True
                elif not t.startswith("<system-reminder"):
                    bounced = False
    except OSError:
        pass
    return bounced


ASKING = re.compile(r"^\s*(what|why|how|when|where|who|which|can|could|would|will|did|does|do|is|are|was|were|should|tell|show|explain|look|check|find|list|give|say|read|open|run)\b|\b(tell me|show me|let me know|how come|what's|look at|or (is|are|do|does|should|can|would)|is (that|it|this)|do (i|we)|should (i|we)|can (i|we))\b", re.I)


def owner_asked(path):
    """True if this turn was started by the owner's typed message and it holds a question mark. The turn's starting message is
    the owner's last typed message; a message from another chat or an app event (cross-session, task, side-sessions, CI)
    ends it (an earlier question of his does not carry over), while hook feedback and system reminders change nothing."""
    last = ""
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
                    if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                        continue
                    c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                c = str(c)
                if not c.strip():
                    continue
                if ENDS_TURN.search(c):
                    last = ""
                elif not NEUTRAL.match(c):
                    last = c
    except OSError:
        pass
    return "?" in last or bool(ASKING.search(last))


def peer_started(path):
    """True when this turn was started by a message from another chat or an app event (cross-session, task, side-sessions,
    CI), not by the owner's typed words; hook feedback and system reminders change nothing (item 75)."""
    last = False
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
                    if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                        continue
                    c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                c = str(c)
                if not c.strip():
                    continue
                if ENDS_TURN.search(c):
                    last = True
                elif not NEUTRAL.match(c):
                    last = False
    except OSError:
        pass
    return last


def short_report(text):
    """A one-to-three line reply of at most 300 characters: a routine report, not a long narration."""
    t = text.strip()
    return len(t) <= 300 and len(t.splitlines()) <= 3


LETTER_ANSWER = re.compile(r"^\s*\(?([A-Da-d])\)?[.:!]*\s*$")
LETTERED = re.compile(r"^\s*\*{2,3}[A-D]\.\*{2,3}", re.M)


LETTER_LINE = re.compile(r"^\s*(?:\*{1,3}|_)?\(?([A-D])[.)]\*{0,3}\s", re.M)
GOOD_LETTER_LINE = re.compile(r"^\s*\*\*\*[A-D]\.\*\*\*\s")


TITLE_LINE = re.compile(r"^\s*\*\*[^*\n]+\s[\u00b7.]\s[^*\n]+\*\*\s*$")


def title_above_choices(text):
    """True when a bold 'WORD \u00b7 job' heading line stands above the first lettered choice line (item 120)."""
    for l in text.splitlines():
        if re.match(r"^\*\*\*[A-D]\.\*\*\*", l):
            return False
        if TITLE_LINE.match(l):
            return True
    return False


def letters_not_bold_italic(text):
    """True when the reply writes two or more lettered choice lines and any of them is not ***A.*** (bold and italic) (item 80)."""
    lines = [l for l in text.splitlines() if LETTER_LINE.match(l)]
    return len(lines) >= 2 and any(not GOOD_LETTER_LINE.match(l) for l in lines)


def typed_letter_answer(path):
    """The letter he typed (A to D) when this turn was started by his bare typed letter and the manager's last text asked a
    lettered question (***A.*** ...); else None. A message from another chat or an app event, hook feedback and system
    reminders are not his words (item 80, D-037)."""
    prev, last = "", None
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                c = (d.get("message") or {}).get("content", "")
                if d.get("type") == "assistant" and isinstance(c, list):
                    t = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text").strip()
                    if t:
                        prev = t
                elif d.get("type") == "user":
                    if isinstance(c, list):
                        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                            continue
                        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                    c = str(c)
                    if not c.strip() or NEUTRAL.match(c):
                        continue
                    if ENDS_TURN.search(c):
                        last = None
                        continue
                    m = LETTER_ANSWER.match(c)
                    last = m.group(1).upper() if m and LETTERED.search(prev) else None
    except OSError:
        pass
    return last


def main_folder(cwd):
    """The project's main folder: the parent of git's common dir (a worktree copy points at it), else cwd."""
    try:
        r = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=cwd or None, capture_output=True, text=True, timeout=10)
        p = r.stdout.strip()
        if p:
            p = os.path.abspath(os.path.join(cwd or ".", p))
            return os.path.dirname(p) if os.path.basename(p) == ".git" else cwd
    except Exception:
        pass
    return cwd


NOREPEAT = " Your reply already reached the owner: do not write it again. Do what this asks, then end with at most one new line, or nothing."
def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": "Muster rule: " + reason}}))


def block(reason):
    print(json.dumps({"decision": "block", "reason": "Muster rule: " + reason + NOREPEAT}))


# ---- PreToolUse -----------------------------------------------------------------------------------------------
_SOC = r"(?:noted|received|thanks|thank you|got it|ok(?:ay)?|ack(?:nowledged)?|will do|and)"
SOCIAL = re.compile(r"^\s*%s\b(?:[\s.,!;&-]+%s\b)*[\s.,!;&-]*$" % (_SOC, _SOC), re.I)  # only social words, however many ("noted, thanks")
PROTECTED = re.compile(r"/muster/(OWNERS-LIST\.md|DECISIONS-LOG\.md|CREW\.md|CLAUDE\.md|rules/|RULES-PAGE\.md|REPORT\.md)")
PROFILE_PROTECTED = None
if PROFILE.get("protected"):  # a project's own manager-only paths (regexes on the path with forward slashes)
    PROFILE_PROTECTED = re.compile("|".join("(?:%s)" % x for x in PROFILE["protected"]))
    PROTECTED = re.compile(PROTECTED.pattern + "|" + PROFILE_PROTECTED.pattern)


def shell_write_targets(cmd):
    """Paths a shell command writes to: a redirect (> or >>), tee, sed -i, and the destination of cp, mv or install."""
    import shlex
    out = []
    for seg in re.split(r"[;&|\n]+", cmd):
        for m in re.finditer(r"(?<![<>&0-9])\d?>>?\s*(\"[^\"]+\"|'[^']+'|[^\s;&|<>]+)", seg):
            out.append(m.group(1).strip("\"'"))
        seg2 = re.sub(r"\d?>>?\s*(\"[^\"]+\"|'[^']+'|[^\s;&|<>]+)", " ", seg)
        try:
            words = shlex.split(seg2)
        except ValueError:
            words = seg2.split()
        if not words:
            continue
        i = 0
        while i < len(words) and (words[i] in ("sudo", "command", "env") or "=" in words[i].split("/")[0]):
            i += 1
        if i >= len(words):
            continue
        prog, args = os.path.basename(words[i]), [w for w in words[i + 1:]]
        files = [w for w in args if not w.startswith("-")]
        if prog == "tee":
            out += files
        elif prog == "sed" and any(re.match(r"-[A-Za-z]*i", w) or w.startswith("--in-place") for w in args):
            out += files[1:] if len(files) > 1 else []
        elif prog in ("cp", "mv", "install", "rsync", "ln") and files:
            out.append(files[-1])
        elif prog == "dd":
            out += [w[3:] for w in args if w.startswith("of=")]
    return out


NAME_NUM = re.compile(r"^(.+?_[^_\s|]+?)(?:_(\d{3}))?$")  # D-040: a name is <Role>_<project>; old names may still carry a number
ID_RE = re.compile(r"local_[^\s|]+")


def _crew_lists(root):
    """[(path, is Muster's own crew.md)]: the crew lists, read live every time (item 94)."""
    lists = [(os.path.join(root, "muster", "CREW.md"), True)]
    if PROFILE.get("crew_list"):
        lists.append((os.path.join(root, PROFILE["crew_list"]), False))
    return lists


def _is_manager_name(name):
    return re.fullmatch(r"Manager_[^_\s|]+(?:_\d{3})?", name) is not None or any(re.search("^(?:%s)$" % x, name) for x in PROFILE.get("manager_names", []))


def crew_rows(root):
    """[(name, chat id, is a manager)] of the crew list rows that are running: Muster's 'Running now' table; a profile's list in full."""
    out = []
    for path, own in _crew_lists(root):
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue
        if own:
            m = re.search(r"## Running now(.*?)(?:\n## |\Z)", text, re.S)
            text = m.group(1) if m else ""
        for l in text.splitlines():
            if not l.lstrip().startswith("|"):
                continue
            cells = [c.strip().strip("*`") for c in l.strip().strip("|").split("|")]
            idm = ID_RE.search(l)
            if cells and NAME_NUM.match(cells[0]) and (idm or not own):
                out.append((cells[0], idm.group(0) if idm else "", _is_manager_name(cells[0])))
    return out


def managers_in_force(root):
    """[(name, id)] the newest manager of each project in the crew lists: the manager a worker's report goes to, never the one in its memory."""
    best = {}
    for name, cid, mgr in crew_rows(root):
        m = NAME_NUM.match(name)
        if mgr and m and (m.group(1) not in best or int(m.group(2) or 0) >= int(NAME_NUM.match(best[m.group(1)][0]).group(2) or 0)):
            best[m.group(1)] = (name, cid)
    return list(best.values())


def recipient_is_manager(to, root):
    """True when `to` is the manager in force (item 101). With a crew list that names managers, only the newest one counts: an
    older manager's name or id, from a worker's memory, no longer does. With no readable list: any Manager name, as before."""
    to = str(to).strip()
    force = managers_in_force(root)
    if force:
        return any(to and to in (n, i) for n, i in force)
    if re.search(r"\bManager", to):
        return True
    for path, _ in _crew_lists(root):
        try:
            for l in open(path, encoding="utf-8"):
                if to and to in l and (l.lstrip("| ").startswith("Manager") or MANAGER_RE.match(l.lstrip("| "))):
                    return True
        except OSError:
            pass
    return False


def manager_now(root):
    force = managers_in_force(root)
    return "; the manager in force is " + " / ".join("%s (%s)" % (n, i) if i else n for n, i in force) + " (from the crew list)" if force else ""


def sessions_dir():
    d = os.environ.get("MUSTER_SESSIONS_DIR")
    if d:
        return d
    home = os.path.expanduser("~")
    for c in (os.path.join(home, "Library", "Application Support", "Claude", "claude-code-sessions"),
              os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude-code-sessions"),
              os.path.join(home, ".config", "Claude", "claude-code-sessions")):
        if os.path.isdir(c):
            return c
    return ""


def session_record(cid):
    """The app's session record for a chat id (read-only), or None."""
    import glob
    base = sessions_dir()
    for f in glob.glob(os.path.join(base, "*", "*", cid + ".json")) if base and cid else []:
        try:
            return json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return None


def sends_all(path):
    """[(recipient, text)] of every message the chat sent (SendMessage 'to', or the app's send_message 'session_id')."""
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                c = (d.get("message") or {}).get("content", "")
                for b in c if isinstance(c, list) else []:
                    if isinstance(b, dict) and d.get("type") == "assistant" and b.get("type") == "tool_use" and (b.get("name") == "SendMessage" or str(b.get("name")).endswith("send_message")):
                        i = b.get("input") or {}
                        out.append((str(i.get("to") or i.get("session_id") or ""), str(i.get("message") or "")))
    except OSError:
        pass
    return out


def goal_problem(root, job):
    """The weekly goal (muster/GOAL.md, set by the manager from the owner's words): an ORDER whose job is not on its set list waits.
    No goal, or a goal with no set list, enforces nothing; the owner can change it any time (scripts/goal.py set)."""
    try:
        text = open(os.path.join(root or ".", "muster", "GOAL.md"), encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r"^Set list.*?:\s*\n((?:- .*\n?)*)", text, re.M)
    jobs = [l[2:].strip() for l in (m.group(1).splitlines() if m else []) if l.startswith("- ") and l[2:].strip()]
    if not jobs or job in jobs:
        return None
    w = re.search(r'^Goal \(his words\):\s*"(.*)"\s*$', text, re.M)
    d = re.search(r"^Done when:\s*(.*)$", text, re.M)
    return ('the owner\'s goal for the team is "%s" (done when: %s) and the job %s is not on its set list, so it waits. '
            "He can change the goal any time: ask him, then run scripts/goal.py set" % (w.group(1) if w else "", d.group(1).strip() if d else "not said", job))


def usage_at_limit(root):
    for cand in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "usage.py"),
                 os.path.join(root or ".", ".muster-checks", "usage.py")):
        if os.path.isfile(cand):
            try:
                return subprocess.run([sys.executable, cand], capture_output=True, text=True, timeout=20).returncode == 3
            except Exception:
                return False
    return False


NOTE_SECRET = re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{12,}|AKIA[A-Z0-9]{12,}|BEGIN [A-Z ]*PRIVATE KEY|password\s*[:=]|api[_-]?key\s*[:=]|token\s*[:=]", re.I)
HELPER_ROLES = ("manager", "builder", "designer", "inspector", "design-inspector", "sketchpad", "ai-socket", "agent-teacher")
HELPER_ASK = re.compile(r"scripts[/\\]ship\.sh|\bgit\s+push\b|\bSendMessage\b|\bAskUserQuestion\b", re.I)
HELPER_NEG = re.compile(r"\b(never|not|no|without|don't|do not)\b|n't\b", re.I)


def helper_problem(inp, manager):
    """Helpers (item 36): a subagent may not stand in for a worker (only the manager's fresh checker uses the inspector
    definition), and its brief may not ask it to ship, push, message other chats or ask the owner."""
    kind = str(inp.get("subagent_type", "")).strip().lower()
    if kind.startswith("muster:"):
        kind = kind[7:]
    if kind in HELPER_ROLES and not (manager and kind == "inspector"):
        return deny("a helper never stands in for a worker or the Inspector chat (%s); use a plain helper for the side job "
                    "(only the manager's fresh checker for a small piece uses the inspector definition)" % kind)
    for line in str(inp.get("prompt", "")).splitlines():
        if HELPER_ASK.search(line) and not HELPER_NEG.search(line):
            return deny("a helper never ships, pushes, messages other chats or talks to the owner; take that out of its brief and do it yourself")


# item 88: a question is about how something looks on screen when it holds a picture word, or a word like look/design/style
# together with a word for something on a screen; "looks right" in a rules choice is not that
LOOK = re.compile(r"\b(colou?rs?|mock-?ups?|layouts?|fonts?|icons?|logos?|pictures?|images?|screenshots?|appearance|visuals?|dark mode|light mode|spacing|banners?)\b", re.I)
LOOK_WEAK = re.compile(r"\b(looks?|looking|designs?|styl(?:e|es|ing)|themes?)\b", re.I)
LOOK_SCREEN = re.compile(r"\b(pages?|screens?|sites?|websites?|apps?|buttons?|headers?|footers?|tiles?|cards?|charts?|dashboards?|tabs?|menus?|ui|display|phones?|mobile|windows?|panes?|panels?|texts?|on screen|homepage|web)\b", re.I)
IMG = re.compile(r"\.(png|jpe?g|gif|webp|svg|html?|pdf)\b", re.I)


def pictures_shown(uses):
    """Show first (item 63): pictures were shown to him in this turn (send-file, an artifact, or card option previews)."""
    for u in uses:
        inp = u.get("input") or {}
        name = u.get("name")
        if name == "SendUserFile" and (IMG.search(json.dumps(inp)) or inp.get("display") == "render"):
            return True
        if name == "Artifact":
            return True
        if name == "AskUserQuestion":
            for q in inp.get("questions") or []:
                if any(isinstance(o, dict) and o.get("preview") for o in q.get("options") or []):
                    return True
    return False


def question_part(text):
    """Item 88: only the sentences that end in a question mark, never a lettered choice line; a word like layout elsewhere in the reply is not a look question."""
    out = []
    for line in text.splitlines():
        if re.match(r"^\s*\W*[A-Z]\.\W", line):
            continue
        out += re.findall(r"[^.!?\n]*\?", line)
    return " ".join(out)


def look_unshown(question, uses):
    return bool(LOOK.search(question) or (LOOK_WEAK.search(question) and LOOK_SCREEN.search(question))) and not pictures_shown(uses)


# item 108: a chat's own memory folder (~/.claude/projects/<project>/memory/) never holds crew rules
MEMORY_DIR = re.compile(r"/\.claude/projects/[^/]+/memory/")
CREW_RULE_WORDS = re.compile(r"\b[Mm]uster\b|\bcrew\b|rules page|\bD-0\d\d\b|\bitem \d{2,3}\b|\b(?:Manager|Builder|Inspector|Designer)[ _]|\b(?:READY|STUCK)\b")
MEMORY_WHY = "the Muster files are the only rulebook (item 108): do not write crew rules into your own memory; if a rule is missing or wrong, send the manager a NEED"

# ---- blocking guards (item 117): a project's own config ("guard" in its profile) says which folders are protected and which public repos it may push to
SECRET_SHAPES = re.compile(
    r"AKIA[0-9A-Z]{16}|\bgh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|\bxox[abprs]-[A-Za-z0-9-]{10,}|\b[sr]k_live_[A-Za-z0-9]{16,}"
    r"|\bsk-ant-[A-Za-z0-9_-]{20,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}|\bAIza[0-9A-Za-z_-]{35}|-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")
ENV_LINE = re.compile(r"^[ \t]*(?:export[ \t]+)?[A-Za-z][A-Za-z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE)[A-Za-z0-9_]*[ \t]*=[ \t]*[\"']?([^\s\"'#]{8,})", re.M)
PLACEHOLDER = re.compile(r"^(?:<.*>|\$.*|\{\{.*|%.*%|\.{3,}|\*{3,}|x{3,}.*|X{3,}.*|your[-_ ].*|my[-_ ].*|changeme.*|change[-_]me.*|replace.*|example.*|placeholder.*|dummy.*|redacted.*|secret|password|token|none|null|todo|test.*|(.)\1{5,})$", re.I)
SECRET_WHY = "a key or secret value is about to be written into %s (item 117): keep it in an ignored .env file, never in a tracked file, a commit message or a message; a placeholder like <your-key> or a .env.example is fine"


def secret_in(text):
    """The first key-shaped or .env-style secret in the text, or None. Placeholders and examples never count."""
    m = SECRET_SHAPES.search(text)
    if m:
        return m.group(0)[:6] + "..."
    for mm in ENV_LINE.finditer(text):
        if not PLACEHOLDER.match(mm.group(1)):
            return mm.group(0).split("=")[0].strip() + "=..."
    return None


def guard_conf():
    g = PROFILE.get("guard")
    return g if isinstance(g, dict) else None


def under(path, folder):
    path, folder = path.replace("\\", "/").rstrip("/"), folder.replace("\\", "/").rstrip("/")
    return path == folder or path.startswith(folder + "/")


def in_protected(path, conf):
    """Inside a protected main folder, but not in a crew copy under its .claude/worktrees (those are the crew's own to change)."""
    p = os.path.normpath(path).replace("\\", "/")
    for f in conf.get("protected_folders") or []:
        if under(p, f) and not under(p, f.rstrip("/") + "/.claude/worktrees"):
            return True
    return False


def repo_of(url):
    m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url.strip())
    return (m.group(1), m.group(2)) if m else None


def repo_public(owner, name):
    """True/False from the GitHub CLI; None when it cannot be told (offline, no gh): then nothing is refused."""
    forced = os.environ.get("MUSTER_GUARD_PUBLIC")  # the self-tests say which repos count as public, with no network
    if forced is not None:
        return name in [x.strip() for x in forced.split(",") if x.strip()]
    try:
        r = subprocess.run(["gh", "repo", "view", "%s/%s" % (owner, name), "--json", "isPrivate", "-q", ".isPrivate"], capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return None
    out = r.stdout.strip()
    return {"false": True, "true": False}.get(out)


def git_words(seg):
    import shlex
    try:
        return shlex.split(seg)
    except ValueError:
        return seg.split()


def guard_shell(cmd, cwd, conf):
    cur = cwd or os.getcwd()
    for seg in re.split(r"&&|\|\||[;&|\n]", cmd):
        w = git_words(seg)
        if not w:
            continue
        if w[0] == "cd" and len(w) > 1:
            cur = os.path.normpath(os.path.join(cur, os.path.expanduser(w[1])))
            continue
        i = 0
        while i < len(w) and (w[i] in ("sudo", "command", "env") or "=" in w[i].split("/")[0]):
            i += 1
        if i >= len(w) or os.path.basename(w[i]) != "git":
            continue
        a = w[i + 1:]
        where = cur
        while a and a[0].startswith("-"):
            if a[0] == "-C" and len(a) > 1:
                where = os.path.normpath(os.path.join(cur, os.path.expanduser(a[1])))
                a = a[2:]
            else:
                a = a[1:]
        if not a:
            continue
        sub, rest = a[0], a[1:]
        if conf.get("protected_folders") and in_protected(where, conf):
            bad = (sub == "reset" or (sub == "stash" and not (rest and rest[0] in ("list", "show")))
                   or (sub == "checkout" and any(r in (".", "-f", "--force") for r in rest))
                   or (sub == "restore" and any(r == "." for r in rest)))
            if bad:
                return "git %s is not run in a protected main folder (item 117): it can throw away other chats' unsaved work; do it in your own copy, or ask the manager" % sub
        if sub == "push":
            pos = [r for r in rest if not r.startswith("-")]
            remote = pos[0] if pos else "origin"
            url = remote
            if not re.search(r"github\.com", remote):
                try:
                    url = subprocess.run(["git", "-C", where, "remote", "get-url", remote], capture_output=True, text=True, timeout=5).stdout.strip()
                except (OSError, subprocess.SubprocessError):
                    url = ""
            rp = repo_of(url)
            if rp:
                named = [x for x in conf.get("public_repos") or [] if isinstance(x, dict) and x.get("name") == rp[1]]
                if named:
                    return "a push to %s goes only through its scanner (item 117): run %s" % (rp[1], named[0].get("scanner") or "the project's scanner")
                if rp[1] not in (conf.get("push_allowed") or []) and repo_public(*rp):
                    return "%s is a public repo and this project does not allow pushing to it (item 117): ask the manager" % rp[1]
    return None


def guard_problem(tool, inp, cwd, conf):
    """Item 117: the blocking hooks. Returns the one-line reason to refuse, or None."""
    if tool == "Bash":
        cmd = str(inp.get("command", ""))
        why = guard_shell(cmd, cwd, conf)
        if why:
            return why
        if re.search(r"\bgit\s+(?:-C\s+\S+\s+)?commit\b", cmd) and secret_in(cmd):
            return SECRET_WHY % "a commit message"
        return None
    if tool == "SendMessage":
        return SECRET_WHY % "a message" if secret_in(str(inp.get("message", ""))) else None
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = str(inp.get("file_path", ""))
        body = " ".join(str(inp.get(k, "")) for k in ("content", "new_string", "new_source"))
        if re.search(r"\.env\.(?:example|sample|template|dist)$", path):
            return None
        if secret_in(body):
            folder = os.path.dirname(path) or "."
            try:
                ignored = subprocess.run(["git", "-C", folder, "check-ignore", "-q", path], capture_output=True, timeout=5).returncode == 0
            except (OSError, subprocess.SubprocessError):
                ignored = False
            if not ignored:
                return SECRET_WHY % "a tracked file"
    return None


def pretool(data, manager):
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}
    root = main_folder(data.get("cwd"))
    conf = guard_conf()
    if conf is not None:
        why = guard_problem(tool, inp, data.get("cwd") or "", conf)
        if why:
            return deny(why)
    if tool in ("Agent", "Task"):
        return helper_problem(inp, manager)
    if tool.endswith("start_session"):
        t = str(inp.get("title", ""))
        if re.match(r"^\s*start\s+\S+_\S+?(?:_\d{3})?\s*$", t, re.I):
            return deny("a started chat's card title is its final name: use the worker's full name without a prefix (not \"%s\")" % t)
        return
    if tool.endswith("__wrap_up"):  # item 119: the app's next-step box is not used; questions go only through Muster's clickable choices
        if str(inp.get("ask", "")).strip() or inp.get("actions"):
            return deny("no question or buttons in the app's wrap-up call (item 119): leave ask and actions out, so no grey next-step box is drawn; put any question to the owner in the chat as lettered choices (***A.*** ... with a blank line between, your pick marked \"my pick\")")
        return
    if tool == "AskUserQuestion":
        if manager:  # item 80, D-037: a card locks the chat until he answers
            return deny("no choice card (it locks the chat until he answers): write the question in the chat as lettered lines, ***A.*** ... one per line with a blank line between, your pick marked \"my pick\"; he answers by typing a letter. Keep working on anything that does not depend on his answer")
        return
    if tool == "SendMessage":
        msg = str(inp.get("message", ""))
        if SOCIAL.match(msg):
            return deny("no 'noted' or 'thanks' replies; send a message only when someone must act")
        if not TEXT_FORM:
            try:
                ok = isinstance(json.loads(msg), dict)
            except ValueError:
                ok = False
            if not ok:
                return deny("a message between chats is a data record (one JSON object with fixed keys), never sentences; see muster/REPORT.md")
            rec = json.loads(msg)
            why = question_order_problem(manager, root, msg, rec, data.get("transcript_path") or "")
            if why:
                return deny(why)
            note = rec.get("note")
            if note is not None and (not isinstance(note, str) or not note.strip() or len(note) > 400 or any(ord(c) < 32 for c in note)
                                     or NOTE_SECRET.search(note)):
                return deny("a note is one plain line of text, 1 to 400 characters, with no key, password or token (detail goes on the board)")
            if rec.get("kind") == "ORDER" and rec.get("action") not in ("ship", "hold", "start"):
                return deny("an ORDER needs action: ship, hold or start (what happens after the work)")
            if rec.get("kind") == "ORDER":
                why = goal_problem(root, str(rec.get("job", "")))
                if why:
                    return deny(why)
            if dup_report(str(inp.get("to", "")), msg, data.get("transcript_path") or ""):
                return deny(DUP_WHY)
            return
        why = question_order_problem(manager, root, msg, None, data.get("transcript_path") or "")
        if why:
            return deny(why)
        if ORDERS_FREE and not re.match(r"^\s*%s\s*:" % FIRST, msg):
            return  # this project has no order shape: only a message that claims to be a report is checked
        bad_report = report_problem(msg)
        bad_order = order_problem(msg)
        if bad_report and bad_order:
            first = msg.strip().splitlines()[0] if msg.strip() else ""
            if re.match(r"^\s*(To|Job)\s*:", first, re.I) or re.search(r"^\s*Job\s*:", msg, re.M | re.I):
                return deny("a message between chats is a six-line report or an order, and this order is wrong: " + bad_order)
            return deny("a message between chats is a six-line report or an order, and this report is wrong: " + bad_report)
        m = re.match(r"^\s*%s: .+ \[ID ([^\]]+)\]" % FIRST, msg)
        if m:
            sent = all_sent_text(data.get("transcript_path") or "")
            if any(("[ID %s]" % m.group(2)) in s for s in sent):
                return deny("this report's ID [%s] was already sent; a repeat is dropped" % m.group(2))
        if m and dup_report(str(inp.get("to", "")), msg, data.get("transcript_path") or ""):
            return deny(DUP_WHY)
        if not bad_order and usage_at_limit(root):
            return deny("the week is at 90% or more (scripts/usage.py exits 3): start no new order; finish and park what is running")
        return
    # item 108, D-027: the Muster files are the only rulebook; no crew chat writes crew rules into its own memory
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        mp = str(inp.get("file_path", "")).replace("\\", "/")
        body = " ".join(str(inp.get(k, "")) for k in ("content", "new_string", "new_source"))
        if MEMORY_DIR.search(mp) and CREW_RULE_WORDS.search(body):
            return deny(MEMORY_WHY)
    if tool in ("Write", "Edit", "NotebookEdit") and not manager:
        p = str(inp.get("file_path", "")).replace("\\", "/")
        if PROTECTED.search(p):
            return deny("only the manager changes the owner's list, decisions, crew list, rules pages and muster/CLAUDE.md (%s)" % os.path.basename(p))
    if tool == "Bash":
        cmd = str(inp.get("command", ""))
        # only paths being added or committed count; a branch such as muster/builder-a-002 is not a path
        for seg in re.split(r"[;&|\n]+", cmd):
            mg = re.match(r"\s*git\s+(?:-C\s+\S+\s+)?(add|commit)\b(.*)", seg)
            if not mg:
                continue
            args = re.sub(r"(\"[^\"]*\"|'[^']*')", " ", mg.group(2))
            if re.search(r"(?<![\w/.-])(muster/?|muster/[^\s]*\.\w+|muster/(rules|handovers|superseded|x-post)/\S*)(?=\s|$)", args):
                return deny("nothing under muster/ is ever saved or committed")
        if CREW_RULE_WORDS.search(re.sub(r"\S*/\.claude/projects/\S*", " ", cmd)) and any(MEMORY_DIR.search(os.path.normpath(os.path.join(data.get("cwd") or os.getcwd(), os.path.expanduser(t))).replace("\\", "/")) for t in shell_write_targets(cmd)):
            return deny(MEMORY_WHY)
        if not manager and PROFILE_PROTECTED is not None:
            base = data.get("cwd") or os.getcwd()
            for tgt in shell_write_targets(cmd):
                full = os.path.normpath(os.path.join(base, os.path.expanduser(tgt))).replace("\\", "/")
                if PROFILE_PROTECTED.search(full):
                    return deny("only the manager changes this project's manager-only files (%s)" % os.path.basename(full))
        if not manager and re.search(r"(>|>>|tee\s+|sed\s+-i\S*\s+(''\s+)?\S*\s*)\s*\S*muster/(OWNERS-LIST|DECISIONS-LOG|CREW|CLAUDE|RULES-PAGE|REPORT)\.md", cmd):
            return deny("only the manager changes the owner's list, decisions, crew list and muster/CLAUDE.md")


# ---- Stop -----------------------------------------------------------------------------------------------------
def card_skipped(path, use_id):
    """True when the choice card got no answer from him: its result is an error ("the user doesn't want to proceed", a rejected
    or interrupted card) or never came back. Then there is nothing to record (item 53)."""
    if not use_id:
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                c = (d.get("message") or {}).get("content", "")
                if d.get("type") == "user" and isinstance(c, list):
                    for b in c:
                        if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") == use_id:
                            body = json.dumps(b.get("content", ""))
                            return bool(b.get("is_error")) or "doesn't want to proceed" in body or "has not answered" in body
    except OSError:
        return False  # an unreadable transcript is never "skipped"
    return True


def recorder_path(root):
    """Where the choice recorder really is: the project's own scripts folder, else this plugin's, else just its name."""
    for cand in (os.path.join(root or ".", "scripts", RECORDER), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", RECORDER)):
        if os.path.isfile(cand):
            return os.path.normpath(os.path.abspath(cand))
    return RECORDER


def status_line(t):
    """Item 123: while the crew works and nothing needs the owner, ONE status line is allowed: "Working: Engine on rug-archive-seed, Site on launch-signs-show"."""
    t = t.strip()
    return len(t.splitlines()) == 1 and len(t) <= 300 and re.match(r"Working: \S.* on \S", t) is not None


def manager_reply_ok(text):
    t = LINK.sub(lambda m: m.group(0), text)
    if status_line(t):
        return True
    if len(t) <= 300 and len(t.strip().splitlines()) <= 3 and re.search(r"\bon the board\b", t, re.I):
        return True  # a short pointer to the news (item 60)
    if re.search(r"\bThe crew is idle\b", t, re.I):
        return len(re.findall(r"^\*\*\*[A-D]\.\*\*\*", t, re.M)) >= 2  # item 124: never a bare idle card; the top next steps ride along as lettered lines
    if re.search(r"\b(I need your yes|needs? your yes|your yes (is needed|to))\b", t, re.I):
        return True
    has_q = "?" in t
    letters = len(re.findall(r"^\*\*\*[A-D]\.\*\*\*", t, re.M))  # lettered lines are the question form (D-037)
    return letters >= 2 or (has_q and letters >= 1)  # two or more lettered choices are the question, with or without a "?" (item 91)


NEWS_UP = re.compile(r"\b(PASS|LIVE|DONE)\b")
NEWS_LO = re.compile(r"\b(shipped|passed|merged|released|progress|landed|finished)\b", re.I)


def owner_form_ok(t):
    """The forms a manager may use to the owner (item 97): a lettered question, a yes he must give, the idle card, the one working status line (never "type in <chat>", item 103)."""
    if status_line(t):
        return True
    if re.search(r"\bThe crew is idle\b", t, re.I):
        return len(re.findall(r"^\*\*\*[A-D]\.\*\*\*", t, re.M)) >= 2  # item 124: never a bare idle card; the top next steps ride along as lettered lines
    if re.search(r"\b(I need your yes|needs? your yes|your yes (is needed|to))\b", t, re.I):
        return True
    letters = len(re.findall(r"^\*\*\*[A-D]\.\*\*\*", t, re.M))
    return letters >= 2 or ("?" in t and letters >= 1)


def is_news(t):
    return bool(NEWS_UP.search(t) or NEWS_LO.search(t))


CHOICE_LINE = re.compile(r"^\*\*\*[A-D]\.\*\*\*\s*(.*)$", re.M)


def question_key(text):
    """The choices of a lettered question, each reduced to its words (no letter, no 'my pick'); empty unless there are two or more."""
    opts = []
    for body in CHOICE_LINE.findall(text):
        b = re.sub(r"\(?\*?my pick\*?\)?", " ", body, flags=re.I)
        b = re.sub(r"[^a-z0-9]+", " ", b.lower()).strip()
        if b:
            opts.append(b[:60])
    return frozenset(opts) if len(opts) >= 2 else frozenset()


def question_repeated(path, text):
    """Item 114: True when this lettered question (nearly) matches one already put to him since his last typed words. A reply the
    Stop hook bounced does not count (the rewrite is the same question); his typed message clears the list."""
    mine = question_key(text)
    if not mine:
        return False
    seen = []  # (key, text) of the manager's earlier lettered messages since he last typed
    user_after = False  # a message came in after the last lettered reply
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                c = (d.get("message") or {}).get("content", "")
                if d.get("type") == "assistant" and isinstance(c, list):
                    t = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
                    k = question_key(t)
                    if k:
                        seen.append((k, t))
                        user_after = False
                elif d.get("type") == "user":
                    if isinstance(c, list):
                        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                            continue
                        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                    c = str(c)
                    if not c.strip():
                        continue
                    user_after = True
                    if re.match(r"\s*Stop hook (feedback|blocking error)", c):
                        if seen:
                            seen.pop()  # the reply that was bounced never counted as asked
                    elif ENDS_TURN.search(c) or NEUTRAL.match(c):
                        pass
                    else:
                        seen = []
    except OSError:
        return False
    if seen and not user_after and seen[-1][1].strip() == text.strip():
        seen.pop()  # this very reply, already in the file
    return any(len(mine & k) / len(mine | k) >= 0.7 for k, _ in seen)


def news_with_question(text):
    """Item 114: news words on a line that is neither a choice nor a question, in a reply that carries a lettered question."""
    if len(CHOICE_LINE.findall(text)) < 2:
        return False
    for ln in text.splitlines():
        if CHOICE_LINE.match(ln.strip()) or "?" in ln:
            continue
        if is_news(ln):
            return True
    return False


QUESTION_WORD = re.compile(r"^\s*(what|why|how|when|where|who|which|can|could|would|will|did|does|do|is|are|was|were|should)\b", re.I)


def owner_questioned(path):
    """Item 115: True when this turn was started by his typed words and they are a question: a '?' or a question word first. An instruction
    ("check the board") is not one. Messages from other chats and app events end his turn; hook feedback and reminders change nothing."""
    last = ""
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
                    if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                        continue
                    c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                c = str(c)
                if not c.strip():
                    continue
                if ENDS_TURN.search(c):
                    last = ""
                elif not NEUTRAL.match(c):
                    last = c
    except OSError:
        pass
    return "?" in last or bool(QUESTION_WORD.match(last))


def choice_recorded(root, item):
    """True when the owner's list (the profile's founder list, else muster/OWNERS-LIST.md) holds a recorded 'Choice (' under that item."""
    rel = (PROFILE or {}).get("founder_list") or "muster/OWNERS-LIST.md"
    try:
        lines = open(os.path.join(root or ".", rel), encoding="utf-8").read().split("\n")
    except OSError:
        return False
    fenced, start = False, None
    for i, l in enumerate(lines):
        if l.strip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced and start is None and re.match(r"^%d\.\s" % item, l):
            start = i
    if start is None:
        return False
    end = start + 1
    while end < len(lines) and not re.match(r"^(\d+\.\s|#)", lines[end]):
        end += 1
    return any(re.match(r"^\s+Choice \(", l) for l in lines[start:end])


def question_order_problem(manager, root, msg, rec, path):
    """Item 115: his question gets an answer, not an order. A manager's order to a worker in a turn his question started is refused unless
    it cites his recorded choice (owner_words item with a Choice line under it)."""
    if not manager or not owner_questioned(path):
        return None
    if rec is not None:
        if rec.get("kind") != "ORDER":
            return None
        item = (rec.get("owner_words") or {}).get("item")
    else:
        if not re.search(r"^\s*(Job|Owner'?s words)\s*:", msg, re.M | re.I):
            return None
        m = re.search(r"\bitem\s+(\d+)", msg, re.I)
        item = int(m.group(1)) if m else None
    if isinstance(item, int) and choice_recorded(root, item):
        return None
    return ("his question gets an answer, not an order (item 115): answer it in plain words; any action it might lead to goes back to him as "
            "lettered choices with your pick, and an order follows only after his recorded choice (cite that list item, with its Choice line)")


def group_unfiled(uses):
    """Group check (item 79): a chat really started this turn (not a card that only proposes one) must be followed by move_sessions into the
    project's group and then a list_sessions read-back."""
    names = [(u.get("name") or "", (u.get("input") or {}).get("initiation")) for u in uses]
    last = -1
    for i, (n, init) in enumerate(names):
        if n.endswith("start_session") and init not in ("offer", "own_initiative"):
            last = i
    if last < 0:
        return False
    moved = next((i for i in range(last + 1, len(names)) if names[i][0].endswith("move_sessions")), None)
    if moved is None:
        return True
    return not any(n.endswith("list_sessions") for n, _ in names[moved + 1:])


REFUSES = re.compile(r"\b(i\s+can['\u2019]?t|i\s+cannot|i\s+won['\u2019]?t|i['\u2019]?m\s+unable|i\s+am\s+unable|i['\u2019]?m\s+not\s+able|i\s+am\s+not\s+able|i\s+(?:would|'d)\s+advise\s+against|i\s+don['\u2019]?t\s+think\s+(?:we|you)\s+should|i\s+(?:am\s+)?not\s+going\s+to|that\s+is\s+not\s+possible|that['\u2019]?s\s+not\s+possible|i\s+disagree|i\s+don['\u2019]?t\s+agree|that['\u2019]?s\s+a\s+bad\s+idea|would\s+be\s+a\s+mistake|i\s+took\s+(?:that|this)\s+to\s+mean|i\s+assumed|i\s+interpreted|you\s+(?:probably|likely|really)\s+mean|what\s+you\s+(?:really|probably)\s+mean|i\s+read\s+(?:that|this)\s+as|i['\u2019]ll\s+do\s+[^.]{0,60}\s+instead|i\s+will\s+do\s+[^.]{0,60}\s+instead)\b", re.I)


def refuses_order(text):
    """True when the reply refuses, argues with or reinterprets a task (item 76). "I can't tell which one" is a question's lead-in, not a refusal."""
    return bool(REFUSES.search(re.sub(r"\bi\s+(?:can['\u2019]?t|cannot)\s+(?:tell|know|see|find|work\s+out|be\s+sure|understand|decide)\b", " ", text, flags=re.I)))


def owner_typed_last(path):
    """True when this turn was started by his own typed message (not an app event, another chat or hook feedback)."""
    typed = False
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
                    if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                        continue
                    c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                c = str(c)
                if not c.strip():
                    continue
                if ENDS_TURN.search(c):
                    typed = False
                elif not re.match(r"^\s*(<system-reminder|Stop hook feedback|Stop hook blocking error)", c, re.I):
                    typed = True
    except OSError:
        pass
    return typed


def open_order_held(root):
    """Item 125: True/False when the board is readable; None when there is no board to judge by. A worker holds an open order when a board entry
    '### <date> | ORDER | <from> -> <to> | <job>' says Status: open and <to> is not a manager."""
    try:
        board = open(os.path.join(root or ".", "muster", "BOARD.md"), encoding="utf-8").read()
    except OSError:
        return None
    for blk in re.split(r"\n(?=### )", board):
        h = re.match(r"### \S+ \| ORDER \| .*? -> ([^|]+?) \|", blk)
        if h and re.search(r"^Status:\s*open", blk, re.M | re.I) and not re.match(r"\s*Manager", h.group(1)):
            return True
    return False


REPORT_KIND = re.compile(r"\"kind\"\s*:\s*\"(READY|PASS|FAIL|DONE|NEED|REPORT|SHIP)\"|^\s*(READY|PASS|FAIL|DONE)\b", re.I | re.M)
CARD_ID = re.compile(r"\"id\"\s*:\s*\"([^\"]+)\"")


def _iso_epoch(ts):
    """'2026-11-17T20:32:30.123Z' as seconds since 1970, or None."""
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)", str(ts or ""))
    if not m:
        return None
    import calendar
    return calendar.timegm(tuple(int(x) for x in m.groups()) + (0, 0, 0))


def idle_changed(path, root):
    """Item 118 (idle-card-when-changed): True when something changed since the manager's last idle card: a new owner message, a new report
    (an id not seen before the card), a ship, or a board change (BOARD.md newer than the card). With no earlier card, or no transcript, True.
    Background, other-chat and repeat-report turns with nothing new are not a change."""
    entries = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    entries.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return True
    seen, card_at, card_ts, changed = set(), None, None, False
    for i, d in enumerate(entries):
        c = (d.get("message") or {}).get("content", "")
        blocks = c if isinstance(c, list) else [{"type": "text", "text": str(c)}]
        text = " ".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
        if d.get("type") == "assistant":
            if re.search(r"\bThe crew is idle\b", text, re.I):
                card_at, card_ts, changed = i, d.get("timestamp"), False
            if card_at is not None and card_at != i:
                for b in blocks:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and re.search(r"\bship\.sh\b|git push\b[^\n]*\bmain\b", str((b.get("input") or {}).get("command", ""))):
                        changed = True
            continue
        if d.get("type") != "user" or any(isinstance(b, dict) and b.get("type") == "tool_result" for b in blocks) or not text.strip():
            continue
        if card_at is None:
            if "<cross-session-message" in text:
                seen.add(CARD_ID.search(text).group(1) if CARD_ID.search(text) else text)
            continue
        if "<cross-session-message" in text:
            key = CARD_ID.search(text).group(1) if CARD_ID.search(text) else text
            if key not in seen and REPORT_KIND.search(text):
                changed = True
            seen.add(key)
        elif not ENDS_TURN.search(text) and not re.match(r"^\s*(<system-reminder|Stop hook feedback|Stop hook blocking error)", text, re.I):
            changed = True
    if card_at is None:
        return True
    if changed:
        return True
    t0 = _iso_epoch(card_ts)
    try:
        return t0 is not None and os.path.getmtime(os.path.join(root or ".", "muster", "BOARD.md")) > t0
    except OSError:
        return False


def idle_card_ok(t):
    """The working status line, the idle card (two or more lettered next steps), or a question or yes he must give."""
    if status_line(t):
        return True
    if re.search(r"\b(I need your yes|needs? your yes|your yes (is needed|to))\b", t, re.I):
        return True
    return len(re.findall(r"^\*\*\*[A-D]\.\*\*\*", t, re.M)) >= 2


def stop(data, manager):
    text = data.get("last_assistant_message") or ""
    # Founder orders (item 76): NOT subject to the once-per-turn pass; the only way through is doing it, or one short question
    if manager and text and refuses_order(text) and owner_typed_last(data.get("transcript_path") or ""):
        return block("he gave you an order in his own words, and a coded rule says you do it: no refusing, no \"cannot\", no arguing, no reinterpreting (item 76). "
                     "Do the task now, or if you are unsure ask him ONE short question, nothing else")
    # Item 125: a manager's turn ends with the idle card or the Working line when no worker holds an open order on the board (even with no text)
    if manager and not data.get("stop_hook_active") and not bounced_this_turn(data.get("transcript_path") or "") \
            and not owner_typed_last(data.get("transcript_path") or "") and open_order_held(main_folder(data.get("cwd"))) is False and not idle_card_ok(text) \
            and idle_changed(data.get("transcript_path") or "", main_folder(data.get("cwd"))):
        return block("no worker holds an open order on the board, and the owner has not been told (item 125): end this turn with the idle card, a bold 'IDLE \u00b7 crew' title, then 'The crew is idle. Here's what's next toward your goal,' and the top next steps as lettered lines (***A.*** ... with your pick marked); or give a worker its next order first")
    if not text or data.get("stop_hook_active") or bounced_this_turn(data.get("transcript_path") or ""):
        return
    uses = turn_blocks(data.get("transcript_path") or "")
    if manager and group_unfiled(uses) and not re.search(r"\bdrag\b", text, re.I):
        return block("you started a chat this turn but did not file it: after start_session call move_sessions into the project's group, then read it back with list_sessions (skill start-the-crew). If the app refuses a step, say so and name what to drag")
    asked = any(u.get("name") == "AskUserQuestion" for u in uses)
    if manager:
        letter = typed_letter_answer(data.get("transcript_path") or "")
        if letter:
            if any(u.get("name") == "Bash" and RECORDER in str((u.get("input") or {}).get("command", "")) for u in uses):
                return  # recorded: a turn that answers his typed letter is handled
            return block("he answered your lettered question by typing \"%s\", and it is not recorded: run %s with the question, every option's text and the one he picked (word for word) under its list item before ending the turn" % (letter, recorder_path(main_folder(data.get("cwd")))))
        idx = max((i for i, u in enumerate(uses) if u.get("name") == "AskUserQuestion"), default=-1)
        if asked and not card_skipped(data.get("transcript_path") or "", uses[idx].get("id")):
            recorded = any(u.get("name") == "Bash" and RECORDER in str((u.get("input") or {}).get("command", "")) for u in uses[idx + 1:])
            if not recorded:
                # never name a flag the project's recorder lacks
                return block("a choice card was answered but not recorded: run %s with his exact answer%s under its list item before ending the turn" % (recorder_path(main_folder(data.get("cwd"))), " (or --no-pick if he skipped the card or typed his own words)" if RECORDER == "record-choice.py" else ""))
            return
        if letters_not_bold_italic(text):
            return block("write each choice letter bold and italic, like ***A.*** red, one line per choice with a blank line between (item 80)")
        if len(re.findall(r"^\*\*\*[A-D]\.\*\*\*", text, re.M)) >= 2 and not re.search(r"\bmy pick\b", text, re.I):
            return block("every lettered question carries your pick: mark one choice *(my pick)* and give a one-line reason, looks included; a pick is advice only and nothing is ordered until he answers (item 100)")
        if len(re.findall(r"^\*\*\*[A-D]\.\*\*\*", text, re.M)) >= 2 and not title_above_choices(text):
            return block("a question to the owner opens with a bold heading line 'WORD \u00b7 job' (like **ASK \u00b7 score-audit**) above the lettered choices, so it draws as a card (item 120)")
        if re.search(r"\bis waiting for you\b|\btype (?:it |your \w+ |anything )?in (?:the |that |this )?[\w .-]*\b(?:chat|window)\b", text, re.I):
            return block("never send the owner to type in a worker's chat (item 103): carrying his approval is your job; forward his quoted go to the worker that asked, by message, and say nothing to him")
        if is_news(text) and not owner_form_ok(text) and not owner_asked(data.get("transcript_path") or ""):
            return block("never tell the owner PASS, LIVE, DONE, shipped or progress news (item 97): his chat gets only a lettered question, a yes he must give, "
                         "or the idle card with its lettered next steps (item 124). When nothing needs him, end this turn with no text at all")
        if news_with_question(text) and not owner_asked(data.get("transcript_path") or ""):
            return block("news does not ride along with a question (item 114): his chat gets the question alone; the news goes to the board only")
        if question_repeated(data.get("transcript_path") or "", text):
            return block("he has already been asked this question and has not answered (item 114): do not put it to him again; keep working on what does not depend on his answer, and end this turn with no text")
        if "?" in text and look_unshown(question_part(text), uses):
            return block("a question about how something looks comes after the pictures: show them to him first in this turn (send-file with render, or card previews), then ask")
        if not manager_reply_ok(text) and not owner_asked(data.get("transcript_path") or "") \
                and not (peer_started(data.get("transcript_path") or "") and short_report(text)):  # a short routine reply to another chat's message is not bounced (item 75)
            return block("to the owner the manager says only a question with its choices as lettered lines (***A.*** ...), a yes he must give, 'The crew is idle' with \"Here's what's next toward your goal,\" and the top next steps as two or more lettered lines (a bare idle card is refused, item 124), or the one status line 'Working: <who> on <job>, ...' while the crew works; never send him to type in a worker's chat, relay his answer yourself (item 103). Rewrite the reply as one of those, or put the news on the board")
        return
    if asked or re.match(r"\s*Messages paused", text):
        return
    body = text.strip()
    bullets = [l for l in body.splitlines() if re.match(r"^\s*[-*•] \S", l)]
    title_ok = bool(re.match(r"^\s*\*\*[^*\n]+\s[·.]\s[^*\n]+\*\*\s*$", body.splitlines()[0])) if body else False
    if not title_ok or not 2 <= len(bullets) <= 3:
        return block("your end-of-turn reply is a card: a bold title line 'WORD · job', then two or three '- ' bullets (what, the result with real numbers, what is left or what you need)")
    if re.match(r"^\s*\*\*(DONE|READY|PASS|FAIL|STUCK|NEED)\b", body):  # item 65: every report reaches the manager as a message
        root = main_folder(data.get("cwd"))
        # SendMessage (to) or the app's older send_message tool (session_id); either reaches the manager
        if not any((u.get("name") == "SendMessage" and recipient_is_manager((u.get("input") or {}).get("to", ""), root))
                   or ((u.get("name") or "").endswith("send_message") and recipient_is_manager((u.get("input") or {}).get("session_id", ""), root)) for u in uses):
            return block("a report reaches the manager as a message as well as the board (item 65): send the manager your %s report with SendMessage (a different ID from any copy to someone else), then end the turn with the card%s" % (body.split()[0].strip("*"), manager_now(root)))


def stood_down(data):
    """The plugin's copy stands down where the project has its own installed copy (.muster-checks/<this file>), so a check never runs twice."""
    me = os.path.abspath(__file__)
    if os.path.basename(os.path.dirname(me)) == ".muster-checks":
        return False
    start = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, ".muster-checks", os.path.basename(me))):
            return True
        if os.path.isfile(os.path.join(d, ".git")):  # a linked worktree's root: the installed copy of the main folder above is not this chat's
            return False
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent


def project_profile(data):
    """The profiles of the project this chat works in, joined: the file named in MUSTER_PROFILE, and in the chat's folder or any
    folder above it both .muster-checks/profile.json and the profile a live stand-in (.muster-checks/live.json) points to. The
    first guard found wins; crew names from all are kept."""
    cands = [os.environ.get("MUSTER_PROFILE")]
    d = os.path.abspath(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
    while True:
        mc = os.path.join(d, ".muster-checks")
        try:
            with open(os.path.join(mc, "live.json"), encoding="utf-8") as fh:
                lj = json.load(fh)
            if isinstance(lj, dict) and lj.get("muster") and lj.get("profile"):
                cands.append(os.path.join(str(lj["muster"]), str(lj["profile"])))
        except (OSError, ValueError):
            pass
        cands.append(os.path.join(mc, "profile.json"))
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    out = {}
    for cand in cands:
        if cand and os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as fh:
                    j = json.load(fh)
            except (OSError, ValueError):
                continue
            if not isinstance(j, dict):
                continue
            if isinstance(j.get("guard"), dict) and "guard" not in out:
                out["guard"] = j["guard"]
            out["crew_names"] = (out.get("crew_names") or []) + [x for x in (j.get("crew_names") or []) if x not in (out.get("crew_names") or [])]
    return out


def guard_main():
    """Item 117, run on its own: the guard in a project's own profile blocks even where the project runs its own older installed copy of
    the checks (the plugin's copy stands down there, and the older copy has no guard)."""
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except Exception:
        return 0
    if data.get("hook_event_name") != "PreToolUse":
        return 0
    prof = project_profile(data)
    conf = prof.get("guard")
    if not isinstance(conf, dict):
        return 0
    crew = CREW_RE
    if prof.get("crew_names"):
        crew = re.compile(CREW_RE.pattern + "|" + "|".join("(?:%s)" % x for x in prof["crew_names"]))
    if not crew.search(first_or_summary(data.get("transcript_path") or "", crew)) and os.environ.get("MUSTER_ASSUME_CREW") != "1":
        return 0
    why = guard_problem(data.get("tool_name", ""), data.get("tool_input") or {}, data.get("cwd") or "", conf)
    if why:
        deny(why)
    return 0


def main():
    if sys.argv[1:2] == ["guard"]:
        return guard_main()
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except Exception:
        return 0
    if stood_down(data):
        return 0
    path = data.get("transcript_path") or ""
    first = first_or_summary(path)
    if not CREW_RE.search(first) and os.environ.get("MUSTER_ASSUME_CREW") != "1":
        return 0
    remember_first(path, first)
    manager = is_manager(first) or os.environ.get("MUSTER_ASSUME_MANAGER") == "1"
    ev = data.get("hook_event_name", "")
    if ev == "PreToolUse":
        pretool(data, manager)
    elif ev == "Stop":
        stop(data, manager)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
