#!/usr/bin/env python3
"""Idle-crew check (owner's list items 58 and 62): before the manager ends a turn, list the crew's chats that are not
running and match them against open items on the owner's list and open orders on the board. If an idle chat has an
open item that fits it and the manager's last message does not name that chat, the stop is refused once, naming the
chat and the item, so the manager gives it the next order or says "The crew is idle".

Idle card (item 95): when two or more chats are idle with no open item to order (still idle), the manager's reply must be ONE card
to the owner: a bullet line for each, naming it with "since <when>", "why: <reason>" and "unblocked by: <what>", plus the one lettered
question that unblocks the most (two or more ***A.*** lines, or one with a "?"); said once unchanged, like every news line (item 81).

Crew sweep (item 96), at a manager's first stop of a session and again each day it still holds: every crew member (the crew list's Running
now table, or the profile's crew names) with no board entry from it or to it dated within the last day. Each is named once until it changes.

Run as a Stop hook (hooks.json registration comes later) or by hand:  python3 scripts/idle-check.py [--project DIR] [--list]
Reads only: muster/CREW.md, muster/OWNERS-LIST.md, muster/BOARD.md in the project folder, and the app's session
records (read-only). Writes and sends nothing. Silent (exit 0) when not in a manager folder, on any error, or when
Claude Code is already continuing because of a stop hook (stop_hook_active), so it can never loop.
An idle chat = in the crew's "Running now" table, not archived, with no activity for IDLE_SECONDS (default 120).
A fitting item = an open owner's-list item whose Stands line says "with <chat name>", or an open board ORDER
addressed to that chat. Environment: MUSTER_SESSIONS_DIR (session records folder), MUSTER_IDLE_SECONDS.
"""
import glob
import json
import os
import re
import sys
import tempfile
import time

IDLE_SECONDS = int(os.environ.get("MUSTER_IDLE_SECONDS") or 120)
HERE = os.path.dirname(os.path.abspath(__file__))
INSTALLED = os.path.basename(HERE) == ".muster-checks"


NOREPEAT = " Your reply already reached the owner: do not write it again. Do what this asks, then end with at most one new line, or nothing."


def load_profile():
    for cand in (os.environ.get("MUSTER_PROFILE"), os.path.join(HERE, "profile.json")):
        if cand and os.path.isfile(cand):
            try:
                d = json.load(open(cand, encoding="utf-8"))
                return d if isinstance(d, dict) else {}
            except (OSError, ValueError):
                return {}
    return {}


PROFILE = load_profile()


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


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


def crew(project):
    """[(name, chat id)] from the Running now table of muster/CREW.md."""
    text = read(os.path.join(project, "muster", "CREW.md"))
    m = re.search(r"## Running now(.*?)(?:\n## |\Z)", text, re.S)
    if not m and PROFILE.get("crew_names"):
        return profile_crew()
    rows = []
    for line in (m.group(1) if m else "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        idm = re.search(r"local_[0-9a-f-]{36}", line)
        if len(cells) >= 2 and idm and cells[0] not in ("Name", ""):
            rows.append((cells[0], idm.group(0)))
    return rows


def profile_crew():
    """[(title, chat id)] of the app's non-archived chats whose title is a crew name in the profile (not a manager)."""
    base = sessions_dir()
    pats = [re.compile("^(?:%s)$" % x) for x in PROFILE.get("crew_names", [])]
    mgr = [re.compile(x) for x in PROFILE.get("manager_names", [])]
    rows = []
    for f in glob.glob(os.path.join(base, "*", "*", "local_*.json")) if base else []:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        t = d.get("title") or ""
        if not d.get("isArchived") and any(p.match(t) for p in pats) and not any(m.search(t) for m in mgr):
            rows.append((t, d.get("sessionId") or os.path.basename(f)[:-5]))
    return rows


def waiting_chats(rows):
    """Chats whose last turn summary (the app's own, in its session record) says they are blocked or need something
    and names the manager: [(name, detail)]."""
    base = sessions_dir()
    out = []
    for name, cid in rows:
        hits = glob.glob(os.path.join(base, "*", "*", cid + ".json")) if base else []
        try:
            d = json.load(open(hits[0], encoding="utf-8")) if hits else {}
        except (OSError, ValueError):
            continue
        if d.get("isArchived"):
            continue
        ps = d.get("postTurnSummary") or {}
        txt = " ".join(str(ps.get(k, "")) for k in ("status_detail", "needs_action"))
        if (ps.get("status_category") == "blocked" or ps.get("needs_action")) and re.search(r"manager", txt, re.I):
            out.append((name, txt.strip()[:100]))
    return out


def idle_chats(rows, now):
    base = sessions_dir()
    out = []
    for name, cid in rows:
        hits = glob.glob(os.path.join(base, "*", "*", cid + ".json")) if base else []
        if not hits:
            continue
        try:
            d = json.load(open(hits[0], encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("isArchived"):
            continue
        last = (d.get("lastActivityAt") or 0) / 1000.0
        if last and now - last >= IDLE_SECONDS:
            out.append((name, int(now - last)))
    return out


def open_items(project):
    """[(owner's-list number or board order job, text with 'with <name>' / addressee)]"""
    items = []
    ol = read(os.path.join(project, "muster", "OWNERS-LIST.md"))
    m = re.search(r"(?:^|\n)## Open\n(.*?)(?:\n## |\Z)", ol, re.S)
    for blk in re.split(r"\n(?=\d+\. )", m.group(1) if m else ""):
        num = re.match(r"(\d+)\. ", blk.strip())
        st = re.search(r"^\s*Stands:\s*(.*)$", blk, re.M)
        if num and st and not re.match(r"(done|waiting)", st.group(1), re.I):
            items.append(("item " + num.group(1), st.group(1)))
    board = read(os.path.join(project, "muster", "BOARD.md"))
    for blk in re.split(r"\n(?=### )", board):
        h = re.match(r"### \S+ \| ORDER \| .*? -> ([^|]+?) \| (.*)", blk)
        if h and re.search(r"^Status:\s*open", blk, re.M | re.I):
            items.append(("order " + h.group(2).strip(), "to " + h.group(1).strip()))
    return items


def fits(name, items):
    return [(k, t) for k, t in items if name.lower() in t.lower()]


def last_message(data):
    m = data.get("last_assistant_message")
    if isinstance(m, str):
        return m
    tp = data.get("transcript_path") or ""
    try:
        with open(tp, "rb") as fh:
            fh.seek(max(0, os.path.getsize(tp) - 200000))
            lines = fh.read().decode("utf-8", "ignore").splitlines()
        for line in reversed(lines):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") == "assistant":
                c = (e.get("message") or {}).get("content")
                if isinstance(c, list):
                    return " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                return str(c)
    except OSError:
        pass
    return ""


BOARD_LINE = re.compile(r"^(?:###\s+)?(\d{4}-\d{2}-\d{2})\S*\s*\|\s*[^|]+\|\s*(.*?)\s*->\s*(.*?)\s*\|")


def board_entries(project):
    """[(date, from, to)] of every board entry, Muster's headed entries and PINR's one-line style."""
    paths = [os.path.join(project, "muster", "BOARD.md")]
    if PROFILE.get("board"):
        paths.append(os.path.join(project, PROFILE["board"]))
    out = []
    for p in paths:
        for ln in read(p).splitlines():
            m = BOARD_LINE.match(ln.strip())
            if m:
                out.append((m.group(1), m.group(2), m.group(3)))
    return out


def session_records():
    """[(title, sessionId, archived)] from the app's session records (read-only); [] where they cannot be read."""
    base = sessions_dir()
    out = []
    for f in glob.glob(os.path.join(base, "*", "*", "local_*.json")) if base else []:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append((d.get("title") or "", d.get("sessionId") or os.path.basename(f)[:-5], bool(d.get("isArchived"))))
    return out




def quiet_members(project, today=None):
    """Crew members (not managers, not archived) with no board entry from or to them dated within the last day."""
    import datetime
    today = today or datetime.date.today()
    cutoff = (today - datetime.timedelta(days=1)).isoformat()
    recent = [(f + " " + t).lower() for d, f, t in board_entries(project) if d >= cutoff]
    arch = set(t for t, _, a in session_records() if a)
    mgr = [re.compile(x) for x in (PROFILE.get("manager_names") or [r"\bManager_[^_\s]*?(?:_\d{3})?\b"])]
    out = []
    for name, _ in crew(project):
        if name in arch or any(m.search(name) for m in mgr):
            continue
        if not any(name.lower() in r for r in recent):
            out.append(name)
    return out


LETTERS = re.compile(r"^\s*\*{2,3}[A-D]\.\*{2,3}", re.M)


def card_problem(raw, names):
    """Item 95: what a reply to the owner lacks when two or more workers are idle and still idle. Empty when it is the card."""
    lines = raw.splitlines()
    lacking = []
    for n in names:
        ok = any(n.lower() in l.lower() and re.search(r"\bsince\b", l, re.I) and re.search(r"\bwhy\b", l, re.I) and re.search(r"\bunblock", l, re.I) for l in lines)
        if not ok:
            lacking.append(n)
    letters = len(LETTERS.findall(raw))
    q_ok = letters >= 2 or ("?" in raw and letters >= 1)
    out = []
    if lacking:
        out.append("no line with 'since', 'why' and 'unblocked by' for: " + ", ".join(lacking))
    if not q_ok:
        out.append("no lettered question (two or more ***A.*** lines, or one with a '?') for the choice that unblocks the most")
    return "; ".join(out)


ENDS_TURN = re.compile(r"<cross-session-message|<task-notification|<side-sessions-event|<ci-monitor-event|\[SYSTEM NOTIFICATION", re.I)
NEUTRAL = re.compile(r"^\s*(<system-reminder|Stop hook feedback)", re.I)


def peer_started(path):
    """True when this turn was started by a message from another chat or an app event, not by the owner's typed words (item 75)."""
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


def running_workers(rows, now):
    """Crew chats other than a manager that were active within IDLE_SECONDS (item 103: a worker is on the goal)."""
    base = sessions_dir()
    out = []
    for name, cid in rows:
        if name.startswith("Manager"):
            continue
        hits = glob.glob(os.path.join(base, "*", "*", cid + ".json")) if base else []
        try:
            d = json.load(open(hits[0], encoding="utf-8")) if hits else {}
        except (OSError, ValueError):
            continue
        last = (d.get("lastActivityAt") or 0) / 1000.0
        if hits and not d.get("isArchived") and last and now - last < IDLE_SECONDS:
            out.append(name)
    return out


def goal_set(project):
    return bool(re.search(r'^Goal \(his words\):\s*"[^"]+"', read(os.path.join(project, "muster", "GOAL.md")), re.M))


def findings(project, now=None):
    now = now or time.time()
    items = open_items(project)
    return [(n, secs, fits(n, items)) for n, secs in idle_chats(crew(project), now)]


HOLD_RE = re.compile(r"\baction:?\s*hold\b", re.I)
BASIS_RE = re.compile(r"\b(item\s*\d+|D-\d+|decision\s*\d+|owner|founder|his\s+(?:word|words|choice|yes|go|pick|call|decision|click)|he\s+(?:said|asked|chose|picked|told))", re.I)


def board_holds(project):
    """[(recipient, short text)] for recent manager board lines that hold a worker and name no owner decision or item.
    Muster's board: open entries "### date | KIND | from -> to | job"; line-style boards (PINR): the last 15 lines."""
    out = []
    if PROFILE.get("board_style") == "lines" and PROFILE.get("board"):
        text = read(os.path.join(project, PROFILE["board"]))
        lines = text.splitlines()[-15:]
        for ln in lines:
            m = re.match(r"^\S+\s*\|\s*[A-Za-z]+\s*\|\s*(.*?)\s*->\s*(.*?)\s*\|\s*(.*)$", ln.strip())
            if m and re.search(r"\bManager_", m.group(1)) and HOLD_RE.search(m.group(3)) and not BASIS_RE.search(m.group(3)):
                out.append((m.group(2), m.group(3)[:80]))
        return out
    for blk in re.split(r"\n(?=### )", read(os.path.join(project, "muster", "BOARD.md"))):
        h = re.match(r"### \S+ \| \w+ \| (Manager_[^|]*?) -> ([^|]+?) \|", blk)
        if h and re.search(r"^Status:\s*open", blk, re.M | re.I) and HOLD_RE.search(blk) and not BASIS_RE.search(blk):
            out.append((h.group(2), blk.splitlines()[0][:80]))
    return out


def fnv(text):
    """FNV-1a 64-bit, the same hash as hooks/board-stop.py: both checks keep what the manager was already told in one small file."""
    h = 0xcbf29ce484222325
    for b in text.encode("utf-8"):
        h = ((h ^ b) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h


def told_file(transcript_path, project):
    return os.path.join(os.environ.get("MUSTER_STATE_DIR") or tempfile.gettempdir(), "muster-told-%016x.txt" % fnv(transcript_path or project))


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


def is_manager_chat(data):
    """Installed copy (a project that does not load the plugin): the chat's OWN TITLE names a manager. Never the first
    message's text (a worker's first message names its manager). A title that cannot be read means no: stay silent."""
    pats = PROFILE.get("manager_names") or [r"\bManager_[^_\s]*?(?:_\d{3})?\b"]
    title = chat_title(data.get("transcript_path") or "")
    return bool(title) and any(re.search(p, title) for p in pats)


def main(argv):
    project = os.getcwd()
    if "--project" in argv:
        project = argv[argv.index("--project") + 1]
    elif INSTALLED:
        project = os.path.dirname(HERE)
    if not INSTALLED and not os.path.isfile(os.path.join(project, "muster", "BOARD.md")):
        return 0
    if "--list" in argv:
        for n, secs, f in findings(project):
            print("%s idle %ds: %s" % (n, secs, "; ".join("%s (%s)" % x for x in f) or "no open item"))
        for n, why in waiting_chats(crew(project)):
            print("%s waits on the manager: %s" % (n, why))
        for to, t in board_holds(project):
            print("hold with no owner basis, to %s: %s" % (to, t))
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if data.get("stop_hook_active"):
        return 0
    try:
        if INSTALLED and not is_manager_chat(data):
            return 0
        msg = last_message(data).lower()
        if not msg.strip() and peer_started(data.get("transcript_path") or ""):
            return 0  # item 97: a turn a worker's message started may end with no text; nothing here demands a line then
        tfile = told_file(data.get("transcript_path") or "", project)
        try:
            told = set(open(tfile, encoding="utf-8").read().split())
        except OSError:
            told = set()
        told0 = set(told)

        def fresh(kind, who, what, key):
            """Not named in the reply and not already said once unchanged (item 81): a worker's message must not make the manager repeat itself."""
            fp = "%016x" % fnv("idle|%s|%s|%s" % (kind, who, what))
            if key.lower() in msg:
                told.add(fp)
                return False
            if fp in told:
                return False
            told.add(fp)
            return True
        missing = [f for f in findings(project) if f[2] and fresh("item", f[0], "; ".join("%s (%s)" % x for x in f[2]), f[0])]
        waiting = [w for w in waiting_chats(crew(project)) if fresh("wait", w[0], w[1], w[0])]
        holds = [h for h in board_holds(project) if fresh("hold", h[0], h[1], h[0])]
        # item 95: two or more chats idle with no open item to order: the owner gets one card, not single-line news
        still = [(n, secs) for n, secs, f in findings(project) if not f]
        card = ""
        # item 103: the card is said once per idle stretch (not again when the list of idle chats shifts), and never while a goal is set and a worker is on it
        stretch = "%016x" % fnv("idle|card|stretch")
        if len(still) < 2:
            told.discard(stretch)  # the stretch ended; the next one may speak once
        elif not missing and not (goal_set(project) and running_workers(crew(project), time.time())) and stretch not in told:
            told.add(stretch)
            card = card_problem(last_message(data), [n for n, _ in still])
        # item 96: crew members with no order and no report in the last day (once a day while unchanged)
        import datetime
        day = datetime.date.today().isoformat()
        sweep = []
        if not missing and not os.environ.get("MUSTER_NO_SWEEP"):  # the variable is for the older self-tests only
            sweep += ["%s has had no order and no report on the board for a day" % n for n in quiet_members(project) if fresh("quiet", n, day, n)]
        if told != told0:
            try:
                open(tfile, "w", encoding="utf-8").write("\n".join(sorted(told)) + "\n")
            except OSError:
                pass
    except Exception:
        return 0
    if sweep and not missing and not waiting and not holds and not card:
        print(json.dumps({"decision": "block", "reason":
            "Crew sweep (item 96): " + " | ".join(sweep) + ". Give each quiet "
            "member its next order or find out why it has none; name each in your reply." + NOREPEAT}))
        return 0
    if not missing and not waiting and not holds:
        if card:
            print(json.dumps({"decision": "block", "reason":
                "Two or more workers are idle with nothing to order and the owner has no clear report (item 95). Send him ONE card: a bold title, one bullet "
                "line per worker (%s), each saying 'since <when>', 'why: <reason>' and 'unblocked by: <what>', then the one lettered question "
                "(***A.*** ...) that unblocks the most. Missing: %s." % ("; ".join("%s idle %d min" % (n, max(1, sec // 60)) for n, sec in still), card) + NOREPEAT}))
        return 0
    lines = ["%s has been idle %d minutes and holds an open item: %s" %
             (n, max(1, secs // 60), "; ".join("%s (%s)" % x for x in f)) for n, secs, f in missing]
    lines += ["%s says it waits on the manager (%s)" % w for w in waiting]
    lines += ["your board line holds %s (%s) but names no decision or item of his: a manager never holds a worker for a "
              "measurement or convenience, and no order of yours outranks his word; release it or cite his words" % h for h in holds]
    print(json.dumps({"decision": "block", "reason":
        "Do not end this turn silently: " + " | ".join(lines) +
        ". Message each one (give it the next order quoting his words, answer what it waits on, or ask why it is idle), "
        "name it in your reply, or if nothing fits say \"The crew is idle\" with the choices as buttons." + NOREPEAT}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
