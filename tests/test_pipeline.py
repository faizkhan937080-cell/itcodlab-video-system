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
    assert idx["layout"] == "9:16" and idx["grid"] == [4, 2] and idx["tile_px"] == [392, 697]
    for c in idx["collages"]:
        w, h = Image.open(pack / c["file"]).size
        assert max(w, h) <= 1568
        assert len(c["tiles"]) <= 8


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
