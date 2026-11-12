"""Keyed/graded copies are reused from Drive on a new machine (same bytes -> identical render)."""
import shutil
from pathlib import Path

from scripts import render


class FakeStorage:
    def __init__(self, root):
        self.root = Path(root)

    def list_dir(self, rel):
        d = self.root / rel
        return sorted(p.name for p in d.iterdir()) if d.is_dir() else []

    def fetch(self, rel, local):
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.root / rel, local)
        return local

    def exists(self, rel):
        return (self.root / rel).exists()

    def put_file(self, local, rel, versioned=True):
        (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local, self.root / rel)
        return rel


PLAN = {"scenes": [{"id": "s", "duration_s": 1, "template": "video", "props": {"src": "creators/x/Raw/VID_1.mp4"}}]}


def test_restore_then_save_roundtrip(tmp_path, monkeypatch):
    rem = tmp_path / "remotion"
    monkeypatch.setattr(render, "REMOTION_DIR", rem)
    drive = FakeStorage(tmp_path / "drive")
    (tmp_path / "drive/cache/derived/fx").mkdir(parents=True)
    (tmp_path / "drive/cache/derived/fx/VID_1.key.abc.webm").write_bytes(b"keyed")
    (tmp_path / "drive/cache/derived/fx/OTHER.key.zzz.webm").write_bytes(b"not ours")
    got = render.restore_derived(PLAN, drive)
    assert got == ["fx/VID_1.key.abc.webm"]
    assert (rem / "public/fx/VID_1.key.abc.webm").read_bytes() == b"keyed"
    assert not (rem / "public/fx/OTHER.key.zzz.webm").exists()       # only this plan's clips
    before = render._derived_now()
    (rem / "public/graded").mkdir(parents=True)
    (rem / "public/graded/VID_1.g1.mp4").write_bytes(b"graded")
    sent = render.save_derived(drive, before)
    assert sent == ["graded/VID_1.g1.mp4"]
    assert render.save_derived(drive, before) == []                    # already there: not sent twice


def test_no_storage_is_a_no_op():
    assert render.restore_derived(PLAN, None) == [] and render.save_derived(None, set()) == []
