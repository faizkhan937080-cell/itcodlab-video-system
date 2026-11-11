"""Green-screen key (rulebooks/23): judged on real-looking frames, tuned, verified, never ships a ghost or a green wall."""
import shutil
import subprocess

import cv2
import numpy as np
import pytest

from scripts import matte

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg missing")


def _clip(path, spill=False, green=True):
    """Lit wall (gradient + shadow) with a skin face, dark hair, navy shirt and a WHITE table, like the real shoot."""
    w, h, n = 216, 384, 14
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 14, (w, h))
    yy = np.linspace(0, 1, h)[:, None]
    for i in range(n):
        fr = np.zeros((h, w, 3), np.uint8)
        wall = np.stack([40 + 20 * yy, 200 - 70 * yy, 70 + 10 * yy], -1) if green else np.full((h, 1, 3), 120.0)  # BGR
        fr[:] = np.broadcast_to(wall, (h, w, 3)).astype(np.uint8)
        fr[:, :40] = (fr[:, :40] * 0.7).astype(np.uint8)                       # shadow on the left
        cv2.rectangle(fr, (60, 170), (160, 290), (90, 40, 20), -1)               # navy shirt
        cv2.circle(fr, (110 + (i % 3), 130), 30, (110, 150, 200), -1)            # skin
        cv2.rectangle(fr, (80, 95), (140, 112), (20, 25, 35), -1)                # dark hair
        cv2.rectangle(fr, (0, 290), (w, h), (240, 242, 240), -1)                 # white table
        if spill:
            fr[120:150, 85:135] = (fr[120:150, 85:135] * 0.85 + np.array([10, 30, 5])).clip(0, 255).astype(np.uint8)
        vw.write(fr)
    vw.release()


def test_key_color_is_the_wall(tmp_path):
    src = tmp_path / "gs.mp4"
    _clip(src)
    col = matte.key_color(src)
    r, g, b = int(col[0:2], 16), int(col[2:4], 16), int(col[4:6], 16)
    assert g > 110 and g > r + 30 and g > b + 30


def test_tuned_key_solid_subject_clear_wall(tmp_path):
    src = tmp_path / "gs.mp4"
    _clip(src, spill=True)
    out, col, q = matte.chroma_key(src, tmp_path / "fx")
    assert out.suffix == ".webm" and out.stat().st_size > 0
    v = q["verified"]
    assert v["fg_alpha_min"] >= 0.95 and v["bg_alpha_max"] <= 0.05 and v["green_visible_max"] <= 0.003
    assert matte.chroma_key(src, tmp_path / "fx")[0] == out        # cached with its quality file


def test_window_keys_only_that_part(tmp_path):
    src = tmp_path / "gs.mp4"
    _clip(src)
    out, _, _ = matte.chroma_key(src, tmp_path / "fx", {"start_s": 0.0, "end_s": 0.5})
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)], capture_output=True, text=True)
    assert float(p.stdout.strip()) < 0.8


def test_no_green_stops_instead_of_shipping(tmp_path):
    src = tmp_path / "nogs.mp4"
    _clip(src, green=False)
    with pytest.raises(RuntimeError):
        matte.chroma_key(src, tmp_path / "fx")


def test_quality_judge_catches_a_ghost():
    bgr = np.zeros((100, 100, 3), np.uint8)
    bgr[:] = (40, 190, 60)
    bgr[30:90, 30:70] = (90, 40, 20)                                             # clearly not green
    rgba = np.dstack([bgr[..., ::-1], np.full((100, 100), 255, np.uint8)]).copy()
    rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
    rgba[..., 3] = 0
    rgba[30:90, 30:70, 3] = 90                                                   # subject only ~35% opaque = ghost
    q = matte.key_quality(bgr, rgba, "3CBE28")
    assert not q["ok"] and q["fg_alpha"] < 0.5
    rgba[30:90, 30:70, 3] = 255
    assert matte.key_quality(bgr, rgba, "3CBE28")["ok"]


def _dim(path, src):
    """Same shoot, underexposed person (the grade must lift it) - the wall stays green."""
    cap = cv2.VideoCapture(str(src))
    w, h = int(cap.get(3)), int(cap.get(4))
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 14, (w, h))
    ok, fr = cap.read()
    while ok:
        f = fr.astype(int)
        wall = (f[..., 1] - np.maximum(f[..., 0], f[..., 2])) > 40
        out = fr.copy()
        out[~wall] = (fr[~wall] * 0.45).astype(np.uint8)                 # only the person gets darker
        vw.write(out)
        ok, fr = cap.read()
    vw.release()


def test_person_is_graded_after_the_key_and_alpha_survives(tmp_path):
    base = tmp_path / "gs.mp4"
    _clip(base)
    dim = tmp_path / "dim.mp4"
    _dim(dim, base)
    on, _, q_on = matte.chroma_key(dim, tmp_path / "fx_on", {"grade_mode": "auto"})
    off, _, q_off = matte.chroma_key(dim, tmp_path / "fx_off", {"grade_mode": "off"})
    assert q_on["grade"].get("changed") is True and q_on["grade"]["mode"] == "auto"
    assert q_off["grade"]["mode"] == "off"
    assert q_on["verified"]["fg_alpha_min"] >= 0.9                      # alpha still solid after the LUT
    a = matte._png_frame(["-c:v", "libvpx-vp9", "-ss", "0.3", "-i", str(on)])
    b = matte._png_frame(["-c:v", "libvpx-vp9", "-ss", "0.3", "-i", str(off)])
    solid = a[..., 3] > 250
    assert a[..., :3][solid].mean() > b[..., :3][solid].mean() + 2      # lifted a little (the grade is bounded)


def test_check_image_shows_raw_alpha_result(tmp_path):
    src = tmp_path / "gs.mp4"
    _clip(src)
    out, _, q = matte.chroma_key(src, tmp_path / "fx")
    img = cv2.imread(str(out.parent / q["check_image"]))
    assert img is not None and img.shape[0] == 3 * 360 and img.shape[1] > 3 * 150


def test_solid_core_fills_see_through_skin(tmp_path):
    """Real shoot: the key made face/beard grey (see-through) = whiteness. The solid-core step must make that skin much more opaque
    while the green wall stays gone."""
    src = tmp_path / "gs.mp4"
    _clip(src, spill=True)
    col = matte.key_color(src)

    def alpha(solid):
        return matte._png_frame(["-i", str(src), "-filter_complex", matte.chroma_filter(col, 0.13, 0.06, 0.6, solid=solid),
                                 "-map", "[v]", "-pix_fmt", "rgba"])[..., 3]
    plain, fixed = alpha(None), alpha(matte.SOLID)
    face = (slice(120, 140), slice(100, 120))
    assert plain[face].mean() < 200                                   # the problem is real in this clip
    assert fixed[face].mean() > plain[face].mean() + 40               # and is fixed
    assert fixed[5:60, 5:60].mean() < 5                               # green wall stays gone
    assert fixed[200:250, 90:130].mean() > 250                        # shirt stays solid
