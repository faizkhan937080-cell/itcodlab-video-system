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


def test_ears_cache_hit_equals_fresh_and_skips_models(clip, tmp_path, monkeypatch):
    """Same file + same settings: cached transcript/listen/voice are identical to a fresh run and the models are not called."""
    from scripts import audio as audio_mod
    lim = limits()
    lim["analysis"]["listen_sound_events"] = False
    lim["analysis"]["stems"] = False
    lim["analysis"]["ears_cache"] = True
    monkeypatch.setattr(pack, "limits", lambda: lim)
    monkeypatch.setenv("ITCOD_CACHE", str(tmp_path / "cache"))
    calls = {"n": 0}

    def fake_transcribe(wav):
        calls["n"] += 1
        return {"available": True, "language": "en", "segments": [{"start": 0.0, "end": 1.0, "text": "hello there"}],
                "text": "hello there", "coverage_ratio": 0.25}

    monkeypatch.setattr(audio_mod, "transcribe", fake_transcribe)
    first, second = tmp_path / "a", tmp_path / "b"
    pack.run_pipeline(clip, first, job_id="selfcheck", with_transcript=True)
    pack.run_pipeline(clip, second, job_id="selfcheck", with_transcript=True)
    assert calls["n"] == 1
    for n in ("transcript.json", "listen.json", "voice.json", "script_metrics.json"):
        assert (first / n).read_text() == (second / n).read_text(), n
    assert json.loads((second / "timings.json").read_text())
