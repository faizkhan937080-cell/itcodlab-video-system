from scripts import ci_brief as C


def test_waits_inside_script_and_prints_one_line(monkeypatch):
    seq = iter([{"status": "in_progress", "id": 1}, {"status": "completed", "conclusion": "success", "id": 1}])
    monkeypatch.setattr(C, "latest", lambda w, r: next(seq))
    t = [0]
    out = C.brief("x.yml", "o/r", wait_min=5, poll_s=30, sleep=lambda s: t.__setitem__(0, t[0] + s), now=lambda: t[0])
    assert out == "x.yml: success run 1"


def test_failed_run_adds_only_last_lines(monkeypatch):
    monkeypatch.setattr(C, "latest", lambda w, r: {"status": "completed", "conclusion": "failure", "id": 2})
    monkeypatch.setattr(C, "_gh", lambda a: (0, "\n".join(f"l{i}" for i in range(100))))
    out = C.brief("x.yml", "o/r", tail=20)
    assert out.splitlines()[0] == "x.yml: failure run 2" and len(out.splitlines()) == 21


def test_timeout_returns_status_not_hang(monkeypatch):
    monkeypatch.setattr(C, "latest", lambda w, r: {"status": "in_progress", "id": 3})
    t = [0]
    out = C.brief("x.yml", "o/r", wait_min=1, poll_s=30, sleep=lambda s: t.__setitem__(0, t[0] + s), now=lambda: t[0])
    assert "still in_progress" in out
