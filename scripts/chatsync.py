"""Shared chat log: every chat (Claude Code, claude.ai, Antigravity, any new bot) reads and writes ONE place,
the private brain repo, folder sync/. One file per day, one dated line per durable event.

  ./run sync read [N]            last N lines (default 40) across the newest day files: what other chats did
  ./run sync add <chat> <text..> one line: decision, install, state change, problem+solution. Pulls, appends, pushes.
  ./run sync nudge               one-line reminder for the UserPromptSubmit hook (cheap, never blocks)
Not for brainstorming or chatter (Faiz rule). Secrets are refused. Files stay under 60 lines (rolls to -2, -3).
"""
import os
import re
import subprocess
import time
from pathlib import Path

from .common import ROOT
from .mem import CARD, KEYS, _luhn

MAX_LINES = 58


def brain():
    for c in (os.environ.get("ITCOD_BRAIN"), str(ROOT.parent / "itcodlab-brain"), str(Path.home() / "itcodlab-brain")):
        if c and (Path(c) / ".git").exists():
            return Path(c)
    return None


def _git(b, *a):
    return subprocess.run(["git", "-C", str(b), *a], capture_output=True, text=True, timeout=120)


def _files(b):
    d = b / "sync"
    return sorted(d.glob("*.md"), key=lambda p: p.name) if d.exists() else []


def read(n=40):
    b = brain()
    if not b:
        return "sync: brain repo not found here (set ITCOD_BRAIN or clone itcodlab-brain next to this repo)"
    _git(b, "pull", "--rebase", "--autostash", "-q")
    lines = []
    for p in _files(b)[-3:]:
        lines += [l for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("- ")]
    return "\n".join(lines[-n:]) or "sync: empty so far"


def _slot(b, day):
    d = b / "sync"
    d.mkdir(exist_ok=True)
    i = 1
    while True:
        p = d / (f"{day}.md" if i == 1 else f"{day}-{i}.md")
        if not p.exists() or len(p.read_text(encoding="utf-8").splitlines()) < MAX_LINES:
            return p
        i += 1


def add(chat, text):
    b = brain()
    if not b:
        return False, "brain repo not found"
    if KEYS.search(text) or any(_luhn(re.sub(r"\D", "", m.group())) for m in CARD.finditer(text)):
        return False, "refused: looks like a secret or card number"
    _git(b, "pull", "--rebase", "--autostash", "-q")
    now = time.gmtime()
    p = _slot(b, time.strftime("%Y-%m-%d", now))
    head = "" if p.exists() else (f"---\nname: sync-{p.stem}\ndescription: shared chat log, one line per durable event\n---\n")
    with p.open("a", encoding="utf-8") as f:
        f.write(head + f"- {time.strftime('%Y-%m-%d %H:%MZ', now)} [{chat}] {text.strip()}\n")
    _git(b, "add", "sync")
    _git(b, "commit", "-q", "-m", f"sync: {chat}")
    r = _git(b, "push", "-q", "origin", "HEAD")
    try:
        from . import braingate
        braingate.refresh()
    except Exception:  # noqa: BLE001
        pass
    return True, "saved + pushed" if r.returncode == 0 else "saved locally, push failed (will go with next push)"


def nudge():
    b = brain()
    fs = _files(b) if b else []
    if not fs:
        return "SYNC: shared chat log empty. After any decision/install/state change: ./run sync add <chat> <text>"
    age = int((time.time() - fs[-1].stat().st_mtime) / 60)
    return (f"SYNC: last shared-log entry {age} min ago. Read it: ./run sync read. "
            "If this chat made a decision/install/state change: ./run sync add <chat> <text> (not chatter).")
