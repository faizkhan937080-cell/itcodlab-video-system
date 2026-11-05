"""Frame-by-frame analysis of a video (pure scripts, no Claude tokens).

Per analysed frame: brightness, saturation, edge density, histogram change, pixel change,
optical flow (speed, direction, zoom), perceptual hash.
Then: cuts / dissolves -> scenes -> per-scene stats, keyframes, dominant colours, optional OCR.
Every frame is analysed when the video is short; long videos are sampled so that at most
limits.analysis.max_frames_analyzed frames are processed (the step is recorded in video_info).
"""
import json
import math
from pathlib import Path

import cv2
import numpy as np

from .common import limits, log, run_cmd, tail, write_json_local


# ---------------------------------------------------------------- basics
def probe(video):
    rc, out, err = run_cmd(["ffprobe", "-v", "error", "-print_format", "json",
                            "-show_streams", "-show_format", str(video)])
    if rc != 0:
        raise RuntimeError("ffprobe failed:\n" + tail(err))
    j = json.loads(out)
    vs = [s for s in j["streams"] if s["codec_type"] == "video"]
    if not vs:
        raise RuntimeError("no video stream found")
    v = vs[0]
    has_audio = any(s["codec_type"] == "audio" for s in j["streams"])
    num, den = v.get("r_frame_rate", "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    duration = float(j["format"].get("duration") or v.get("duration") or 0)
    return {"width": int(v["width"]), "height": int(v["height"]), "fps": round(fps, 3),
            "duration_s": round(duration, 3), "codec": v.get("codec_name"),
            "has_audio": has_audio, "bit_rate": int(j["format"].get("bit_rate") or 0)}


def bits_to_hex(bits):
    v = 0
    for b in bits:
        v = (v << 1) | int(b)
    return f"{v:016x}"


def thumb32(gray):
    return cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)


def phash64(gray, small=None):
    """64-bit perceptual hash (DCT) of a grayscale image -> 16 hex chars."""
    small = thumb32(gray) if small is None else small
    dct = cv2.dct(small)[:8, :8]
    med = np.median(dct.flatten()[1:])
    return bits_to_hex((dct.flatten() > med).astype(np.uint8))


def hamming_hex(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def _resize_long(img, long_edge):
    h, w = img.shape[:2]
    s = long_edge / max(h, w)
    if s >= 1:
        return img
    return cv2.resize(img, (max(2, int(w * s)), max(2, int(h * s))), interpolation=cv2.INTER_AREA)


def dominant_colors(bgr, k=3):
    small = cv2.resize(bgr, (64, 64), interpolation=cv2.INTER_AREA).reshape(-1, 3).astype(np.float32)
    k = min(k, len(small))
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(small, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.flatten(), minlength=k)
    order = np.argsort(-counts)
    out = []
    for i in order:
        b, g, r = [int(round(x)) for x in centers[i]]
        out.append({"hex": f"#{r:02X}{g:02X}{b:02X}", "share": round(float(counts[i]) / counts.sum(), 3)})
    return out


def ocr_text(bgr):
    """Optional OCR. Returns list of {text, bbox_norm, height_norm}; [] if tesseract is missing."""
    try:
        import pytesseract
        from pytesseract import Output
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        d = pytesseract.image_to_data(rgb, output_type=Output.DICT)
    except Exception:
        return None
    h, w = bgr.shape[:2]
    out = []
    for i, txt in enumerate(d["text"]):
        txt = (txt or "").strip()
        if txt and float(d["conf"][i]) > 50:
            out.append({"text": txt,
                        "x": round(d["left"][i] / w, 3), "y": round(d["top"][i] / h, 3),
                        "w": round(d["width"][i] / w, 3), "h": round(d["height"][i] / h, 3)})
    return out


# ---------------------------------------------------------------- per-frame pass
def frame_pass(video, lim):
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError("cannot open video")
    info = probe(video)
    fps = info["fps"] or cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or int(info["duration_s"] * fps)
    step = max(1, math.ceil(total / lim["analysis"]["max_frames_analyzed"]))
    info.update({"total_frames": total, "analysis_step": step,
                 "analysed_fps": round(fps / step, 3)})
    frames, hists, thumbs = [], [], []
    prev_gray = prev_hist = prev_flow_gray = None
    idx = 0
    LE = lim["analysis"]["metrics_long_edge_px"]
    FL = lim["analysis"]["flow_long_edge_px"]
    while True:
        if idx % step != 0:
            if not cap.grab():
                break
            idx += 1
            continue
        ok, frame = cap.read()
        if not ok:
            break
        small = _resize_long(frame, LE)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256])
        cv2.normalize(hist, hist, 1.0, 0.0, cv2.NORM_L1)
        fg = cv2.resize(gray, (max(2, int(gray.shape[1] * FL / max(gray.shape))),
                               max(2, int(gray.shape[0] * FL / max(gray.shape)))), interpolation=cv2.INTER_AREA)
        t32 = thumb32(gray)
        rec = {"i": idx, "t": round(idx / fps, 3),
               "bright": round(float(gray.mean()) / 255, 4),
               "sat": round(float(hsv[..., 1].mean()) / 255, 4),
               "edge": round(float((cv2.Canny(gray, 100, 200) > 0).mean()), 4),
               "phash": phash64(gray, t32)}
        if prev_gray is None:
            rec.update({"hist_diff": 0.0, "pix_diff": 0.0, "flow": 0.0, "dx": 0.0, "dy": 0.0, "zoom": 0.0})
        else:
            rec["hist_diff"] = round(float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)), 4)
            rec["pix_diff"] = round(float(np.abs(gray.astype(np.int16) - prev_gray.astype(np.int16)).mean()) / 255, 4)
            flow = cv2.calcOpticalFlowFarneback(prev_flow_gray, fg, None, 0.5, 2, 15, 2, 5, 1.1, 0)
            mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
            hh, ww = fg.shape
            ys, xs = np.mgrid[0:hh, 0:ww]
            cx, cy = (ww - 1) / 2.0, (hh - 1) / 2.0
            rx, ry = xs - cx, ys - cy
            denom = float((rx ** 2 + ry ** 2).sum()) or 1.0
            zoom = float((rx * flow[..., 0] + ry * flow[..., 1]).sum()) / denom
            rec.update({"flow": round(float(mag.mean()), 4), "dx": round(float(flow[..., 0].mean()), 4),
                        "dy": round(float(flow[..., 1].mean()), 4), "zoom": round(zoom, 5)})
        frames.append(rec)
        hists.append(hist.flatten().astype(np.float32))
        thumbs.append(t32)
        prev_gray, prev_hist, prev_flow_gray = gray, hist, fg
        idx += 1
    cap.release()
    return info, frames, fps, hists, thumbs


# ---------------------------------------------------------------- cuts and scenes
def _rolling_median(vals, w=15):
    out = []
    for i in range(len(vals)):
        seg = vals[max(0, i - w):i] or [0.0]
        out.append(float(np.median(seg)))
    return out


def detect_boundaries(frames, hists, thumbs, fps, lim):
    """Return list of (frame_list_index, type) for scene starts after the first scene.
    hard_cut / whip: one big histogram jump. dissolve: the two ends of a window differ a lot,
    every single step is small, the path is efficient (not wandering motion) and flow is low."""
    if len(frames) < 3:
        return []
    a = lim["analysis"]
    hd = [f["hist_diff"] for f in frames]
    flow = [f["flow"] for f in frames]
    med = _rolling_median(hd)
    cuts = []
    for k in range(1, len(frames)):
        thr = max(a["cut_hist_min"], a["cut_hist_factor"] * med[k])
        if hd[k] > thr:
            prev_flow = float(np.mean(flow[max(0, k - 4):k])) if k > 1 else 0.0
            base = float(np.median(flow)) or 0.01
            kind = "whip" if prev_flow > max(3.0, 4 * base) else "hard_cut"
            cuts.append((k, kind))
    # dissolves: compare frames w apart where no hard cut sits inside the window
    step_t = frames[1]["t"] - frames[0]["t"] or 1.0 / fps
    w = max(2, int(round(a["dissolve_window_s"] / step_t)))
    cut_idx = {c[0] for c in cuts}
    cand = []
    for k in range(w, len(frames) - w):
        if any((k - w) < c <= (k + w) for c in cut_idx):
            continue
        dist = [float(cv2.compareHist(hists[k - w], hists[j], cv2.HISTCMP_BHATTACHARYYA))
                for j in range(k - w, k + w + 1)]
        d_ends = dist[-1]
        max_single = max(hd[k - w + 1:k + w + 1])
        flow_mean = float(np.mean(flow[k - w + 1:k + w + 1]))
        vec = float(np.hypot(np.mean([f["dx"] for f in frames[k - w + 1:k + w + 1]]),
                             np.mean([f["dy"] for f in frames[k - w + 1:k + w + 1]])))
        coherence = vec / (flow_mean + 1e-6)  # ~1 = one steady camera move (pan), low = no real motion
        not_a_pan = flow_mean < 0.3 or coherence < a["dissolve_max_coherence"]
        rising = sum(dist[i + 1] >= dist[i] - 0.02 for i in range(len(dist) - 1)) / (len(dist) - 1)
        if (d_ends > a["dissolve_hist_min"] and max_single < a["cut_hist_min"] and not_a_pan
                and rising >= a["dissolve_monotonic_min"] and flow_mean < a["dissolve_max_flow"]):
            # a real cross-fade: the middle frame is the average of the two ends
            A, B, M = thumbs[k - w], thumbs[k + w], thumbs[k]
            e_blend = float(np.abs(M - (A + B) / 2).mean())
            e_min = min(float(np.abs(M - A).mean()), float(np.abs(M - B).mean()))
            if e_blend < a["dissolve_blend_ratio"] * e_min:
                cand.append((k, d_ends))
    for k, score in sorted(cand, key=lambda x: -x[1]):
        if all(abs(k - o[0]) > 2 * w for o in cuts):
            cuts.append((k, "dissolve"))
    cuts.sort()
    # min scene length
    min_frames = max(1, int(round(a["min_scene_s"] / step_t)))
    merged = []
    for k, kind in cuts:
        if merged and k - merged[-1][0] < min_frames:
            continue
        merged.append((k, kind))
    return merged


def build_scenes(frames, boundaries, info, lim):
    a = lim["analysis"]["motion_classes_flow_px"]
    starts = [(0, "start")] + boundaries
    scenes = []
    for n, (k, kind) in enumerate(starts):
        end_k = starts[n + 1][0] if n + 1 < len(starts) else len(frames)
        seg = frames[k:end_k]
        if not seg:
            continue
        t0 = seg[0]["t"]
        t1 = frames[end_k]["t"] if end_k < len(frames) else info["duration_s"]
        flows = [f["flow"] for f in seg[1:]] or [0.0]
        mf = float(np.mean(flows))
        shake = float(np.std([f["dx"] for f in seg] + [f["dy"] for f in seg]))
        zoom = float(np.mean([f["zoom"] for f in seg]))
        cls = ("static" if mf < a["static"] else "slow" if mf < a["slow"]
               else "medium" if mf < a["medium"] else "fast")
        scenes.append({
            "id": len(scenes) + 1, "start_s": round(t0, 3), "end_s": round(t1, 3),
            "duration_s": round(t1 - t0, 3), "transition_in": kind,
            "first_frame": seg[0]["i"], "last_frame": seg[-1]["i"],
            "motion": {"class": cls, "mean_flow": round(mf, 3), "shake": round(shake, 3),
                       "zoom_trend": "in" if zoom > 0.002 else "out" if zoom < -0.002 else "none",
                       "pan": _pan(seg)},
            "brightness": round(float(np.mean([f["bright"] for f in seg])), 3),
            "saturation": round(float(np.mean([f["sat"] for f in seg])), 3),
            "edge_density": round(float(np.mean([f["edge"] for f in seg])), 3),
        })
    return scenes


def _pan(seg):
    dx = float(np.mean([f["dx"] for f in seg])) if seg else 0.0
    dy = float(np.mean([f["dy"] for f in seg])) if seg else 0.0
    if max(abs(dx), abs(dy)) < 0.15:
        return "none"
    return ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("down" if dy > 0 else "up")


# ---------------------------------------------------------------- keyframes
def grab_frame_at(cap, t, fps):
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(round(t * fps))))
    ok, frame = cap.read()
    return frame if ok else None


def extract_keyframes(video, scenes, outdir, fps, lim):
    """Full-resolution JPEG per scene (middle of the scene) + hash, thumb and colours."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    q = lim["analysis"]["keyframe_jpeg_quality"]
    for sc in scenes:
        mid = (sc["start_s"] + sc["end_s"]) / 2.0
        frame = grab_frame_at(cap, mid, fps)
        if frame is None:
            frame = grab_frame_at(cap, sc["start_s"], fps)
        if frame is None:
            sc["keyframe"] = None
            continue
        name = f"scene_{sc['id']:04d}.jpg"
        cv2.imwrite(str(outdir / name), frame, [cv2.IMWRITE_JPEG_QUALITY, q])
        gray = cv2.cvtColor(_resize_long(frame, 128), cv2.COLOR_BGR2GRAY)
        sc["keyframe"] = name
        sc["keyframe_t"] = round(mid, 3)
        sc["phash"] = phash64(gray)
        sc["_thumb"] = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
        sc["colors"] = dominant_colors(frame)
        sc["text"] = ocr_text(_resize_long(frame, 1280))  # None = OCR unavailable
    cap.release()


# ---------------------------------------------------------------- entry
def analyze_video(video, outdir, lim=None, with_ocr=True):
    lim = lim or limits()
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    log(f"frame pass: {video}")
    info, frames, fps, hists, thumbs = frame_pass(video, lim)
    log(f"frames analysed: {len(frames)} (step {info['analysis_step']})")
    boundaries = detect_boundaries(frames, hists, thumbs, fps, lim)
    scenes = build_scenes(frames, boundaries, info, lim)
    extract_keyframes(video, scenes, outdir / "keyframes", fps, lim)
    # persist (without private numpy fields)
    with open(outdir / "frames_metrics.jsonl", "w", encoding="utf-8") as f:
        for rec in frames:
            f.write(json.dumps(rec) + "\n")
    write_json_local(outdir / "video_info.json", info)
    clean = [{k: v for k, v in s.items() if not k.startswith("_")} for s in scenes]
    write_json_local(outdir / "scenes.json", clean)
    return info, frames, scenes, fps
