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
    w0 = None  # a slow Drive scan (no stage) is not work
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
            with common.stage("render"):   # the whole render happened inside the first call
                c.t += 200
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


def test_rate_limit_is_retried_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def flaky(cmd, **k):
        calls["n"] += 1
        if calls["n"] < 3:
            return subprocess.CompletedProcess(cmd, 1, "", 'googleapi: Error 403: RATE_LIMIT_EXCEEDED')
        return subprocess.CompletedProcess(cmd, 0, "ok", "")
    slept = []
    monkeypatch.setattr(storage.subprocess, "run", flaky)
    import time as _t
    monkeypatch.setattr(_t, "sleep", lambda s: slept.append(s))
    r = storage._rc(["rclone", "cat", "x:a"])
    assert r.returncode == 0 and calls["n"] == 3 and slept == [10, 30]


def test_drive_error_on_one_job_does_not_crash_the_pass(monkeypatch):
    w = jobs.Worker.__new__(jobs.Worker)

    class S:
        def list_dir(self, rel):
            return ["a.json", "b.json"] if rel in ("jobs/inbox", "jobs/state") else []

        def read_json(self, rel):
            if rel == "jobs/state/a.json":
                raise storage.StorageError("cannot read: RATE_LIMIT_EXCEEDED")
            if rel.startswith("jobs/inbox/"):
                return {"id": rel.split("/")[-1][:-5], "type": "render"}
            return {"id": "b", "status": "AWAIT_GATE5"}

        def exists(self, rel):
            return True

        def list_meta(self, rel):
            return {n: "t1" for n in self.list_dir(rel)}
    w.storage = S()
    w.step = lambda job, st: False
    res = w.process_once()
    assert res == [("b", "AWAIT_GATE5")]          # a skipped, b handled, no crash
    assert w.process_once() == [("b", "AWAIT_GATE5")] and "b" in w._waiting   # b served from the waiting cache


def test_unchanged_files_are_not_read_again():
    w = jobs.Worker.__new__(jobs.Worker)
    reads = []

    class S:
        def list_meta(self, rel):
            return {"j.json": "t1"} if rel in ("jobs/inbox", "jobs/state") else {}

        def read_json(self, rel):
            reads.append(rel)
            return {"id": "j", "type": "render"} if rel.startswith("jobs/inbox/") else {"id": "j", "status": "RENDERING_PREVIEW"}
    w.storage = S()
    w.step = lambda job, st: False
    w.process_once()
    w.process_once()
    assert reads == ["jobs/inbox/j.json", "jobs/state/j.json"]      # second pass: nothing changed, nothing read
