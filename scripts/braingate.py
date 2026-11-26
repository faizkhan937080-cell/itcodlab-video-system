"""Brain barrier (Faiz 2026-11-22): nothing that changes anything starts until Claude has READ the brain.
`./run brain-read [topic words]` prints state + what other chats did (+ a topic lookup) and writes a marker holding
hashes of what was read. guard.py (PreToolUse) calls gate(): a changing action is blocked when the marker is missing,
older than brain.read_max_age_min, or the shared log got NEW lines since the read (so it must be read again).
Read-only commands are never blocked. Own `sync add` lines refresh the marker (they are not "new news")."""
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

from .common import ROOT

CACHE = Path(os.environ.get("ITCOD_CACHE", str(Path.home() / ".cache" / "itcod")))
MAX_AGE_MIN = 90

# ./run sub-commands that only read or that ARE the brain routine; everything else under ./run changes something
RUN_FREE = {"brain-read", "sync", "mem", "check", "status", "ci", "tools", "catalog", "cost", "gate-check", "doctor", "validate",
            "review-fetch", "test", "inventory", "snapshot", "guard-install", "story", "library"}
READONLY = re.compile(r"^\s*(ls|cat|head|tail|grep|rg|sed\s+-n|wc|find|echo|pwd|date|which|stat|du|df|python3\s+-c|jq|diff|"
                      r"git\s+(status|log|diff|show|fetch|pull|branch|rev-parse|ls-files|ls-tree|stash|restore|reset\s+-q\s+--soft)|"
                      r"gh\s+(run\s+(list|view)|api\s+(?!.*-X\s*(POST|PUT|PATCH|DELETE))))", re.I)
CHANGING = re.compile(r"git\s+(commit|push|add|rm|mv|merge|rebase|checkout\s+-b)\b|gh\s+api\s+.*-X\s*(POST|PUT|PATCH|DELETE)|"
                      r"gh\s+(run\s+(cancel|rerun)|workflow\s+run)|\bmkdir\b|\bmv\b|\bcp\b|\btee\b|npm\s+(install|i|uninstall)|pip3?\s+install|>\s*[\w./-]")


def _marker():
    return CACHE / "brain_read.json"


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _sync_lines():
    from . import chatsync
    b = chatsync.brain()
    if not b:
        return None
    out = []
    for p in chatsync._files(b)[-3:]:
        out += [l for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("- ")]
    return out


def _sync_hash():
    ls = _sync_lines()
    return None if ls is None else _digest("\n".join(ls))


def _run(args):
    r = subprocess.run(["./run", *args], cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    return (r.stdout or "") + (r.stderr or "")


def read_brain(topic=""):
    """Read state + shared log (+ topic lookup). Writes the marker only after the text really came back."""
    from . import chatsync
    state = _run(["mem", "brief"])
    log = chatsync.read(40)                       # pulls the brain repo first
    found = _run(["mem", "find", topic])[:1500] if topic.strip() else ""
    ok = bool(state.strip()) and bool(log.strip()) and "not found here" not in log
    if ok:
        CACHE.mkdir(parents=True, exist_ok=True)
        _marker().write_text(json.dumps({"ts": time.time(), "sync": _sync_hash(), "state": _digest(state), "topic": topic}))
    head = state.strip().splitlines()[:14]
    return ok, "\n".join(["BRAIN STATE (top):", *head, "", "OTHER CHATS (last lines):", *log.splitlines()[-12:],
                          *(["", f"TOPIC '{topic}':", found.strip()[:900]] if found else []),
                          "", "brain-read: OK, marker written" if ok else "brain-read: FAILED (brain repo or state not readable) - fix before working"])


def refresh():
    """After this chat's own sync add: our own line is not news, keep the marker valid."""
    try:
        m = json.loads(_marker().read_text())
        m["sync"] = _sync_hash()
        _marker().write_text(json.dumps(m))
    except (OSError, ValueError):
        pass


def status():
    """(ok, why) for the marker right now."""
    if os.environ.get("ITCOD_NO_BRAIN_GATE"):
        return True, "gate off by env"
    try:
        m = json.loads(_marker().read_text())
    except (OSError, ValueError):
        return False, "you have not read the brain in this session"
    age = (time.time() - m.get("ts", 0)) / 60
    if age > MAX_AGE_MIN:
        return False, f"your last brain read is {int(age)} min old (limit {MAX_AGE_MIN})"
    cur = _sync_hash()
    if cur is not None and m.get("sync") != cur:
        return False, "other chats wrote to the shared log after your read"
    return True, "fresh"


def changing(tool, inp):
    """Does this tool call change something? Read-only calls are never gated."""
    if tool in ("Write", "Edit"):
        p = str(inp.get("file_path", ""))
        return not (p.startswith("/tmp/") or "/.cache/" in p)
    if tool == "SendUserFile":
        return False
    if tool != "Bash":
        return False
    cmd = (inp.get("command") or "").strip()
    m = re.search(r"(?:^|[;&|]\s*)\./run\s+([\w-]+)", cmd)
    if m:
        return m.group(1) not in RUN_FREE
    if CHANGING.search(cmd):
        return True
    return False


def gate(tool, inp):
    if not changing(tool, inp):
        return None
    ok, why = status()
    if ok:
        return None
    return (f"BRAIN BARRIER: {why}. Before changing anything run: ./run brain-read <topic words> "
            "(reads state + what other chats did + the topic). Then retry.")
