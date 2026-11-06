"""Analysis pipeline checks on a synthetic video whose real cuts are known."""
import json

from PIL import Image


def test_scene_boundaries_match_known_cuts(analysed):
    scenes = analysed["scenes"]
    starts = [round(s["start_s"]) for s in scenes]
    for expected in (4, 8, 12, 16, 19):
        assert expected in starts, f"missing cut at {expected}s, got {starts}"
    kinds = [s["transition_in"] for s in scenes[1:]]
    assert kinds.count("dissolve") == 1, kinds
    dissolve = next(s for s in scenes if s["transition_in"] == "dissolve")
    assert 16.5 < dissolve["start_s"] < 18.5
    assert 6 <= len(scenes) <= 8


def test_dedup_merges_repeated_looks(analysed):
    by_id = {s["id"]: s for s in analysed["scenes"]}
    # scenes 1&3 are the same look (A), scenes 2&4 the same look (B)
    assert by_id[1]["cluster"] == by_id[3]["cluster"]
    assert by_id[2]["cluster"] == by_id[4]["cluster"]
    assert by_id[1]["cluster"] != by_id[2]["cluster"]
    assert len(analysed["clusters"]) < len(analysed["scenes"])
    # nothing removed from the scene list: dedup only groups
    assert all("cluster" in s for s in analysed["scenes"])


def test_collage_limits(analysed):
    manifest = analysed["manifest"]
    assert 1 <= manifest["collage_count"] <= 10
    pack = analysed["pack"]
    idx = json.loads((analysed["out_root"] / "collage_index.json").read_text())
    assert idx["layout"] == "9:16"
    assert idx["tile_px"] in ([784, 1394], [522, 929], [392, 697])
    assert idx["grid"][0] * idx["grid"][1] <= 8
    for c in idx["collages"]:
        w, h = Image.open(pack / c["file"]).size
        assert max(w, h) <= 1568
        assert len(c["tiles"]) <= idx["grid"][0] * idx["grid"][1]


def test_summary_is_small_and_complete(analysed):
    size = analysed["manifest"]["summary_bytes"]
    assert size <= 24 * 1024
    summary = json.loads((analysed["pack"] / "metrics_summary.json").read_text())
    for key in ("video", "cut_rhythm", "palette", "clusters", "dedup", "audio", "collages"):
        assert key in summary
    assert summary["cut_rhythm"]["transitions"].get("hard_cut", 0) >= 4


def test_audio_tempo_and_beat_sync(analysed):
    audio = json.loads((analysed["out_root"] / "audio.json").read_text())
    assert 110 <= audio["bpm"] <= 130
    assert audio["cut_beat_sync"]["cuts_checked"] >= 5


def test_per_frame_metrics_saved(analysed):
    lines = (analysed["out_root"] / "frames_metrics.jsonl").read_text().splitlines()
    assert len(lines) >= 700  # every frame of the 24 s / 30 fps test video (step 1)
    first = json.loads(lines[0])
    for k in ("t", "bright", "sat", "edge", "hist_diff", "flow", "phash"):
        assert k in first
    assert (analysed["out_root"] / "keyframes").is_dir()
    assert any((analysed["out_root"] / "keyframes").iterdir())


def test_describe_skipped_without_key_and_works_with_fake_model(analysed, monkeypatch):
    from scripts import describe
    idx = json.loads((analysed["out_root"] / "collage_index.json").read_text())
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(describe, "get_key", lambda: None)
    assert describe.describe_pack(analysed["pack"], idx)["status"] == "skipped"
    monkeypatch.setattr(describe, "get_key", lambda: "fake")
    monkeypatch.setattr(describe, "_ask", lambda models, key, jpg: ("m1", [{"tile": "c1 s1", "shot": "wide"}]))
    res = describe.describe_pack(analysed["pack"], idx)
    assert res["status"] == "ok" and res["collages"] == len(idx["collages"])
    doc = json.loads((analysed["pack"] / "descriptions.json").read_text())
    assert doc["collages"][0]["tiles"][0]["shot"] == "wide"
    (analysed["pack"] / "descriptions.json").unlink()  # test cleanup only


def test_transcribe_never_breaks_the_job(tmp_path, monkeypatch):
    import sys
    import types
    from scripts import audio

    class Boom:
        def __init__(self, *a, **k):
            pass

        def transcribe(self, *a, **k):
            raise TypeError("open() got an unexpected keyword argument 'metadata_errors'")

    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = Boom
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)
    import numpy as np
    import soundfile as sf
    wav = tmp_path / "a.wav"
    sf.write(str(wav), np.zeros(16000, dtype="float32"), 16000)
    res = audio.transcribe(wav)
    assert res["available"] is False and "metadata_errors" in res["error"]


def test_layout_follows_aspect_and_tile_never_stretches():
    import numpy as np
    from scripts.collage import _tile, pick_layout
    from scripts.common import limits
    lim = limits()
    key, lay = pick_layout(1916, 1078, lim, 16)
    assert key == "16:9" and lay["tile_px"] == [784, 441]
    assert pick_layout(1080, 1920, lim, 16)[0] == "9:16"
    # too many scenes for the big tiles -> default dense layout
    assert pick_layout(1916, 1078, lim, 200)[1] == lim["collage"]["layouts"]["16:9"]
    frame = np.full((1078, 1916, 3), 200, dtype=np.uint8)
    t = _tile(frame, 392, 697, "x")
    col = t[:, 196]
    rows = int((col[:, 0] > 100).sum())
    assert abs(rows - 392 * 1078 / 1916) < 6  # same scale on both axes, bars above/below


def test_transcribe_keeps_both_passes_and_coverage(tmp_path, monkeypatch):
    import sys
    import types
    import numpy as np
    import soundfile as sf
    from scripts import audio

    calls = []

    class Seg:
        def __init__(self, t, e=1.0):
            self.start, self.end, self.text = 0.0, e, t

    class Info:
        def __init__(self, lang):
            self.language = lang

    class Fake:
        def __init__(self, *a, **k):
            pass

        def transcribe(self, y, **kw):
            calls.append(kw)
            assert kw["temperature"] == 0.0 and kw["condition_on_previous_text"] is False
            if kw.get("language") == "en":
                return [Seg("jaha pe duniya bhar", 0.5)], Info("en")
            return [Seg("जहाँ पर दुनिया", 0.25)], Info("hi")

    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = Fake
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)
    wav = tmp_path / "a.wav"
    sf.write(str(wav), np.zeros(16000, dtype="float32"), 16000)  # 1 s
    res = audio.transcribe(wav)
    assert res["available"] and len(calls) == 2
    assert res["language"] == "hi" and res["coverage_ratio"] == 0.25
    assert "jaha" in res["alt_english"]["text"] and res["alt_english"]["coverage_ratio"] == 0.5


def test_review_publish_and_fetch_roundtrip(tmp_path, monkeypatch):
    import subprocess
    import pytest
    from PIL import Image
    from scripts import review
    monkeypatch.delenv("ITCOD_NO_REVIEW", raising=False)
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(bare)], check=True)
    (repo / "work").mkdir()
    monkeypatch.setattr(review, "ROOT", repo)
    pack = tmp_path / "pack"
    pack.mkdir()
    Image.new("RGB", (64, 36), (1, 2, 3)).save(pack / "collage_01.jpg")
    (pack / "metrics_summary.json").write_text("{}")
    assert review.publish(pack, "job-a-001")["status"] == "ok"
    got = review.fetch("job-a-001", tmp_path / "out", repo=repo)
    assert {p.split("/")[-1] for p in got} == {"collage_01.jpg", "metrics_summary.json"}
    assert Image.open(tmp_path / "out" / "collage_01.jpg").size == (64, 36)
    assert review.publish(pack, "job-a-001")["status"] == "ok"  # retry reuses the same scratch repo
    assert review.publish(pack, "job-b-002")["status"] == "ok"  # newest job replaces the older one: no growth
    assert review.fetch("job-b-002", tmp_path / "out2", repo=repo)
    with pytest.raises(RuntimeError):
        review.fetch("job-a-001", tmp_path / "out3", repo=repo)


def test_collage_tile_keeps_real_colors():
    """Regression: tiles were returned RGB into a BGR canvas, so skin turned purple/blue."""
    import numpy as np
    from scripts.collage import _tile
    frame = np.zeros((1078, 1916, 3), np.uint8)
    frame[:] = (120, 160, 220)  # BGR skin-orange (R=220, G=160, B=120)
    t = _tile(frame, 784, 441, "x")
    assert t[220, 392].tolist() == [120, 160, 220]


def test_written_collage_jpg_has_real_colors(tmp_path):
    import cv2
    import numpy as np
    from scripts.collage import _tile
    frame = np.zeros((1078, 1916, 3), np.uint8)
    frame[:] = (30, 60, 200)  # BGR: strong red
    out = tmp_path / "c.jpg"
    cv2.imwrite(str(out), _tile(frame, 784, 441, "x"))
    px = cv2.imread(str(out))[220, 392]
    assert px[2] > 150 and px[0] < 90  # red channel (index 2 in BGR) still the strongest


def test_stems_optional_and_measured(tmp_path, monkeypatch):
    import numpy as np
    import soundfile as sf
    from scripts import audio
    wav = tmp_path / "a.wav"
    sf.write(str(wav), 0.1 * np.sin(np.arange(48000 * 4) / 20.0), 48000)
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    assert audio.separate_stems(wav, tmp_path) == {}            # demucs missing -> skipped quietly
    monkeypatch.undo()
    import importlib.util
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())

    def fake_run(cmd, **kw):                                      # pretend demucs wrote two stems
        base = tmp_path / "stems" / "htdemucs" / "a"
        base.mkdir(parents=True, exist_ok=True)
        sf.write(str(base / "vocals.wav"), 0.1 * np.sin(np.arange(48000 * 4) / 20.0), 48000)
        sf.write(str(base / "no_vocals.wav"), 0.05 * np.sin(np.arange(48000 * 4) / 20.0), 48000)
        return 0, "", ""
    monkeypatch.setattr(audio, "run_cmd", fake_run)
    r = audio.separate_stems(wav, tmp_path)
    assert r["voice_minus_music_lu"] == 6.0 and r["vocals_lufs"] > r["music_lufs"]


def test_build_summary_survives_numpy_values(analysed):
    """Regression (job reel-DfMQ7zqkuxO): np.int64 in script metrics / voice crashed json.dumps(summary) on the worker."""
    import numpy as np
    from scripts.common import limits
    from scripts.pack import build_summary
    idx = json.loads((analysed["out_root"] / "collage_index.json").read_text())
    audio = json.loads((analysed["out_root"] / "audio.json").read_text())
    script_m = {"available": True, "words": np.int64(40), "pauses": {"count_gt_0_5s": np.int64(3), "mean_s": np.float32(0.8)}}
    voice = {"available": True, "backend": "x", "global": {"pitch_median_hz": np.float32(211.0)},
             "tempo": {"wpm_mean": np.float64(230.2)}, "gaps": {"count": np.int64(1)},
             "emphasis": [{"w": "x", "i": np.int64(2)}], "words_timed": np.int64(9)}
    s = build_summary(analysed["info"], analysed["scenes"], analysed["clusters"], analysed["dedup_report"], idx, audio,
                      {"available": False}, limits(), script_m, voice)
    back = json.loads(json.dumps(s))  # plain json.dumps, no default=
    assert back["script_metrics"]["pauses"]["count_gt_0_5s"] == 3 and back["voice"]["gaps"]["count"] == 1
