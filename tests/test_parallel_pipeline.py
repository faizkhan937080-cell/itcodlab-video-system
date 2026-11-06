"""Parallel ears must give exactly the same pack as the serial order (speed without precision loss)."""
import json
import shutil
import subprocess

import pytest

from scripts import pack
from scripts.common import limits


@pytest.fixture()
def clip(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("no ffmpeg")
    p = tmp_path / "c.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=4",
                    "-f", "lavfi", "-i", "sine=frequency=220:duration=4", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p)], check=True)
    return p


def _read(root):
    out = {}
    for name in ("scenes.json", "audio.json", "transcript.json", "script_metrics.json", "voice.json", "listen.json", "audit.json"):
        f = root / name
        out[name] = json.loads(f.read_text().replace(str(root), "<root>")) if f.exists() else None
    return out


def test_parallel_equals_serial(clip, tmp_path, monkeypatch):
    # no heavy models here: transcript off, sound-event model off
    lim = limits()
    lim["analysis"]["listen_sound_events"] = False
    lim["analysis"]["stems"] = False
    monkeypatch.setattr(pack, "limits", lambda: lim)
    res = {}
    for mode in (True, False):
        lim["analysis"]["parallel"] = mode
        root = tmp_path / f"o{mode}"
        pack.run_pipeline(clip, root, job_id="selfcheck", with_transcript=False)
        res[mode] = _read(root)
    assert res[True] == res[False]
    assert res[True]["audio.json"]["has_audio"] is True
    assert res[True]["voice.json"] is not None
