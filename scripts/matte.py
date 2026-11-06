"""Background removal (rembg / U2-Net, CPU). Worker only; heavy deps are optional (requirements-heavy.txt).
Image -> PNG with alpha. Short clip -> WebM (VP9) with alpha, no audio (cut-outs are visual elements). Remotion draws the alpha
file; video needs `transparent` on the video element (the fx step sets props.transparent).
Limits: config/limits.json -> matte. Results are cached by file name + settings."""
import hashlib
import tempfile
from pathlib import Path

import cv2
import numpy as np

from .common import limits, run_cmd, tail

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")


def default_remover():
    try:
        from rembg import new_session, remove
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("background removal needs `pip install rembg onnxruntime` on the worker") from e
    sess = new_session("u2netp")           # small model: fine for CPU, good edges for people / products
    return lambda rgb: np.array(remove(rgb, session=sess))


def _key(src, extra=""):
    p = Path(src)
    return hashlib.sha1(f"{p.name}|{p.stat().st_size}|{extra}".encode()).hexdigest()[:10]


def remove_image(src, dst, remover):
    bgr = cv2.imread(str(src), cv2.IMREAD_COLOR)
    rgba = remover(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise RuntimeError("remover did not return RGBA")
    if not cv2.imwrite(str(dst), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)):
        raise RuntimeError("could not write cut-out")
    return dst


def remove_video(src, dst, remover, max_frames):
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if n > max_frames:
        cap.release()
        raise RuntimeError(f"clip has {n} frames; limit is {max_frames} (matte.max_frames). Cut it shorter or lower the fps first")
    with tempfile.TemporaryDirectory() as tmp:
        i = 0
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            rgba = remover(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
            cv2.imwrite(str(Path(tmp) / f"f_{i:05d}.png"), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
            i += 1
        cap.release()
        if not i:
            raise RuntimeError("clip has no frames")
        rc, _, err = run_cmd(["ffmpeg", "-y", "-v", "error", "-framerate", f"{fps:.3f}", "-i", str(Path(tmp) / "f_%05d.png"), "-c:v", "libvpx-vp9",
                              "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "20", "-auto-alt-ref", "0", str(dst)], timeout=60 * 60)
    if rc != 0:
        raise RuntimeError("alpha video encode failed: " + tail(err, 2))
    return dst


def process(src, out_dir, remover=None, lim=None):
    """-> path of the cut-out (PNG or WebM) inside out_dir. Cached."""
    lim = lim or limits()
    src, out_dir = Path(src), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    is_img = src.suffix.lower() in IMG_EXT
    dst = out_dir / f"{src.stem}.cut.{_key(src)}{'.png' if is_img else '.webm'}"
    if dst.exists():
        return dst
    remover = remover or default_remover()
    if is_img:
        return remove_image(src, dst, remover)
    return remove_video(src, dst, remover, int(lim.get("matte", {}).get("max_frames", 360)))
