"""Cover-frame picker: the frame people see before they press play. Chosen by numbers, not taste:
sharp (Laplacian variance), well exposed (median luma near 0.45), contrast, colour, and a bonus when a face-like skin area is in the
picture. The first 0.3 s and last 10% are skipped (fade in/out). Output = full-size JPEG next to the final video."""
import tempfile
from pathlib import Path

import cv2
import numpy as np

from . import grade as G
from .common import run_cmd, tail


def score_frame(rgb):
    gray = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    sharp = min(float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 600.0, 1.0)
    y = G.luma(rgb)
    expo = 1.0 - min(abs(float(np.median(y)) - 0.45) / 0.45, 1.0)
    contrast = min(float(np.percentile(y, 99) - np.percentile(y, 1)) / 0.7, 1.0)
    color = min(G.colourfulness(rgb) / 60.0, 1.0)
    face = min(G.skin(rgb)[0] / 0.08, 1.0)
    return round(0.40 * sharp + 0.25 * expo + 0.15 * contrast + 0.10 * color + 0.10 * face, 4)


def pick(frames_with_t):
    """[(t, rgb_float)] -> (best_t, score, all_scores)"""
    scores = [(t, score_frame(f)) for t, f in frames_with_t]
    t, s = max(scores, key=lambda x: x[1])
    return t, s, scores


def make_cover(video, out_jpg, n=24, long_edge=360):
    from .analyze import probe
    dur = probe(video)["duration_s"]
    t0, t1 = min(0.3, dur / 4), dur * 0.9
    if t1 <= t0:
        t0, t1 = 0.0, dur
    ts = [t0 + (t1 - t0) * (i + 0.5) / n for i in range(n)]
    frames = []
    with tempfile.TemporaryDirectory() as td:
        for i, t in enumerate(ts):
            p = Path(td) / f"c{i:02d}.png"
            rc, _, _ = run_cmd(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                                "-vf", f"scale=-2:{long_edge}", str(p)], timeout=120)
            if rc == 0 and p.exists():
                im = cv2.imread(str(p))
                if im is not None:
                    frames.append((t, cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0))
    if not frames:
        raise RuntimeError("no frames could be read for the cover")
    best_t, score, _ = pick(frames)
    rc, _, err = run_cmd(["ffmpeg", "-y", "-v", "error", "-ss", f"{best_t:.3f}", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(out_jpg)], timeout=120)
    if rc != 0:
        raise RuntimeError("cover export failed: " + tail(err, 2))
    return {"t": round(best_t, 3), "score": score, "file": str(out_jpg)}
