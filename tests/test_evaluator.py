from scripts import evaluator as ev

TGT = {"type": "editing", "pacing": {"cuts_per_min": 30}}


def test_pass_when_nothing_differs(monkeypatch):
    monkeypatch.setattr(ev, "clone_report", lambda *a, **k: {"pass": True, "differences": []})
    r = ev.evaluate("editing", TGT, {})
    assert r["verdict"] == "PASS" and r["step"] is None


def test_plan_fix_twice_then_failed(monkeypatch):
    monkeypatch.setattr(ev, "clone_report", lambda *a, **k: {"pass": False, "differences": ["cuts differ"]})
    st = ev.new_state()
    assert ev.evaluate("editing", TGT, {}, state=st)["step"] == "plan"
    assert ev.evaluate("editing", TGT, {}, state=st)["step"] == "plan"
    assert ev.evaluate("editing", TGT, {}, state=st)["verdict"] == "FAILED"


def test_ltx_then_ask_then_minimax_only_after_y(monkeypatch):
    monkeypatch.setattr(ev, "clone_report", lambda *a, **k: {"pass": True, "differences": []})
    st = ev.new_state()
    need = ["realistic kidney shot"]
    assert ev.evaluate("editing", TGT, {}, footage_needs=need, state=st)["step"] == "ltx"
    assert ev.evaluate("editing", TGT, {}, footage_needs=need, state=st)["step"] == "ltx"
    r = ev.evaluate("editing", TGT, {}, footage_needs=need, state=st)
    assert r["verdict"] == "ASK" and "MiniMax" in r["ask"] and st["attempt"]["minimax"] == 0
    ev.approve_minimax(st)
    assert ev.evaluate("editing", TGT, {}, footage_needs=need, state=st)["step"] == "minimax"
    assert ev.evaluate("editing", TGT, {}, footage_needs=need, state=st)["verdict"] == "FAILED"


def test_qa_fail_counts_and_state_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(ev, "clone_report", lambda *a, **k: {"pass": True, "differences": []})
    r = ev.evaluate("editing", None, {}, qa_findings=[{"level": "fail", "code": "x", "msg": "m"}, {"level": "warn"}])
    assert r["verdict"] == "FIX" and len(r["qa_fail"]) == 1
    p = tmp_path / "s.json"
    ev.save_state(p, r["state"])
    assert ev.load_state(p)["attempt"]["plan"] == 1
