#!/usr/bin/env python3
"""Idle-crew check (owner's list items 58 and 62): before the manager ends a turn, list the crew's chats that are not
running and match them against open items on the owner's list and open orders on the board. If an idle chat has an
open item that fits it and the manager's last message does not name that chat, the stop is refused once, naming the
chat and the item, so the manager gives it the next order or says "The crew is idle".

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
import time

IDLE_SECONDS = int(os.environ.get("MUSTER_IDLE_SECONDS") or 120)
HERE = os.path.dirname(os.path.abspath(__file__))
INSTALLED = os.path.basename(HERE) == ".muster-checks"


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


def is_manager_chat(data):
    """Installed copy (a project that does not load the plugin): the chat's first message names a manager."""
    pats = PROFILE.get("manager_names") or [r"\bManager_[^_\s]*_\d{3}\b"]
    first = first_message(data.get("transcript_path") or "")
    return any(re.search(p, first) for p in pats)


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
        missing = [f for f in findings(project) if f[2] and f[0].lower() not in msg]
        waiting = [w for w in waiting_chats(crew(project)) if w[0].lower() not in msg]
        holds = [h for h in board_holds(project) if h[0].lower() not in msg]
    except Exception:
        return 0
    if not missing and not waiting and not holds:
        return 0
    lines = ["%s has been idle %d minutes and holds an open item: %s" %
             (n, max(1, secs // 60), "; ".join("%s (%s)" % x for x in f)) for n, secs, f in missing]
    lines += ["%s says it waits on the manager (%s)" % w for w in waiting]
    lines += ["your board line holds %s (%s) but names no decision or item of his: a manager never holds a worker for a "
              "measurement or convenience, and no order of yours outranks his word; release it or cite his words" % h for h in holds]
    print(json.dumps({"decision": "block", "reason":
        "Do not end this turn silently: " + " | ".join(lines) +
        ". Message each one (give it the next order quoting his words, answer what it waits on, or ask why it is idle), "
        "name it in your reply, or if nothing fits say \"The crew is idle\" with the choices as buttons."}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
