"""Screen-in-scene: detect the playing video inside a shaky phone shot, flatten it, schema + review wiring."""
import json
import subprocess

import cv2
import numpy as np
import pytest

from scripts import screencrop
from scripts.common import ROOT

W, H, N = 640, 480, 40
QUAD = np.float32([[170, 90], [490, 120], [470, 360], [150, 330]])


def _room():
    rng = np.random.RandomState(1)
    r = cv2.resize(rng.randint(60, 200, (24, 32, 3)).astype(np.uint8), (W, H), interpolation=cv2.INTER_CUBIC)
    r = cv2.GaussianBlur(r, (0, 0), 2)
    for _ in range(120):                                   # corners/edges like a real room (ORB needs them)
        x, y = rng.randint(0, W - 30), rng.randint(0, H - 30)
        cv2.rectangle(r, (x, y), (x + rng.randint(6, 30), y + rng.randint(6, 30)), tuple(int(v) for v in rng.randint(0, 255, 3)), -1)
    return r


def _pattern(t, w=320, h=240):
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (30 + (9 * t) % 160, 20, 120)
    x = (t * 17) % w
    cv2.circle(img, (x, h // 2), 40, (0, 255, 255), -1)
    cv2.rectangle(img, (0, 0), (60, 40), (255, 255, 255), -1)       # white marker top-left of the inner video
    return img


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    d = tmp_path_factory.mktemp("sc")
    room = _room()
    p = d / "scene.mp4"
    vw = cv2.VideoWriter(str(p), cv2.VideoWriter_fourcc(*"mp4v"), 25, (W, H))
    src = np.float32([[0, 0], [320, 0], [320, 240], [0, 240]])
    for t in range(N):
        dx, dy = 2 * np.sin(t / 3), 2 * np.cos(t / 4)
        M0 = cv2.getPerspectiveTransform(src, QUAD)
        fr = room.copy()
        cv2.fillPoly(fr, [QUAD.astype(np.int32)], (0, 0, 0))
        fr = np.where(cv2.warpPerspective(np.full((240, 320), 255, np.uint8), M0, (W, H))[..., None] > 0,
                      cv2.warpPerspective(_pattern(t), M0, (W, H)), fr)
        sh = np.float32([[1, 0, dx], [0, 1, dy]])
        vw.write(cv2.warpAffine(fr, sh, (W, H), borderMode=cv2.BORDER_REPLICATE))
    vw.release()
    return p


def test_detect_finds_screen(clip, tmp_path):
    c = screencrop.detect(clip, tmp_path)
    assert c and (tmp_path / "screen_candidates.jpg").stat().st_size <= 1_500_000
    assert json.loads((tmp_path / "screen_candidates.json").read_text())["candidates"]
    q = np.array(c[0]["quad"])
    assert np.linalg.norm(q - QUAD, axis=1).max() < 45


def test_extract_aspect_and_content(clip, tmp_path):
    rep = screencrop.extract(clip, QUAD.tolist(), None, None, tmp_path / "o.mp4")
    assert abs(rep["out_w"] / rep["out_h"] - 4 / 3) < 0.15 and rep["out_w"] % 2 == 0 and rep["out_h"] % 2 == 0
    assert (tmp_path / "screen_crop.json").exists() and rep["tracked_fraction"] > 0.5
    cap = cv2.VideoCapture(str(tmp_path / "o.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 10)
    ok, f = cap.read()
    assert ok
    h, w = f.shape[:2]
    tl = f[: h // 8, : w // 8].mean()
    assert tl > 200 and f[h // 2:, : w // 8].mean() < 200          # white marker sits top-left, flattened


def test_prepare_fallback_never_raises(tmp_path):
    bad = tmp_path / "x.mp4"
    bad.write_bytes(b"nope")
    path, cap, warn = screencrop.prepare(bad, tmp_path / "w")
    assert path == str(bad) and cap["analysed"] == "full_frame" and warn


def test_schema_and_review_keep():
    from jsonschema import validate
    sch = json.loads((ROOT / "schemas" / "job.schema.json").read_text())
    job = {"id": "abc123", "type": "analyze", "mode": "video", "target": "general", "gate1_approved_by_user": True,
           "file": "input/references/x.mp4", "content_only": True,
           "crop": {"quad": [[0, 0], [10, 0], [10, 10], [0, 10]], "out_w": 540, "out_h": 960}}
    validate(job, sch)
    from scripts.review import KEEP
    for n in ("screen_candidates.jpg", "screen_candidates.json", "screen_crop.json"):
        assert n in KEEP
