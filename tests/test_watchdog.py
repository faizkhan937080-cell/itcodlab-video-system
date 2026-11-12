"""Watchdog + warm worker (2026-11-12: a run hung 16 min on one step; every new run paid ~3 min setup)."""
import subprocess

import pytest

from scripts import common, jobs, storage


class Clock:
    def __init__(self):
        self.t = 1000.0

    def time(self):
        return self.t

    def sleep(self, s):
        self.t += s


def _worker(results, clock, work_s=0):
    w = jobs.Worker.__new__(jobs.Worker)
    w.lim = {"jobs": {"poll_seconds": 20}}
    it = iter(results)
    state = {"last": results[-1]}

    def process_once():
        clock.t += work_s
        try:
            state["last"] = next(it)
        except StopIteration:
            pass
        return state["last"]
    w.process_once = process_once
    w._self_update = lambda: None
    w.start_watchdog = lambda *a, **k: None
    return w


def test_idle_run_stops_after_grace(monkeypatch):
    c = Clock()
    monkeypatch.setattr(jobs.time, "time", c.time)
    monkeypatch.setattr(jobs.time, "sleep", c.sleep)
    w = _worker([[("a", "AWAIT_PLAN")]], c)
    t0 = c.t
    w.run_until_idle(max_minutes=300, grace_s=180, warm_s=2400)
    assert c.t - t0 < 300           # nothing was done: no reason to stay


def test_run_that_worked_stays_warm(monkeypatch):
    c = Clock()
    monkeypatch.setattr(jobs.time, "time", c.time)
    monkeypatch.setattr(jobs.time, "sleep", c.sleep)
    w = _worker([[("a", "RENDERING")], [("a", "AWAIT_PLAN")]], c)
    t0 = c.t
    w.run_until_idle(max_minutes=300, grace_s=180, warm_s=2400)
    assert 2400 <= c.t - t0 < 2600   # waited for Claude's next plan instead of shutting down


def test_long_call_counts_as_work(monkeypatch):
    c = Clock()
    monkeypatch.setattr(jobs.time, "time", c.time)
    monkeypatch.setattr(jobs.time, "sleep", c.sleep)
    w = _worker([[("a", "AWAIT_PLAN")]], c, work_s=0)
    calls = {"n": 0}
    orig = w.process_once

    def first_is_render():
        calls["n"] += 1
        if calls["n"] == 1:
            c.t += 200          # the whole render happened inside the first call
        return orig()
    w.process_once = first_is_render
    t0 = c.t
    w.run_until_idle(max_minutes=300, grace_s=180, warm_s=2400)
    assert c.t - t0 >= 2400


def test_rclone_timeout_is_code_124_and_exists_refuses_to_guess(monkeypatch):
    def hang(*a, **k):
        raise subprocess.TimeoutExpired(a[0], k.get("timeout"))
    monkeypatch.setattr(storage.subprocess, "run", hang)
    r = storage._rc(["rclone", "lsf", "x:"])
    assert r.returncode == 124
    s = storage.Storage.__new__(storage.Storage)
    s.root, s.remote = None, "x:"
    with pytest.raises(storage.StorageError):
        s.exists("a/b.json")      # "unknown" must not read as "absent" (that could overwrite a file)


def test_stage_beats_the_heart():
    common._BEAT[0] = 0
    with common.stage("t"):
        pass
    assert common.since_beat() < 5
