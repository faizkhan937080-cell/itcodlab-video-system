"""Barrier for Claude's own tool calls (Claude Code PreToolUse hook). Exit 2 = blocked, message goes to Claude.
Fence: heavy work (download, ffmpeg, whisper, rclone, render, network) belongs to the worker, never to Claude.
Also blocks deletes and secrets. Pure text checks, no side effects."""
import json
import re
import sys

from .mem import has_secret

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
    if has_secret(cmd):
        return "BARRIER: a secret (token/key/card number) is in this command. Never put secrets in commands."
    flat = _strip_quotes(_strip_heredocs(cmd))
    for pat, msg in RULES:
        if pat.search(flat):
            if "--delete" in flat and ALLOWED_PUSH_DELETE.search(flat.strip()):
                continue
            return msg
    return None


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
        reason = check_write(inp.get("content") or inp.get("new_string") or "")
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
