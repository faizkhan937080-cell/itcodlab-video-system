"""Render only changed shots: fingerprints must change exactly for the pieces whose pixels can change."""
import copy

from scripts import render_chunks as rc

PLAN = {
    "fps": 30, "orientation": "portrait", "width": 1080, "height": 1920,
    "caption_style": {"look": "ext", "y": 0.5},
    "captions": [{"text": "a", "start_s": 0.5, "end_s": 1.5}, {"text": "b", "start_s": 9.0, "end_s": 9.8}],
    "scenes": [{"id": "s1", "duration_s": 12.0, "template": "video",
                "props": {"src": "x.mp4", "layout": [{"from_s": 0, "scale": 1}, {"from_s": 4.0, "scale": 2}, {"from_s": 8.0, "scale": 1}]},
                "underlays": [{"template": "clone", "start_s": 0, "end_s": 4.0, "props": {"component": "a"}},
                              {"template": "clone", "start_s": 4.0, "end_s": 8.0, "props": {"component": "b"}},
                              {"template": "clone", "start_s": 8.0, "end_s": 12.0, "props": {"component": "c"}}]}],
}
EXTRA = {"code": "x", "scale": 0.5}


def keys(plan):
    return [rc.piece_key(plan, a, b, int(a * 30), int(b * 30) - 1, EXTRA) for a, b in rc.cut_points(plan)]


def test_cut_points_follow_shots_and_merge_tiny_pieces():
    assert rc.cut_points(PLAN) == [(0.0, 4.0), (4.0, 8.0), (8.0, 12.0)]
    p = copy.deepcopy(PLAN)
    p["scenes"][0]["props"]["layout"].append({"from_s": 8.4, "scale": 3})   # 0.4 s piece -> merged
    assert len(rc.cut_points(p)) == 3


def test_changing_the_last_shot_changes_only_its_key():
    k0 = keys(PLAN)
    p = copy.deepcopy(PLAN)
    p["scenes"][0]["underlays"][2]["props"]["component"] = "z"
    k1 = keys(p)
    assert k0[:2] == k1[:2] and k0[2] != k1[2]


def test_global_and_code_changes_change_every_key():
    p = copy.deepcopy(PLAN)
    p["caption_style"]["y"] = 0.6
    assert all(a != b for a, b in zip(keys(PLAN), keys(p)))
    other = [rc.piece_key(PLAN, a, b, int(a * 30), int(b * 30) - 1, {"code": "y", "scale": 0.5}) for a, b in rc.cut_points(PLAN)]
    assert all(a != b for a, b in zip(keys(PLAN), other))


def test_caption_change_touches_only_nearby_pieces():
    p = copy.deepcopy(PLAN)
    p["captions"][1]["text"] = "changed"           # at 9 s: pieces 4-8 (within 3 s) and 8-12
    k0, k1 = keys(PLAN), keys(p)
    assert k0[0] == k1[0] and k0[1] != k1[1] and k0[2] != k1[2]


def test_layout_segment_change_is_seen_by_its_piece():
    p = copy.deepcopy(PLAN)
    p["scenes"][0]["props"]["layout"][1]["scale"] = 2.6
    k0, k1 = keys(PLAN), keys(p)
    assert k0[0] == k1[0] and k0[1] != k1[1] and k0[2] == k1[2]


def test_sound_key_ignores_graphics():
    p = copy.deepcopy(PLAN)
    p["scenes"][0]["underlays"][0]["props"]["component"] = "q"
    p["captions"][0]["text"] = "q"
    assert rc.audio_key(PLAN, EXTRA) == rc.audio_key(p, EXTRA)
    p["scenes"][0]["props"]["src"] = "y.mp4"
    assert rc.audio_key(PLAN, EXTRA) != rc.audio_key(p, EXTRA)


def test_missing_neighbour_pieces_render_in_one_call(tmp_path, monkeypatch):
    import subprocess
    calls = []

    def fake_remotion(args, timeout):
        calls.append(args)
        out = args[0]
        fr = [a for a in args if a.startswith("--frames=")]
        if fr:
            a, b = map(int, fr[0].split("=")[1].split("-"))
            from pathlib import Path
            for i in range(a, b + 1):
                (Path(out) / f"element-{i:04d}.png").write_bytes(b"x%d" % i)
        else:
            open(out, "wb").write(b"aac")
    monkeypatch.setattr(rc, "_remotion", fake_remotion)
    monkeypatch.setattr(rc, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(rc, "code_hash", lambda: "c")
    monkeypatch.setattr(rc.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""))
    m = {"crf": 18, "pixel_format": "yuv420p", "colorspace": "bt709"}
    r1 = rc.render("p.json", PLAN, tmp_path / "a.mp4", 0.5, m, 30, 360, 60)
    assert r1["fresh"] == 3 and len([c for c in calls if any(x.startswith("--frames=") for x in c)]) == 1
    calls.clear()
    p = copy.deepcopy(PLAN)
    p["scenes"][0]["underlays"][2]["props"]["component"] = "z"
    r2 = rc.render("p.json", p, tmp_path / "b.mp4", 0.5, m, 30, 360, 60)
    fr = [x for c in calls for x in c if x.startswith("--frames=")]
    assert r2["fresh"] == 1 and r2["reused"] == 2 and fr == ["--frames=240-359"]
