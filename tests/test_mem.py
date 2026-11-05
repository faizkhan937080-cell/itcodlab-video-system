import pytest

from scripts import mem


def test_add_rolls_over_and_never_exceeds_limit(tmp_path):
    for i in range(130):
        mem.add("decisions/x", f"line {i}", mem=tmp_path)
    files = sorted(p.name for p in (tmp_path / "decisions").iterdir())
    assert files == ["x-2.md", "x-3.md", "x.md"]
    assert all(len(p.read_text().splitlines()) <= 60 for p in (tmp_path / "decisions").iterdir())
    assert sum(len(p.read_text().splitlines()) for p in (tmp_path / "decisions").iterdir()) == 130 + 2 * 3  # nothing lost


def test_secret_refused(tmp_path):
    with pytest.raises(ValueError):
        mem.add("decisions/x", "token github_pat_" + "A" * 30, mem=tmp_path)
    assert not (tmp_path / "decisions").exists()


def test_find_and_index(tmp_path):
    mem.add("decisions/a", "Faiz wants Hinglish replies", keys="style", mem=tmp_path)
    mem.add("decisions/b", "collages max 10", mem=tmp_path)
    assert mem.find(["hinglish"], roots=[tmp_path])[0].endswith("Faiz wants Hinglish replies")
    idx = mem.build_index(tmp_path)
    assert any(line.startswith("decisions/a.md") and "style" in line for line in idx)
