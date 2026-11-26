"""Brain barrier + auto-feed: blocks changing actions until the brain is read, notices new news, feeds minor events."""
import json
import subprocess
import time

import pytest

from scripts import autofeed, braingate, chatsync


@pytest.fixture
def brain(tmp_path, monkeypatch):
    b = tmp_path / "brain"
    (b / "sync").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(b)], check=True)
    subprocess.run(["git", "-C", str(b), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(b), "config", "user.name", "t"], check=True)
    (b / "sync" / "2026-11-22.md").write_text("---\nname: x\n---\n- 2026-11-22 00:00Z [other] first line\n")
    subprocess.run(["git", "-C", str(b), "add", "."], check=True)
    subprocess.run(["git", "-C", str(b), "commit", "-qm", "i"], check=True)
    monkeypatch.setenv("ITCOD_BRAIN", str(b))
    monkeypatch.delenv("ITCOD_NO_BRAIN_GATE", raising=False)
    monkeypatch.setattr(braingate, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(autofeed, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(autofeed, "SEEN", tmp_path / "cache" / "seen.json")
    monkeypatch.setattr(braingate, "_run", lambda args: "state line 1\nstate line 2\n" if args[:2] == ["mem", "brief"] else "hit")
    return b


COMMIT = {"command": "git commit -qm 'x'"}


def test_changing_action_blocked_without_read(brain):
    assert "BRAIN BARRIER" in braingate.gate("Bash", COMMIT)
    assert "BRAIN BARRIER" in braingate.gate("Write", {"file_path": "/home/x/itcodlab-video-system/a.py"})
    assert "BRAIN BARRIER" in braingate.gate("Bash", {"command": "./run new-job --type analyze"})


def test_read_only_and_brain_commands_never_blocked(brain):
    for c in ("ls -la", "git status -sb", "git log --oneline -3", "./run sync read", "./run mem brief", "./run brain-read topic",
              "./run ci fast", "gh run list -w fast", "grep -n x file", "./run gate-check looked j --score 7"):
        assert braingate.gate("Bash", {"command": c}) is None, c
    assert braingate.gate("Write", {"file_path": "/tmp/x.txt"}) is None


def test_after_real_read_allowed_and_marker_has_hashes(brain):
    ok, text = braingate.read_brain("reel")
    assert ok and "other" in text and "OK, marker written" in text
    m = json.loads(braingate._marker().read_text())
    assert m["sync"] and m["state"] and m["topic"] == "reel"
    assert braingate.gate("Bash", COMMIT) is None


def test_failed_read_writes_no_marker(brain, monkeypatch):
    monkeypatch.setattr(braingate, "_run", lambda args: "")
    ok, text = braingate.read_brain()
    assert not ok and "FAILED" in text and not braingate._marker().exists()


def test_stale_read_blocks(brain):
    braingate.read_brain()
    m = json.loads(braingate._marker().read_text())
    m["ts"] = time.time() - 3 * 3600
    braingate._marker().write_text(json.dumps(m))
    assert "min old" in braingate.gate("Bash", COMMIT)


def test_other_chat_news_forces_reread_but_own_add_does_not(brain):
    braingate.read_brain()
    p = brain / "sync" / "2026-11-22.md"
    p.write_text(p.read_text() + "- 2026-11-22 01:00Z [other] news\n")
    assert "other chats wrote" in braingate.gate("Bash", COMMIT)
    braingate.read_brain()
    assert braingate.gate("Bash", COMMIT) is None
    ok, _ = chatsync.add("me", "own line")          # own line must not demand a re-read
    assert ok and braingate.gate("Bash", COMMIT) is None


def test_autofeed_lines():
    assert autofeed.line_for("Bash", {"command": "git commit -qm \"skilltest: camera back\" && git push"}).startswith("commit: skilltest")
    assert "fast.yml" in autofeed.line_for("Bash", {"command": "gh api -X POST repos/o/r/actions/workflows/fast.yml/dispatches -f ref=main -f 'inputs[spec]=trigger/sample/a.json'"})
    assert autofeed.line_for("Bash", {"command": "./run new-job --type analyze --link x"}).startswith("run: ./run new-job")
    assert autofeed.line_for("Bash", {"command": "ls -la"}) is None
    assert autofeed.line_for("Write", {"file_path": "/home/claude/itcodlab-video-system/rulebooks/24-director.md"}) == "edited rulebooks/24-director.md"
    assert autofeed.line_for("Write", {"file_path": "/tmp/a.txt"}) is None
    assert autofeed.line_for("SendUserFile", {"files": ["/tmp/v.mp4"]}) == "sent to Faiz: v.mp4"


def test_autofeed_dedupes_and_really_writes(brain):
    assert autofeed.fresh("commit: a") and not autofeed.fresh("commit: a")
    ok, msg = chatsync.add("chat-auto", "commit: a")
    day = time.strftime("%Y-%m-%d", time.gmtime())
    assert ok and "commit: a" in (brain / "sync" / (day + ".md")).read_text()
