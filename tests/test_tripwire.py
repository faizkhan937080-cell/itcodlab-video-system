import json

import pytest

from scripts import guard, tripwire


@pytest.fixture(autouse=True)
def iso(tmp_path, monkeypatch):
    monkeypatch.setattr(tripwire, "CACHE", tmp_path)
    monkeypatch.setattr(tripwire, "HALT", tmp_path / "halt.json")
    monkeypatch.setattr(tripwire, "SCOPE", tmp_path / "scope.json")
    monkeypatch.setattr(tripwire, "RULES", tmp_path / "rules.json")
    monkeypatch.setenv("ITCOD_NO_GUARD_LOG", "1")


class Store:
    def __init__(self):
        self.d = {}

    def write_state(self, rel, row):
        self.d[rel] = row

    def read_json(self, rel):
        return self.d[rel]


def test_missing_cost_row_halts_worker_and_claude(monkeypatch):
    from scripts import costs
    st = Store()
    monkeypatch.setattr(costs, "record", lambda *a, **k: None)
    tripwire.record_checked(st, "j1", "analysis")
    assert tripwire.worker_halt(st) == "tracking_failed"
    assert "HALT" in guard.check_bash("./run wake --reason x")
    assert guard.check_bash("./run check") is None


def test_failed_job_needs_lesson_before_new_work(tmp_path, monkeypatch):
    (tmp_path / "lessons").mkdir()
    (tmp_path / "lessons" / "core.md").write_text("# l\n")
    st = Store()
    tripwire.halt_for_failed_job("j2", "render", st)
    assert "HALT" in guard.check_bash("./run wake")
    assert tripwire.check_halt_write("videos/x.py")
    assert tripwire.check_halt_write("lessons/core.md") is None
    tripwire.add_lesson("M: x | C: y | R: z", "no_x", "guard:FENCE", root=tmp_path)
    assert tripwire.current_halt() is None
    assert guard.check_bash("./run wake") is None
    assert json.loads((tmp_path / "rules.json").read_text())[0]["id"] == "no_x"


def test_lesson_needs_three_parts(tmp_path):
    with pytest.raises(ValueError):
        tripwire.add_lesson("just text", root=tmp_path)


def test_scope_blocks_outside_paths():
    tripwire.set_scope(["scripts/", "tests/"], hours=1)
    assert tripwire.check_scope("scripts/a.py") is None
    assert "SCOPE" in tripwire.check_scope("rulebooks/x.md")
    tripwire.clear_scope()
    assert tripwire.check_scope("rulebooks/x.md") is None


def test_registry_reports_unenforced_and_missing(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "scripts" / "a.py").write_text("def real_guard(): pass\n")
    tripwire.RULES.write_text(json.dumps([
        {"id": "ok", "rule": "r", "enforcer": "guard:real_guard"},
        {"id": "ghost", "rule": "r", "enforcer": "guard:not_there_anywhere"},
        {"id": "open", "rule": "r", "enforcer": "none:"}]))
    probs = " ".join(tripwire.verify_registry(tmp_path))
    assert "ghost" in probs and "open" in probs and "rule ok" not in probs


def test_real_registry_enforcers_exist(monkeypatch):
    from scripts.common import ROOT
    monkeypatch.setattr(tripwire, "RULES", ROOT / "config" / "rules.json")
    bad = [p for p in tripwire.verify_registry() if "not found" in p or "unknown" in p]
    assert bad == []
