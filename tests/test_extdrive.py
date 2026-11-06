import json

import pytest

from scripts import extdrive


def test_folder_id_forms():
    fid = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"
    assert extdrive.folder_id(f"https://drive.google.com/drive/folders/{fid}?usp=sharing") == fid
    assert extdrive.folder_id(f"https://drive.google.com/open?id={fid}") == fid
    assert extdrive.folder_id(fid) == fid
    with pytest.raises(ValueError):
        extdrive.folder_id("https://example.com")


def test_index_skips_exact_duplicates_and_types(drive):
    raw = [{"Path": "sfx", "IsDir": True},
           {"Path": "sfx/whoosh.wav", "Size": 100, "ID": "a", "Hashes": {"md5": "m1"}},
           {"Path": "sfx/whoosh copy.wav", "Size": 100, "ID": "b", "Hashes": {"md5": "m1"}},
           {"Path": "fonts/x.ttf", "Size": 50, "ID": "c", "Hashes": {"md5": "m2"}},
           {"Path": "vfx/pop.json", "Size": 5, "ID": "d", "Hashes": {"md5": "m3"}}]
    idx = extdrive.build_index(raw, "acme", "FID123456789")
    assert idx["count"] == 3 and idx["exact_duplicates"] == [{"path": "sfx/whoosh copy.wav", "same_as": "sfx/whoosh.wav"}]
    assert idx["by_type"] == {"audio": 1, "font": 1, "motion": 1} and "NOT CONFIRMED" in idx["licence_note"]
    extdrive.write_index(drive, idx)
    assert json.loads(drive.read_text("assets/external/acme/INDEX.json"))["count"] == 3
    assert [e["id"] for e in extdrive.search(idx, "pop")] == ["d"]


def test_list_folder_uses_root_folder_id_and_explains_failure():
    seen = {}

    class R:
        returncode, stdout, stderr = 0, "[]", ""

    def ok(cmd, **k):
        seen["cmd"] = cmd
        return R()
    extdrive.list_folder("gdrive,root_folder_id=OLD:", "NEWFOLDERID1", run=ok)
    assert seen["cmd"][-1] == "gdrive,root_folder_id=NEWFOLDERID1:"

    class Bad(R):
        returncode, stderr = 1, "403 forbidden"
    with pytest.raises(RuntimeError, match="not shared"):
        extdrive.list_folder("gdrive:", "NEWFOLDERID1", run=lambda *a, **k: Bad())
