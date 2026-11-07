from scripts import habits as audit


def test_survey_flags_long_rule_files(tmp_path, monkeypatch):
    (tmp_path / "rulebooks").mkdir()
    (tmp_path / "rulebooks" / "x.md").write_text("a\n" * 61)
    monkeypatch.setattr(audit, "CACHE", tmp_path / "c")
    monkeypatch.setattr(audit, "STATE", tmp_path / "c" / "s.json")
    monkeypatch.setattr(audit, "LOG", tmp_path / "none.log")
    monkeypatch.setattr(audit, "_git", lambda *a: "")
    rows = audit.survey(tmp_path)
    assert any("over 60 lines" in r for r in rows)


def test_guard_log_counts_blocks(tmp_path, monkeypatch):
    log = tmp_path / "g.log"
    log.write_text("100 tokens\n100 tokens\n100 call\n")
    monkeypatch.setattr(audit, "LOG", log)
    assert audit._log_since(50) == {"tokens": 2, "call": 1}
    assert audit._log_since(500) == {}
