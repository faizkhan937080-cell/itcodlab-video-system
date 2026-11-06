import json
import shutil

import cv2
import numpy as np

from scripts import grade as G
from scripts import grade_video as GV


def _scene(rng, base, cast=(1, 1, 1), n=96, sd=0.18):
    x = np.clip(rng.normal(base, sd, (n, n, 1)), 0, 1) * np.ones((1, 1, 3))
    return np.clip(x * np.array(cast), 0, 1).astype(np.float32)


def _solve(frames, mode="auto", ref=None):
    st = G.measure(frames)
    pix = GV.pool(frames)
    p, notes = G.solve(st, pix, mode, ref)
    return st, pix, p, notes


def test_normal_footage_is_left_alone():
    rng = np.random.default_rng(0)
    st, pix, p, _ = _solve([_scene(rng, 0.45) for _ in range(4)])
    assert G.is_identity(p)                       # no needless change, so no re-encode


def test_dark_blue_footage_is_fixed_within_bounds_and_verified():
    rng = np.random.default_rng(1)
    st, pix, p, notes = _solve([_scene(rng, 0.22, (0.85, 0.95, 1.2)) for _ in range(5)])
    assert 1.0 < p["exposure"] <= 2.0001          # never more than +1 stop
    assert p["gains"][2] < 1.0 < p["gains"][0]    # blue cast pulled back
    assert all(abs(g - 1) <= 0.15 + 1e-6 for g in p["gains"])
    v = G.verify(pix, p, st)
    assert v["ok"] and v["after"]["p50"] > st["p50"]
    json.dumps({"stats": st, "params": p, "verify": v})   # reports must be JSON-safe


def test_off_is_identity_and_natural_ignores_reference():
    rng = np.random.default_rng(2)
    fr = [_scene(rng, 0.2, (0.8, 1, 1.2)) for _ in range(3)]
    _, _, p, _ = _solve(fr, "off")
    assert G.is_identity(p)
    ref = {"p50": 0.6, "contrast": 0.9, "colourfulness": 80.0, "mid_ratio": [1.2, 1.0, 0.8]}
    st, pix, pn, _ = _solve(fr, "natural", ref)
    _, _, pa, _ = _solve(fr, "auto", ref)
    assert pn["contrast"] == 1.0 and pa["contrast"] != 1.0
    assert pa["strength"] < 1.0 and pn["strength"] == 1.0


def test_reference_look_moves_footage_towards_it():
    rng = np.random.default_rng(3)
    ref_frames = [_scene(rng, 0.6, (1.15, 1.0, 0.85)) for _ in range(4)]    # bright, warm reel
    ref = G.measure(ref_frames)
    fr = [_scene(rng, 0.35, (0.9, 1.0, 1.1)) for _ in range(4)]             # darker, cool footage
    st, pix, p, _ = _solve(fr, "auto", ref)
    after = G.measure([G.apply_params(f, p) for f in fr])
    assert abs(after["p50"] - ref["p50"]) < abs(st["p50"] - ref["p50"])
    assert after["mid_ratio"][0] / after["mid_ratio"][2] > st["mid_ratio"][0] / st["mid_ratio"][2]   # warmer


def test_flat_scene_is_not_blown_up_to_full_range():
    rng = np.random.default_rng(4)
    st, pix, p, _ = _solve([_scene(rng, 0.7, sd=0.03) for _ in range(4)])
    assert (p["white_in"] - p["black_in"]) >= 1 / 1.5 - 1e-6


def test_oversaturated_is_pulled_into_band():
    rng = np.random.default_rng(5)
    f = np.stack([rng.uniform(0.7, 1, (64, 64)), rng.uniform(0.0, 0.2, (64, 64)), rng.uniform(0.0, 0.3, (64, 64))], -1).astype(np.float32)
    st = G.measure([f])
    assert st["colourfulness"] > 95
    p, _ = G.solve(st, GV.pool([f]), "natural")
    assert p["saturation"] < 1.0 and p["saturation"] >= 0.7


def test_skin_hue_nudge_is_small_and_needs_real_skin():
    skin = np.ones((80, 80, 3), np.float32) * np.array([0.80, 0.62, 0.55], np.float32)
    st = G.measure([skin])
    assert st["skin_fraction"] > 0.9
    p, _ = G.solve(st, GV.pool([skin]), "natural")
    assert abs(p["hue_deg"]) <= 8.0
    nonskin = np.ones((80, 80, 3), np.float32) * np.array([0.1, 0.3, 0.9], np.float32)
    assert G.measure([nonskin])["skin_hue"] is None


def test_lut_matches_apply_params_and_cube_file_is_valid(tmp_path):
    p = {**G.IDENTITY, "gains": [1.1, 1.0, 0.9], "exposure": 1.2, "saturation": 1.1}
    lut = G.make_lut(p, 17)
    assert lut.shape == (17 ** 3, 3)
    probe = np.array([[[0.25, 0.5, 0.75]]], np.float32)
    idx = (round(0.25 * 16)) + 17 * (round(0.5 * 16)) + 17 * 17 * (round(0.75 * 16))   # red fastest
    assert np.allclose(lut[idx], G.apply_params(probe, p)[0, 0], atol=1e-5)
    f = G.write_cube(tmp_path / "x.cube", lut)
    lines = open(f).read().splitlines()
    assert lines[1] == "LUT_3D_SIZE 17" and len(lines) == 4 + 17 ** 3 + 1 - 1


def test_filter_text_hdr_and_lut():
    assert "tonemap" in GV.build_vf("hlg") and "lut3d" not in GV.build_vf("hlg")
    vf = GV.build_vf("sdr", "/tmp/a.cube")
    assert "tonemap" not in vf and "lut3d=file=/tmp/a.cube:interp=tetrahedral" in vf and "in_color_matrix=bt709" in vf
    assert GV.build_vf("sdr") == ""


def test_graded_targets_only_footage_and_pictures():
    plan = {"scenes": [{"id": "a", "template": "video", "props": {"src": "input/x.mp4"}},
                       {"id": "b", "template": "paper_cutout", "props": {"src": "assets/c.png"}},
                       {"id": "c", "template": "image", "props": {"src": "assets/i.jpg"}},
                       {"id": "d", "template": "title", "props": {"text": "x"}}]}
    assert [r for _, r in GV.graded_targets(plan)] == ["input/x.mp4", "assets/i.jpg"]


def _make_clip(path, dark=True):
    w, h, n = 320, 240, 30
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 15, (w, h))
    rng = np.random.default_rng(0)
    for i in range(n):
        base = 0.2 if dark else 0.45
        im = np.clip(rng.normal(base, 0.12, (h, w, 1)), 0, 1) * np.array([1.2, 0.95, 0.8])   # BGR: bluish
        vw.write((np.clip(im, 0, 1) * 255).astype(np.uint8))
    vw.release()


def test_end_to_end_grade_plan_on_real_files(tmp_path):
    pub = tmp_path / "public"
    (pub / "input").mkdir(parents=True)
    (pub / "assets").mkdir()
    _make_clip(pub / "input" / "dark.mp4")
    _make_clip(pub / "input" / "ok.mp4", dark=False)
    shutil.copy(pub / "input" / "dark.mp4", pub / "input" / "same.mp4")
    img = (np.ones((120, 160, 3)) * np.array([60, 50, 40]) ).astype(np.uint8)
    cv2.imwrite(str(pub / "assets" / "p.png"), img)
    plan = {"scenes": [{"id": "a", "template": "video", "props": {"src": "input/dark.mp4"}},
                       {"id": "b", "template": "video", "props": {"src": "input/ok.mp4"}},
                       {"id": "c", "template": "image", "props": {"src": "assets/p.png"}},
                       {"id": "d", "template": "video", "props": {"src": "input/missing.mp4"}}]}
    new, rep = GV.grade_plan(plan, None, public_dir=pub, work=tmp_path / "w")
    assert plan["scenes"][0]["props"]["src"] == "input/dark.mp4"            # stored plan untouched
    assert new["scenes"][0]["props"]["src"].startswith("graded/") and (pub / new["scenes"][0]["props"]["src"]).exists()
    assert rep["files"]["input/dark.mp4"]["changed"] is True
    assert "input/missing.mp4" in rep["errors"]
    # brighter after the grade
    cap = cv2.VideoCapture(str(pub / new["scenes"][0]["props"]["src"]))
    ok, fr = cap.read()
    assert ok and fr.mean() > 0.2 * 255 * 0.9
    json.dumps(rep)
    # off: nothing re-encoded for SDR footage
    new2, rep2 = GV.grade_plan({**plan, "grade": {"mode": "off"}}, None, public_dir=pub, work=tmp_path / "w2")
    assert new2["scenes"][0]["props"]["src"] == "input/dark.mp4"
    assert GV.summary_line(rep).startswith("grade auto")
