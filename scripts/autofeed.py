"""Auto-feed the brain (Faiz 2026-11-22): minor things Claude does are written to the shared log WITHOUT being told.
PostToolUse hook: reads the tool call from stdin, turns the durable ones into one line, and adds it to the brain repo
sync/ log in a detached process (the hook returns at once). Same line twice = skipped. Secrets are refused by chatsync.
Durable = commits, workflow dispatches, job/approval/library commands, edits to rules/config/code, files sent to Faiz."""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

CACHE = Path(os.environ.get("ITCOD_CACHE", str(Path.home() / ".cache" / "itcod")))
SEEN = CACHE / "autofeed_seen.json"
EDIT_DIRS = ("rulebooks/", "lessons/", "config/", "scripts/", "remotion/src/", ".claude/", "schemas/", "tests/", ".github/")
RUN_LOG = {"new-job", "approve", "bulk-jobs", "wake", "render-local", "analyze-local", "sample-shard", "sample-join", "sample"}


def line_for(tool, inp):
    """The one-line event for this tool call, or None if it is not worth recording."""
    if tool == "Bash":
        cmd = (inp.get("command") or "")
        m = re.search(r"git\s+commit\b.*?-\w*m\s+(?:\"([^\"\n]+)|'([^'\n]+)|\"?\$\(cat <<'?EOF'?\n(.+?)\n)", cmd, re.S)
        if m:
            return "commit: " + next(g for g in m.groups() if g).strip()[:140]
        m = re.search(r"workflows/([\w.-]+)/dispatches.*?spec\]=(\S+)", cmd, re.S) or re.search(r"workflows/([\w.-]+)/dispatches", cmd)
        if m:
            return f"workflow dispatched: {m.group(1)} " + (m.group(2).strip("'\"")[:80] if m.lastindex and m.lastindex > 1 else "")
        m = re.search(r"\./run\s+([\w-]+)((?:\s+[^;&|\n]+)?)", cmd)
        if m and (m.group(1) in RUN_LOG or (m.group(1) == "library" and re.search(r"\blibrary\s+(add|fetch)\b", cmd))):
            return ("run: ./run " + m.group(1) + m.group(2))[:160]
        return None
    if tool in ("Write", "Edit"):
        p = str(inp.get("file_path", ""))
        rel = p.split("itcodlab-video-system/", 1)[-1] if "itcodlab-video-system/" in p else p
        return f"edited {rel}" if rel.startswith(EDIT_DIRS) else None
    if tool == "SendUserFile":
        fs = inp.get("files") or []
        return "sent to Faiz: " + ", ".join(os.path.basename(f) for f in fs)[:120] if fs else None
    return None


def _seen():
    try:
        return json.loads(SEEN.read_text())
    except (OSError, ValueError):
        return {}


def fresh(text, now=None):
    """True the first time within 30 min (edits of the same file are one event, not twenty)."""
    now = now or time.time()
    k = hashlib.sha256(text.encode()).hexdigest()[:14]
    s = {a: t for a, t in _seen().items() if now - t < 1800}
    if k in s:
        return False
    s[k] = now
    CACHE.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(s))
    return True


def feed(chat, text):
    """Detached: the hook must not wait for git pull/push."""
    subprocess.Popen([sys.executable, "-c", "import sys;from scripts import chatsync;chatsync.add(sys.argv[1],sys.argv[2])", chat, text],
                     cwd=str(Path(__file__).resolve().parent.parent), start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    try:
        d = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    text = line_for(d.get("tool_name", ""), d.get("tool_input", {}) or {})
    if text and fresh(text) and not os.environ.get("ITCOD_NO_AUTOFEED"):
        feed(os.environ.get("ITCOD_CHAT", "chat-auto"), text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
