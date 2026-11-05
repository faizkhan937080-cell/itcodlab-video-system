"""Build collage images for Claude.
Hard limits come from config/limits.json: at most 10 collages, long edge <= 1568 px.
Each tile carries cluster / scene / timestamp so Claude can map a tile back to the metrics.
"""
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .analyze import grab_frame_at
from .common import fmt_ts


def pick_layout(width, height, lim, scene_count=None):
    """Aspect decides the grid. Biggest tiles that still fit every scene win (more detail per frame)."""
    ratio = width / float(height)
    key = "9:16" if ratio < 0.85 else "16:9" if ratio > 1.2 else "1:1"
    if scene_count:
        for lay in lim["collage"].get("detail_layouts", {}).get(key, []):
            if scene_count <= capacity(lay, lim):
                return key, lay
    return key, lim["collage"]["layouts"][key]


def capacity(layout, lim):
    return lim["collage"]["max_collages_per_video"] * layout["frames_per_collage"]


def plan_frames(scenes, clusters, layout, lim):
    """One frame per collage cluster rep; spare space goes to extra frames of the longest scenes."""
    cap = capacity(layout, lim)
    reps = [c for c in clusters if c.get("in_collage")]
    by_id = {s["id"]: s for s in scenes}
    plan = []
    for c in reps:
        s = by_id[c["rep_scene"]]
        if s.get("keyframe"):
            plan.append({"cluster": c["cluster"], "scene": s["id"], "t": s["keyframe_t"],
                         "keyframe": s["keyframe"], "extra": False})
    spare = cap - len(plan)
    c_cfg = lim["collage"]
    if spare > 0:
        longest = sorted((by_id[c["rep_scene"]] for c in reps),
                         key=lambda s: -s["duration_s"])
        for s in longest:
            if s["duration_s"] < c_cfg["extra_frame_min_scene_s"]:
                continue
            cl = next(c["cluster"] for c in reps if c["rep_scene"] == s["id"])
            for frac in (0.15, 0.85)[: c_cfg["extra_frames_per_scene_max"]]:
                if spare <= 0:
                    break
                plan.append({"cluster": cl, "scene": s["id"],
                             "t": round(s["start_s"] + frac * s["duration_s"], 3),
                             "keyframe": None, "extra": True})
                spare -= 1
    plan.sort(key=lambda p: (p["t"], p["scene"]))
    return plan[:cap]


def lim_label_px():
    from .common import limits
    return limits()["collage"].get("label_max_px", 22)


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _tile(frame_bgr, tile_w, tile_h, label):
    h, w = frame_bgr.shape[:2]
    s = min(tile_w / w, tile_h / h)
    nw, nh = max(1, int(w * s)), max(1, int(h * s))
    resized = cv2.resize(frame_bgr, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.full((tile_h, tile_w, 3), 18, dtype=np.uint8)
    y0, x0 = (tile_h - nh) // 2, (tile_w - nw) // 2
    canvas[y0:y0 + nh, x0:x0 + nw] = resized
    img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(img)
    fs = max(12, min(lim_label_px(), tile_w // 22))
    f = _font(fs)
    pad = 3
    tw = d.textlength(label, font=f)
    d.rectangle([0, 0, tw + 2 * pad, fs + 2 * pad], fill=(0, 0, 0))
    d.text((pad, pad - 1), label, fill=(255, 255, 255), font=f)
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)  # PIL is RGB; the canvas and cv2.imwrite are BGR


def build_collages(video, outdir, scenes, clusters, info, fps, lim):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    key, layout = pick_layout(info["width"], info["height"], lim, len(scenes))
    cols, rows = layout["grid"]
    tw, th = layout["tile_px"]
    per = layout["frames_per_collage"]
    plan = plan_frames(scenes, clusters, layout, lim)
    max_n = lim["collage"]["max_collages_per_video"]
    n_collages = math.ceil(len(plan) / per) if plan else 0
    if n_collages > max_n:
        raise RuntimeError(f"collage count {n_collages} > limit {max_n}")
    cap = cv2.VideoCapture(str(video))
    kf_dir = outdir.parent / "keyframes"
    files, index = [], []
    for ci in range(n_collages):
        part = plan[ci * per:(ci + 1) * per]
        canvas = np.full((rows * th, cols * tw, 3), 0, dtype=np.uint8)
        for j, p in enumerate(part):
            if p["keyframe"] and (kf_dir / p["keyframe"]).exists():
                frame = cv2.imread(str(kf_dir / p["keyframe"]))
            else:
                frame = grab_frame_at(cap, p["t"], fps)
            if frame is None:
                continue
            label = f"c{p['cluster']} s{p['scene']} {fmt_ts(p['t'])}"
            r, c = divmod(j, cols)
            canvas[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = _tile(frame, tw, th, label)
        H, W = canvas.shape[:2]
        assert max(H, W) <= lim["collage"]["max_long_edge_px"], (W, H)
        name = f"collage_{ci + 1:02d}.jpg"
        cv2.imwrite(str(outdir / name), canvas, [cv2.IMWRITE_JPEG_QUALITY, lim["collage"]["jpeg_quality"]])
        files.append(name)
        index.append({"file": name, "size_px": [W, H], "tiles": [
            {"pos": j + 1, "cluster": p["cluster"], "scene": p["scene"], "t": p["t"], "extra": p["extra"]}
            for j, p in enumerate(part)]})
    cap.release()
    return {"layout": key, "grid": [cols, rows], "tile_px": [tw, th], "collages": index,
            "count": len(files), "max_allowed": max_n}
