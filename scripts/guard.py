"""Barrier for Claude's own tool calls (Claude Code PreToolUse hook). Exit 2 = blocked, message goes to Claude.
Fence: heavy work (download, ffmpeg, whisper, rclone, render, network) belongs to the worker, never to Claude.
Also blocks deletes and secrets. Pure text checks, no side effects."""
import json
import os
import re
import sys
import time
from pathlib import Path

from .mem import has_secret
from . import tripwire

LOG = Path.home() / ".cache" / "itcod" / "guard.log"
TEXT_EXT = {".py", ".md", ".json", ".jsonl", ".log", ".txt", ".csv", ".tsx", ".ts", ".js", ".yml", ".yaml", ".sh", ".html"}
CHAT_MAX_MB, READ_MAX_KB = 8, 40          # defaults; config/limits.json "claude" overrides
ALLOW_SEND = Path.home() / ".cache" / "itcod" / "allow_send.txt"   # path of ONE big file Faiz OK'd in chat

HEAVY = r"(ffmpeg|ffprobe|yt-dlp|youtube-dl|whisper|faster-whisper|rclone|remotion|tesseract|gsutil|curl|wget)"
DELETE = r"(rm|rmdir|unlink|shred|trash)"
SEG = re.compile(r"(?:^|[;&|(\n]|\$\()\s*(?:sudo\s+|env\s+\S+=\S+\s+|nohup\s+|time\s+)*")
RULES = [
    (re.compile(SEG.pattern + r"(?:npx\s+)?" + HEAVY + r"\b"),
     "FENCE: heavy/network tools are the worker's job. Use ./run <command> or send a job."),
    (re.compile(SEG.pattern + DELETE + r"\b"),
     "BARRIER: no deleting from Claude's shell. Faiz-approved scrap goes to Drive trash via the connector, logged in memory."),
    (re.compile(r"find\b.*\s-delete\b|git\s+clean\b|git\s+reset\s+--hard|git\s+push\b.*(--force|\s-f\b)"),
     "BARRIER: destructive git/file command. Ask Faiz."),
    (re.compile(r"git\s+push\b.*(--delete|\s:\S+)"),
     "BARRIER: deleting a remote branch needs Faiz's OK (only `--delete review` is allowed)."),
    (re.compile(SEG.pattern + r"(?:python3?\s+-m\s+)?pytest\b(?![^;&|]*(?:tests/\S+\.py|\s-k\s))"),
     "TOKENS: never run the whole suite raw. `./run test <file>` while fixing, `./run test` once before push (skips if already green)."),
]
ALLOWED_PUSH_DELETE = re.compile(r"git\s+push\s+origin\s+--delete\s+review\s*$")


def _strip_heredocs(cmd):
    out, skip = [], None
    for line in cmd.split("\n"):
        if skip is not None:
            if line.strip() == skip:
                skip = None
            continue
        m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", line)
        out.append(line[:m.start()] if m else line)
        if m:
            skip = m.group(1)
    return "\n".join(out)


def _strip_quotes(cmd):
    return re.sub(r"'[^']*'|\"[^\"]*\"", "''", cmd)


def check_bash(cmd):
    halted = tripwire.check_halt_bash(cmd)
    if halted:
        return halted
    if has_secret(cmd):
        return "BARRIER: a secret (token/key/card number) is in this command. Never put secrets in commands."
    flat = _strip_quotes(_strip_heredocs(cmd))
    for pat, msg in RULES:
        if pat.search(flat):
            if "--delete" in flat and ALLOWED_PUSH_DELETE.search(flat.strip()):
                continue
            return msg
    return None


def _claude_limits():
    try:
        from .common import ROOT
        c = json.loads((ROOT / "config" / "limits.json").read_text(encoding="utf-8")).get("claude", {})
        return float(c.get("chat_file_max_mb", CHAT_MAX_MB)), float(c.get("read_max_kb", READ_MAX_KB))
    except Exception:  # noqa: BLE001
        return CHAT_MAX_MB, READ_MAX_KB


def check_send(files):
    """Big files (4K video etc.) never go into the chat: Drive via script. One-off OK from Faiz = path in allow_send.txt."""
    mb, _ = _claude_limits()
    try:
        ok = ALLOW_SEND.read_text().strip()
    except OSError:
        ok = ""
    for f in files or []:
        try:
            size = os.path.getsize(f)
        except OSError:
            continue
        if size > mb * 1024 * 1024 and os.path.abspath(f) != ok:
            return (f"TOKENS/CHAT: {os.path.basename(f)} is {size // (1 << 20)} MB (> {mb:g} MB). Big files go to Drive by script, "
                    "not the chat. Only if Faiz says so in chat: write the file path into ~/.cache/itcod/allow_send.txt.")
    return None


def check_read(path, has_range):
    """A big text file read whole burns tokens: grep/head/tail or Read with offset+limit."""
    _, kb = _claude_limits()
    if has_range or Path(path or "").suffix.lower() not in TEXT_EXT:
        return None
    try:
        size = os.path.getsize(path)
    except OSError:
        return None
    if size > kb * 1024:
        return f"TOKENS: {os.path.basename(path)} is {size // 1024} KB. Use grep/head/tail, or Read with offset+limit."
    return None


def _log(tag):
    if os.environ.get("ITCOD_NO_GUARD_LOG"):
        return
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.time():.0f} {tag}\n")
    except OSError:
        pass


def check_write(text):
    return ("BARRIER: a secret (token/key/card number) is in this file content. Never store secrets."
            if has_secret(text or "") else None)


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    tool, inp = data.get("tool_name", ""), data.get("tool_input", {}) or {}
    reason = None
    if tool == "Bash":
        reason = check_bash(inp.get("command", ""))
    elif tool in ("Write", "Edit"):
        reason = (check_write(inp.get("content") or inp.get("new_string") or "")
                  or tripwire.check_halt_write(inp.get("file_path"))
                  or tripwire.check_scope(inp.get("file_path")))
    elif tool == "Read":
        reason = check_read(inp.get("file_path", ""), inp.get("offset") is not None or inp.get("limit") is not None)
    elif tool == "SendUserFile":
        reason = check_send(inp.get("files") or [])
    if reason:
        _log(reason.split(":")[0].split()[0].lower())
        print(reason, file=sys.stderr)
        return 2
    _log("call")
    return 0


if __name__ == "__main__":
    sys.exit(main())
