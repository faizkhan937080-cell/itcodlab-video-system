"""Alert, not a wall: Faiz's words let a not-cleared item through, and it stays marked."""
import pytest

from scripts import clients, library


def test_gate_alerts_then_passes_with_faiz_words():
    credits = [{"name": "meme-clip", "licence": "needs-licence"}, {"name": "m", "licence": "cc0"}]
    assert clients.licence_blockers(credits) == ["meme-clip"]
    new, marked = clients.accept_risk(credits, "meme 3 sec, my page")
    assert marked == ["meme-clip"] and clients.licence_blockers(new) == []
    assert new[0]["risk_accepted"]["by"] == "faiz" and new[0]["risk_accepted"]["reason"] == "meme 3 sec, my page"
    assert "risk_accepted" not in new[1]                    # cleared items are never marked
    assert clients.licence_blockers(credits) == ["meme-clip"]   # input not changed


def test_library_add_needs_words_for_uncleared(drive):
    with pytest.raises(ValueError) as e:
        library.add_entry(drive, "sfx", "vine boom", "unknown", "https://example.org/x")
    assert str(e.value).startswith("ALERT")
    ent = library.add_entry(drive, "sfx", "vine boom", "unknown", "https://example.org/x", accept_risk="Faiz: use it")
    assert ent["risk_accepted"]["by"] == "faiz"
    assert library.add_entry(drive, "sfx", "airhorn", "cc0")["licence"] == "cc0"


def test_write_json_local_accepts_numpy(tmp_path):
    import json
    import numpy as np
    from scripts.common import write_json_local
    p = write_json_local(tmp_path / "x.json", {"a": np.int64(3), "b": np.float32(1.5), "c": np.array([1, 2]), "d": {1, 2}})
    assert json.loads(p.read_text()) == {"a": 3, "b": 1.5, "c": [1, 2], "d": [1, 2]}
