import json
import subprocess
import sys

from scripts.common import ROOT
from scripts.guard import check_bash, check_write

OK = [
    "./run mem find hinglish",
    "python3 -m pytest -q tests/test_guard.py",
    "./run test",
    "git add -A && git commit -q -m 'ffmpeg and rm are mentioned only in text' && git push -q origin main",
    "python3 -c \"import time; time.sleep(5)\"",
    "cat > f.py <<'EOF'\nffmpeg -i x\nrm -rf y\nEOF\npython3 f.py",
    "git push origin --delete review",
    "./run review-fetch job-1 --out /tmp/x",
    "ls -la config && wc -l CLAUDE.md",
]
BAD = [
    "ffmpeg -i a.mp4 b.mp4",
    "cd x && yt-dlp https://example.com",
    "curl -s https://example.com",
    "rm -rf work",
    "echo hi; rclone sync a b",
    "npx remotion render",
    "find . -name '*.tmp' -delete",
    "git reset --hard HEAD~1",
    "git push --force origin main",
    "git push origin --delete main",
    "echo github_pat_" + "A" * 30,
    "sudo rm file",
    "python3 -m pytest -q tests",
    "pytest",
]


def test_allowed_commands_pass():
    for c in OK:
        assert check_bash(c) is None, c


def test_blocked_commands_are_blocked():
    for c in BAD:
        assert check_bash(c), c


def test_secret_in_file_blocked():
    assert check_write("token = ghp_" + "b" * 30)
    assert check_write("normal text") is None


def test_hook_exit_codes():
    def run(payload):
        return subprocess.run([sys.executable, "-m", "scripts.guard"], input=json.dumps(payload), text=True,
                              capture_output=True, cwd=str(ROOT),
                              env={**__import__('os').environ, 'ITCOD_NO_GUARD_LOG': '1'})
    assert run({"tool_name": "Bash", "tool_input": {"command": "ls"}}).returncode == 0
    r = run({"tool_name": "Bash", "tool_input": {"command": "ffmpeg -i a b"}})
    assert r.returncode == 2 and "FENCE" in r.stderr
    assert run({"tool_name": "Read", "tool_input": {}}).returncode == 0
    assert run({}).returncode == 0


def test_card_numbers_use_luhn_but_timestamps_pass():
    assert check_bash("echo 4111 1111 1111 1111")
    assert check_bash("echo 1793903496979") is None  # a 13-digit timestamp is not a card


def test_big_file_not_sent_to_chat_and_big_read_needs_range(tmp_path, monkeypatch):
    from scripts import guard
    big, small = tmp_path / "a.mp4", tmp_path / "b.jpg"
    big.write_bytes(b"0" * (9 * 1024 * 1024))
    small.write_bytes(b"0" * 1000)
    monkeypatch.setattr(guard, "ALLOW_SEND", tmp_path / "none.txt")
    assert guard.check_send([str(big)]) and guard.check_send([str(small)]) is None
    (tmp_path / "ok.txt").write_text(str(big))
    monkeypatch.setattr(guard, "ALLOW_SEND", tmp_path / "ok.txt")
    assert guard.check_send([str(big)]) is None
    txt = tmp_path / "big.log"
    txt.write_text("x" * 50_000)
    assert guard.check_read(str(txt), False) and guard.check_read(str(txt), True) is None
