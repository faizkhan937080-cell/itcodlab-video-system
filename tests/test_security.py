import json
import urllib.error
from pathlib import Path

import pytest

from scripts import netguard, security
from scripts.jobs import Worker
from scripts.netguard import HostBlocked, NetGuard, block_reason, host_key, is_public_host, safe_download, sniff

CFG = netguard.config()


class Clock:
    def __init__(self):
        self.t = 1_800_000_000.0
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def mk(ledger=None):
    c = Clock()
    return NetGuard(CFG, ledger if ledger is not None else {}, clock=c.now, sleep=c.sleep, rng=lambda: 0.0), c


# ------------------------------------------------------------------ polite pacing
def test_host_keys():
    assert host_key("https://www.instagram.com/reel/x/") == "instagram"
    assert host_key("scontent.cdninstagram.com") == "instagram"
    assert host_key("https://api.openverse.org/v1/audio/") == "openverse"
    assert host_key("https://example.org/a.mp3") == "default"


def test_minimum_gap_between_requests_is_kept():
    g, c = mk()
    g.before("instagram")
    c.t += 5
    g.before("instagram")                      # 5 s later: must wait the rest of the 60 s gap
    assert c.slept and abs(c.slept[0] - 55.0) < 1e-6


def test_daily_maximum_stops_then_resumes_next_day():
    g, c = mk()
    cap = CFG["hosts"]["openverse"]["daily_max"]
    for _ in range(cap):
        g.before("openverse")
    with pytest.raises(HostBlocked, match="daily maximum"):
        g.before("openverse")
    c.t += 86400
    g.before("openverse")


def test_block_signal_starts_growing_cooldown_and_never_retries():
    g, c = mk()
    g.before("instagram")
    with pytest.raises(HostBlocked, match="said stop"):
        g.after("instagram", None, "ERROR: HTTP Error 429: Too Many Requests")
    with pytest.raises(HostBlocked, match="cooldown"):
        g.before("instagram")
    c.t += CFG["hosts"]["instagram"]["cooldown_h"][0] * 3600 + 1
    g.before("instagram")                      # first strike: short pause is over
    with pytest.raises(HostBlocked):
        g.after("instagram", 403, "")
    assert g.ledger["instagram"]["blocked_until"] - c.t > CFG["hosts"]["instagram"]["cooldown_h"][0] * 3600   # second strike is longer
    assert g.status()["instagram"]["blocked"] is True


def test_calm_week_forgives_strikes_and_normal_errors_are_not_blocks():
    g, c = mk()
    assert block_reason(200, "all fine") is None and block_reason(404, "not found") is None
    assert block_reason(None, "Please complete the CAPTCHA") and block_reason(503, "")
    g.before("acoustid")
    with pytest.raises(HostBlocked):
        g.after("acoustid", 429, "")
    c.t += 8 * 86400
    g.before("acoustid")
    assert g.ledger["acoustid"]["strikes"] == 0


def test_http_error_from_a_call_trips_the_wire():
    g, _ = mk()
    def boom():
        raise urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)
    with pytest.raises(HostBlocked):
        g.call("openverse", boom)


def test_ledger_is_shared_through_storage(drive):
    g, _ = mk()
    g.attach(drive)
    g.before("openverse")
    g2 = NetGuard(CFG)
    g2.attach(drive)
    assert g2.ledger["openverse"]["count"] == 1


# ------------------------------------------------------------------ files we bring in
class FakeResp:
    def __init__(self, data, headers=None):
        self.data, self.pos, self.headers = data, 0, headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=-1):
        out = self.data[self.pos:self.pos + n] if n >= 0 else self.data[self.pos:]
        self.pos += len(out)
        return out


class FakeOpener:
    def __init__(self, data, headers=None):
        self.resp = FakeResp(data, headers)

    def open(self, req, timeout=None):
        return self.resp


PUBLIC = lambda h: ["93.184.216.34"]   # noqa: E731
MP3 = b"ID3\x03\x00" + b"\x00" * 600


def dl(tmp_path, data, kind="audio", url="https://cdn.example.org/a.mp3", headers=None, **kw):
    g, _ = mk()
    return safe_download(url, tmp_path / "a.bin", kind, guard_=g, resolver=kw.pop("resolver", PUBLIC),
                         opener=FakeOpener(data, headers), **kw)


def test_sniff_kinds():
    assert sniff(MP3)[0] == "audio" and sniff(b"\x89PNG\r\n\x1a\n" + b"0" * 20)[0] == "image"
    assert sniff(b"RIFF\x00\x00\x00\x00WAVEfmt ")[0] == "audio" and sniff(b"\x00\x00\x00\x18ftypmp42" + b"0" * 8)[0] == "video"
    assert sniff(b"MZ\x90\x00")[1] and sniff(b"\x7fELF")[1] and sniff(b"#!/bin/sh")[1] and sniff(b"PK\x03\x04")[1]
    assert sniff(b"<!DOCTYPE html><html>")[0] == "html"


def test_good_file_is_saved_and_bad_ones_are_refused(tmp_path):
    assert dl(tmp_path, MP3).read_bytes() == MP3
    with pytest.raises(ValueError, match="program"):
        dl(tmp_path, b"MZ" + b"\x00" * 600)
    with pytest.raises(ValueError, match="archive"):
        dl(tmp_path, b"PK\x03\x04" + b"\x00" * 600)
    with pytest.raises(ValueError, match="expected audio"):
        dl(tmp_path, b"\x89PNG\r\n\x1a\n" + b"\x00" * 600)
    with pytest.raises(HostBlocked):                               # a web page instead of a file = block / login page
        dl(tmp_path, b"<html><title>Just a moment...</title>")


def test_size_scheme_host_and_private_address_limits(tmp_path):
    big = {"Content-Length": str(500 * 1024 * 1024)}
    with pytest.raises(ValueError, match="limit"):
        dl(tmp_path, MP3, headers=big)
    with pytest.raises(ValueError, match="https"):
        dl(tmp_path, MP3, url="http://cdn.example.org/a.mp3")
    with pytest.raises(ValueError, match="not on the allowed list"):
        dl(tmp_path, MP3, only_hosts=["github.com"])
    with pytest.raises(ValueError, match="public"):
        dl(tmp_path, MP3, resolver=lambda h: ["169.254.169.254"])
    assert not is_public_host("localhost", lambda h: ["127.0.0.1"]) and not is_public_host("x", lambda h: ["10.0.0.5"])
    assert not is_public_host("x", lambda h: ["8.8.8.8", "192.168.1.2"]) and is_public_host("x", lambda h: ["8.8.8.8"])


def test_vet_file(tmp_path):
    ok = tmp_path / "a.mp3"
    ok.write_bytes(MP3)
    assert security.vet_file(ok, "audio")["ok"]
    exe = tmp_path / "b.mp3"
    exe.write_bytes(b"MZ" + b"\x00" * 600)
    v = security.vet_file(exe, "audio")
    assert not v["ok"] and "program" in v["problems"][0]
    assert not security.vet_file(ok, "image")["ok"]
    assert not security.vet_file(ok, "audio", scanner=lambda p: {"status": "infected", "detail": "Eicar-Test"})["ok"]
    assert not security.vet_file(tmp_path / "missing.mp3", "audio")["ok"]
    with pytest.raises(security.SecurityError):
        security.require_safe(exe, "audio")


def test_library_refuses_a_disguised_program(drive, tmp_path):
    from scripts import library
    f = tmp_path / "evil.mp3"
    f.write_bytes(b"MZ" + b"\x00" * 600)
    with pytest.raises(security.SecurityError):
        library.add_file(drive, f, "sfx", "evil", "cc0")


# ------------------------------------------------------------------ repo checks
def test_workflow_audit_finds_the_risky_patterns(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "x.yml").write_text("on: pull_request_target\njobs:\n  a:\n    steps:\n      - uses: someone/tool@v1\n      - uses: actions/checkout@v4\n"
                              "      - run: echo ${{ github.event.issue.title }}\n      - run: curl https://x.sh | sh\n")
    msgs = " | ".join(f["msg"] for f in security.audit_workflows(tmp_path))
    assert "someone/tool@v1 is not pinned" in msgs and "actions/checkout" not in msgs
    assert "pull_request_target" in msgs and "untrusted" in msgs and "runs a script" in msgs and "permissions" in msgs
    (wf / "x.yml").write_text("permissions:\n  contents: read\njobs:\n  a:\n    steps:\n      - uses: actions/checkout@v4\n")
    assert security.audit_workflows(tmp_path) == []


def test_secret_scan_reports_place_not_value(tmp_path):
    f = tmp_path / "cfg.py"
    f.write_text("TOKEN = '" + "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4" + "'\nOK = 1\n")
    hit = security.scan_secrets(tmp_path, [f])
    assert hit == ["cfg.py:1"]
    g = tmp_path / "fine.py"
    g.write_text("x = 1\n")
    assert security.scan_secrets(tmp_path, [g]) == []


def test_integrity_baseline_detects_silent_change(tmp_path, monkeypatch):
    monkeypatch.setattr(security, "CRITICAL", ["a.py"])
    (tmp_path / "a.py").write_text("one")
    base = tmp_path / "base.json"
    security.write_baseline(tmp_path, base)
    assert security.integrity(tmp_path, base) == []
    (tmp_path / "a.py").write_text("two")
    assert "changed since the baseline" in security.integrity(tmp_path, base)[0]["msg"]
    (tmp_path / "a.py").unlink()
    assert "missing" in security.integrity(tmp_path, base)[0]["msg"]


def test_this_repo_is_clean_and_baseline_is_current():
    r = security.report()
    assert r["secrets"] == [] and r["integrity"] == [] and r["verdict"] in ("OK", "WARN"), r


# ------------------------------------------------------------------ jobs: a block stops, it does not retry
def test_block_signal_during_download_ends_in_needs_input_without_retry(drive, tmp_path, monkeypatch):
    from scripts import jobs as jobs_mod
    g, c = mk()
    monkeypatch.setattr(netguard, "_G", g)
    calls = []
    def fake_run(cmd, timeout=None, cwd=None, env=None):
        calls.append(cmd)
        return 1, "", "ERROR: HTTP Error 429: Too Many Requests"
    monkeypatch.setattr("scripts.common.run_cmd", fake_run)
    w = Worker(drive, work=tmp_path / "work")
    monkeypatch.setattr(netguard, "_G", g)          # Worker() attached its own storage to this guard; keep our clock
    g.sleep = lambda s: None
    job = {"id": "reel-AAAAAAAAAAA", "type": "analyze", "mode": "audio", "target": "general", "gate1_approved_by_user": True,
           "link": "https://www.instagram.com/reel/AAAAAAAAAAA/"}
    drive.put_json("jobs/inbox/reel-AAAAAAAAAAA.json", job)
    for _ in range(4):
        w.process_once()
    st = drive.read_json("jobs/state/reel-AAAAAAAAAAA.json")
    assert st["status"] == "NEEDS_INPUT" and "ALERT" in st["note"]
    assert len([c for c in calls if c[0] == "yt-dlp"]) == 1                    # exactly one try, no hammering
    assert drive.exists("jobs/state/_worker_alert.json") and drive.exists("jobs/state/_net.json")
    assert "--sleep-interval" in [x for c in calls for x in c]                 # polite flags were passed
