import pytest
from scripts import library as lib


def test_add_find_scan(drive):
    e = lib.add_entry(drive, "sfx", "Whoosh 1", "cc0", "openverse", tags=["whoosh", "swipe"])
    assert e["id"] == "sfx-whoosh-1"
    assert lib.add_entry(drive, "sfx", "Whoosh 1", "cc0")["added"] == e["added"]  # no duplicate
    assert len(lib.load(drive)) == 1
    with pytest.raises(ValueError):
        lib.add_entry(drive, "music", "Song", "by-nc")  # non-commercial refused
    drive.put_text("assets/library/font/Courier Prime Bold.ttf", "x")
    new = lib.scan(drive)
    assert [n["id"] for n in new] == ["font-courier-prime-bold"] and "courier" in new[0]["tags"]
    assert lib.scan(drive) == []  # second scan finds nothing new
    assert [i["id"] for i in lib.find(drive, "swipe")] == ["sfx-whoosh-1"]
    assert "Whoosh 1" in drive.read_text("assets/library/INDEX.md")
