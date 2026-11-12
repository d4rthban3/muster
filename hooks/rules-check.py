#!/usr/bin/env python3
"""Muster's rules as code (D-027): one self-contained file, so a project that does not load the plugin can copy just this.

It reads one hook event from standard input and acts only in a crew chat (the chat's FIRST message names agents/<role>.md
or <Role>_<project>_<digits>); it is silent in the owner's own chats and on any error. It writes nothing and sends nothing.

PreToolUse (a chat is about to act):
  SendMessage    a message between chats must be a six-line report (FIRST WORD, What, Where with touches:, Why, How, Need,
                 and a Usage line on DONE and READY; a READY shows a test count) or an order (To, Job, Owner's words with
                 his words in quotes, Owns, Out, Done); no "noted/thanks" replies; no ID sent twice; no PASS or FAIL
                 copy to the manager as a message (it goes on the board); no new order while the week is at 90% (usage.py).
  Write/Edit/Bash  only the manager changes the owner's list, the decisions log, the crew list, the rules pages and
                 muster/CLAUDE.md; nobody saves or pushes anything under muster/.
Stop (a chat is about to end its turn; blocks at most once, never loops):
  manager        the reply to the owner is a question with its choices, a yes he must give, "<worker> is waiting for you:
                 type in <chat>", or "The crew is idle"; and an answer to a choice card is recorded (record-choice.py).
  other workers  the reply is a card: a bold "WORD . job" title, then two or three bullets.
Exit 0 always; a refusal is printed as the hook's JSON.
"""
import json
import os
import re
import subprocess
import sys

ROLE = (r"(?:Manager|Builder [A-Za-z]|Designer|Design Inspector|Inspector|Sketchpad|AI Socket|Agent Teacher)")
CREW_RE = re.compile(r"agents[/\\](?:manager|builder|designer|inspector|design-inspector|sketchpad|ai-socket|agent-teacher)\.md|\b%s_[^\s_][^_\n]*_\d{3}\b" % ROLE)
MANAGER_RE = re.compile(r"agents[/\\]manager\.md|\bManager_[^_\n]*_\d{3}\b")


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
    """An order: lines To, Job, Owner's words (his words in quotes), Owns, Out, Done, each starting its label."""
    labels = {}
    for l in text.splitlines():
        m = re.match(r"^\s*(To|Job|Owner'?s words|Owns|Out|Done)\s*:\s*(.*)$", l, re.I)
        if m:
            labels.setdefault(m.group(1).lower().replace("owners", "owner's"), m.group(2))
    for need in ("to", "job", "owner's words", "owns", "out", "done"):
        if need not in labels or not labels[need].strip():
            return "an order needs a filled '%s:' line" % need.capitalize()
    if not re.search(r"[\"“][^\"”]{3,}[\"”]", labels["owner's words"]):
        return "the Owner's words line must quote his words in quotation marks"
    return None


def _token_is_manager(tok):
    """tok is a crew name or an agents/<role>.md path, as CREW_RE matched it."""
    if re.match(r"agents[/\\]", tok):
        return re.search(r"agents[/\\]manager\.md$", tok) is not None
    return re.fullmatch(r"Manager_[^_\n]*_\d{3}", tok) is not None or any(
        re.fullmatch(x, tok) for x in PROFILE.get("manager_names", []))


def is_manager(first):
    """Only the chat's OWN name makes it the manager. Its own name is the first crew name that follows 'Job:', 'You are' or 'I am' (a summary says "I am **Manager_X_001**") in
    its starting note (every such place is tried: 'You are operating in a git worktree' holds no name). Else the first
    agents/<role>.md it names, else a Job line that says 'go-between' or 'record keeper'. A crew name that is merely
    mentioned ("report to Manager_X_002", "Manager_X_001 gives every order") never makes a chat the manager."""
    best = None
    for lead in (r"\bJob:\s*[*`]{0,2}", r"\b(?:you are|i am|i'm)\s+(?:the\s+)?[*`]{0,2}"):
        for m in re.finditer(lead, first, re.I):
            c = CREW_RE.match(first, m.end())
            if c and (best is None or m.start() < best[0]):
                best = (m.start(), c.group(0))
                break
    if best:
        return _token_is_manager(best[1])
    m = re.search(r"agents[/\\](?:manager|builder|designer|inspector|design-inspector|sketchpad|ai-socket|agent-teacher)\.md", first)
    if m:
        return _token_is_manager(m.group(0))
    return re.search(r"\bJob:[^\n]*(go-between|record keeper)", first, re.I) is not None


# ---- reading the event ----------------------------------------------------------------------------------------
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


def all_sent_text(path):
    """The text of messages that were really sent: a SendMessage whose result came back without an error. A call still
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
                        calls[b.get("id")] = str((b.get("input") or {}).get("message", ""))
                    elif d.get("type") == "user" and b.get("type") == "tool_result":
                        done.add(b.get("tool_use_id"))
                        rc = b.get("content", "")
                        rc = " ".join(x.get("text", "") for x in rc if isinstance(x, dict)) if isinstance(rc, list) else str(rc)
                        if b.get("is_error") or rc.lstrip().startswith("Muster rule:") or "Muster rule:" in rc[:200]:
                            failed.add(b.get("tool_use_id"))
    except OSError:
        pass
    return [t for i, t in calls.items() if i in done and i not in failed]


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


ASKING = re.compile(r"^\s*(what|why|how|when|where|who|which|can|could|would|will|did|does|do|is|are|was|were|should|tell|show|explain|look|check|find|list|give|say|read|open|run)\b|\b(tell me|show me|let me know|how come|what's|look at)\b", re.I)


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


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": "Muster rule: " + reason}}))


def block(reason):
    print(json.dumps({"decision": "block", "reason": "Muster rule: " + reason}))


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


def recipient_is_manager(to, root):
    to = str(to)
    if re.search(r"\bManager", to):
        return True
    try:
        for l in open(os.path.join(root, "muster", "CREW.md"), encoding="utf-8"):
            if to and to in l and l.lstrip("| ").startswith("Manager"):
                return True
    except OSError:
        pass
    return False


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


LOOK = re.compile(r"\b(looks?|looking|colou?rs?|designs?|mock-?ups?|layouts?|fonts?|styl(?:e|es|ing)|themes?|icons?|logos?|pictures?|images?|screenshots?|appearance|visuals?|dark mode|light mode|spacing|banners?)\b", re.I)
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


def look_unshown(question, uses):
    return bool(LOOK.search(question)) and not pictures_shown(uses)


def pretool(data, manager):
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}
    root = main_folder(data.get("cwd"))
    if tool in ("Agent", "Task"):
        return helper_problem(inp, manager)
    if tool == "AskUserQuestion":
        if manager and look_unshown(json.dumps(inp.get("questions") or []),
                                    turn_blocks(data.get("transcript_path") or "") + [{"name": "AskUserQuestion", "input": inp}]):
            return deny("a question about how something looks comes after the pictures: show them first (send-file with render, or the card's option previews), then ask")
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
            return
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
            if re.match(r"^\s*(PASS|FAIL)\b", msg) and recipient_is_manager(inp.get("to", ""), root):
                return deny("a PASS or FAIL copy for the manager goes on the board only, not as a message")
        if not bad_order and usage_at_limit(root):
            return deny("the week is at 90% or more (scripts/usage.py exits 3): start no new order; finish and park what is running")
        return
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


def manager_reply_ok(text):
    t = LINK.sub(lambda m: m.group(0), text)
    if len(t) <= 300 and len(t.strip().splitlines()) <= 3 and re.search(r"\bon the board\b", t, re.I):
        return True  # a short pointer to the news (item 60)
    if re.search(r"\bThe crew is idle\b", t, re.I):
        return True
    if re.search(r"\bis waiting for you\b.*\btype in\b", t, re.I | re.S):
        return True
    if re.search(r"\b(I need your yes|needs? your yes|your yes (is needed|to))\b", t, re.I):
        return True
    has_q = "?" in t
    has_choices = bool(re.search(r"^\*\*[A-D]\.\*\*", t, re.M)) or bool(re.search(r"\bbuttons?\b", t, re.I))
    return has_q and has_choices


def stop(data, manager):
    text = data.get("last_assistant_message") or ""
    if not text or data.get("stop_hook_active") or bounced_this_turn(data.get("transcript_path") or ""):
        return
    uses = turn_blocks(data.get("transcript_path") or "")
    asked = any(u.get("name") == "AskUserQuestion" for u in uses)
    if manager:
        idx = max((i for i, u in enumerate(uses) if u.get("name") == "AskUserQuestion"), default=-1)
        if asked and not card_skipped(data.get("transcript_path") or "", uses[idx].get("id")):
            recorded = any(u.get("name") == "Bash" and RECORDER in str((u.get("input") or {}).get("command", "")) for u in uses[idx + 1:])
            if not recorded:
                return block("a choice card was answered but not recorded: run %s with his exact answer (or --no-pick if he skipped the card or typed his own words)" % recorder_path(main_folder(data.get("cwd"))) + " under its list item before ending the turn")
            return
        if "?" in text and look_unshown(text, uses):
            return block("a question about how something looks comes after the pictures: show them to him first in this turn (send-file with render, or card previews), then ask")
        if not manager_reply_ok(text) and not owner_asked(data.get("transcript_path") or ""):
            return block("to the owner the manager says only a question with its choices as buttons, a yes he must give, '<worker> is waiting for you: type in <chat>', or 'The crew is idle'. Rewrite the reply as one of those, or put the news on the board")
        return
    if asked or re.match(r"\s*Messages paused", text):
        return
    body = text.strip()
    bullets = [l for l in body.splitlines() if re.match(r"^\s*[-*•] \S", l)]
    title_ok = bool(re.match(r"^\s*\*\*[^*\n]+\s[·.]\s[^*\n]+\*\*\s*$", body.splitlines()[0])) if body else False
    if not title_ok or not 2 <= len(bullets) <= 3:
        return block("your end-of-turn reply is a card: a bold title line 'WORD · job', then two or three '- ' bullets (what, the result with real numbers, what is left or what you need)")


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
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except Exception:
        return 0
    if stood_down(data):
        return 0
    path = data.get("transcript_path") or ""
    first = first_message(path)
    if not CREW_RE.search(first) and os.environ.get("MUSTER_ASSUME_CREW") != "1":
        return 0
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
