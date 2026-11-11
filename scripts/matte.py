"""Background removal (rembg / U2-Net, CPU). Worker only; heavy deps are optional (requirements-heavy.txt).
Image -> PNG with alpha. Short clip -> WebM (VP9) with alpha, no audio (cut-outs are visual elements). Remotion draws the alpha
file; video needs `transparent` on the video element (the fx step sets props.transparent).
Limits: config/limits.json -> matte. Results are cached by file name + settings."""
import hashlib
import json
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


# ---- green screen (chroma key): far faster and cleaner than rembg for studio footage ----
# rulebooks/23: the key is judged on REAL frames of the real clip (subject solid, wall gone, no green left) and the
# settings are tuned until it passes; if nothing passes the render stops (never ships a ghost person or a green wall).
import subprocess

KEY_CANDIDATES = [(0.13, 0.06, 0.6), (0.18, 0.08, 0.7), (0.24, 0.10, 0.8), (0.30, 0.12, 0.85), (0.36, 0.14, 0.9), (0.10, 0.05, 0.5)]


def _green_pixels(fr):
    b, g, r = [fr[..., i].astype(int) for i in range(3)]
    return (g - np.maximum(r, b) > 30) & (g > 90)


def key_color(src, samples=6, start_s=None, end_s=None):
    """Median colour of the green-dominant pixels of a few frames (the lit wall) -> 'RRGGBB'."""
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    a = int((start_s or 0) * fps)
    b = min(n, int(end_s * fps)) if end_s else n
    px = []
    for k in range(samples):
        if b > a:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(a + (b - a) * (k + 0.5) / samples))
        ok, fr = cap.read()
        if not ok:
            continue
        m = _green_pixels(fr)
        if m.sum() > 500:
            px.append(fr[m][::7])
    cap.release()
    if not px:
        raise RuntimeError("no green screen found in the clip (key colour not detectable)")
    bgr = np.median(np.concatenate(px), axis=0).astype(int)
    return f"{bgr[2]:02X}{bgr[1]:02X}{bgr[0]:02X}"


def chroma_chain(color, similarity=0.13, blend=0.06, despill=0.6):
    """Simple -vf chain (no grade): used to try key settings on single frames."""
    return (f"format=yuv444p,chromakey=0x{color}:{similarity}:{blend},format=gbrap,"
            f"despill=type=green:mix={despill}:expand=0:alpha=0,format=yuva420p")


SOLID = (30, 120)   # alpha 0-255: below LO = background (gone), above HI = fully solid. Real keyed faces came out grey (see-through skin)


def chroma_filter(color, similarity=0.13, blend=0.06, despill=0.6, cube=None, solid=SOLID):
    """ffmpeg filter graph [0:v] -> [v]: key -> despill (removes green fringe on hair/skin) -> solid core (the matte is steepened so
    skin/beard that the key made half see-through becomes solid, green-wall leftovers stay gone) -> colour grade (3D LUT, picture
    only: alpha is split off and put back) -> alpha format. The grade comes AFTER the key so the green wall never steers it."""
    base = (f"format=yuv444p,chromakey=0x{color}:{similarity}:{blend},format=gbrap,"
            f"despill=type=green:mix={despill}:expand=0:alpha=0")
    lo, hi = solid if solid else (0, 255)
    curve = f"alphaextract,format=gray,lut=y='clip((val-{lo})*255/{max(1, hi - lo)},0,255)',gblur=sigma=0.8"
    if not cube:
        pic = "[c]format=gbrp[g]"
    else:
        c = str(cube).replace("\\", "/").replace(":", r"\:")
        pic = f"[c]format=gbrp,lut3d=file='{c}':interp=tetrahedral[g]"
    return (f"[0:v]{base},split=2[c][m];[m]{curve}[al];{pic};[g][al]alphamerge,format=yuva420p[v]")


PAGE = (250, 250, 249)   # the clean page colour behind the person (remotion Clean.tsx)


def person_frames(src, color, start_s, end_s, n=6):
    """Float RGB 'frames' (N,1,3) holding ONLY the person's pixels (screen colour and green cast removed), for measuring the grade."""
    key = np.uint8([[[int(color[4:6], 16), int(color[2:4], 16), int(color[0:2], 16)]]])
    kc = cv2.cvtColor(key, cv2.COLOR_BGR2YCrCb).astype(float)[0, 0]
    out = []
    for t in _src_times(src, start_s, end_s, n):
        bgr = _png_frame(["-ss", str(t), "-i", str(src)])[..., :3]
        ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb).astype(float)
        d = np.hypot(ycc[..., 1] - kc[1], ycc[..., 2] - kc[2]) / 255.0
        b_, g_, r_ = [bgr[..., i].astype(int) for i in range(3)]
        m = (d > 0.22) & (g_ - np.maximum(r_, b_) < 10)
        if m.sum() > 2000:
            px = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)[m].astype(np.float32) / 255.0
            out.append(px.reshape(-1, 1, 3)[:: max(1, len(px) // 20000)])
    return out


def person_grade(src, color, start_s, end_s, mode, ref, strength, lim, work):
    """Grade of the PERSON in a green-screen clip (rulebooks/13-grade.md, same maths). -> (cube_path or None, report)."""
    from . import grade as G
    if mode == "off":
        return None, {"mode": "off"}
    frames = person_frames(src, color, start_s, end_s)
    if not frames:
        return None, {"mode": mode, "skipped": "no person pixels found to measure"}
    stats = G.measure(frames, lim)
    pooled = np.concatenate(frames)
    params, notes = G.solve(stats, pooled, mode, ref, lim, strength)
    rep = {"mode": mode, "stats": {k: stats[k] for k in ("p1", "p50", "p99", "colourfulness", "skin_hue", "spread")},
           "params": {k: (round(v, 4) if isinstance(v, float) else [round(x, 4) for x in v] if isinstance(v, list) else v) for k, v in params.items()},
           "verify": G.verify(pooled, params, stats, ref, lim), "notes": notes + stats["warnings"]}
    if G.is_identity(params, lim):
        rep["changed"] = False
        return None, rep
    cube = G.write_cube(Path(work) / f"person_{hashlib.sha1(json.dumps(rep['params'], sort_keys=True).encode()).hexdigest()[:8]}.cube", G.make_lut(params))
    rep["changed"] = True
    return cube, rep


def key_check_image(src, webm, start_s, end_s, out_jpg, n=3):
    """The look at the real clip (rulebooks/23 rule 3): per frame  RAW | ALPHA matte | RESULT on the page (as the render shows it).
    Claude looks at this: grey in the alpha panel on the face = see-through skin; washed colour with solid alpha = a colour/grade problem."""
    off = start_s or 0.0
    rows = []
    for t in _src_times(src, start_s, end_s, n):
        bgr = _png_frame(["-ss", str(t), "-i", str(src)])[..., :3]
        rgba = _png_frame(["-c:v", "libvpx-vp9", "-ss", str(round(t - off, 2)), "-i", str(webm)])
        h, w = bgr.shape[:2]
        if rgba.shape[:2] != (h, w):
            rgba = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
        a = rgba[..., 3:4].astype(np.float32) / 255.0
        page = np.array(PAGE[::-1], np.float32)
        res = page * (1 - a) + a * (rgba[..., :3].astype(np.float32) * page / 255.0)
        k = 360.0 / h
        tile = lambda im: cv2.resize(im, (int(w * k), 360), interpolation=cv2.INTER_AREA)  # noqa: E731
        alpha_vis = cv2.cvtColor((a[..., 0] * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        rows.append(np.hstack([tile(bgr), tile(alpha_vis), tile(np.clip(res, 0, 255).astype(np.uint8))]))
    cv2.imwrite(str(out_jpg), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
    return out_jpg


def _png_frame(args):
    p = subprocess.run(["ffmpeg", "-v", "error", *args, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                       capture_output=True, timeout=120)
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError("frame extract failed: " + p.stderr.decode("utf-8", "ignore")[-200:])
    return cv2.imdecode(np.frombuffer(p.stdout, np.uint8), cv2.IMREAD_UNCHANGED)


def _src_times(src, start_s, end_s, n):
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    dur = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / fps
    cap.release()
    a, b = (start_s or 0.0), (end_s or dur)
    return [round(a + (b - a) * (k + 0.5) / n, 2) for k in range(n)]


def key_quality(bgr, rgba, color, lim=None):
    """Judge one keyed frame against its source. fg = pixels clearly NOT the screen colour (must be solid),
    bg = pixels clearly the screen colour (must be gone), and no green may remain visible."""
    pl = (lim or limits()).get("protocol", {})
    h, w = bgr.shape[:2]
    if rgba.shape[:2] != (h, w):
        rgba = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
    alpha = rgba[..., 3].astype(float) / 255.0
    key = np.uint8([[[int(color[4:6], 16), int(color[2:4], 16), int(color[0:2], 16)]]])
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb).astype(float)
    kc = cv2.cvtColor(key, cv2.COLOR_BGR2YCrCb).astype(float)[0, 0]
    d = np.hypot(ycc[..., 1] - kc[1], ycc[..., 2] - kc[2]) / 255.0
    b_, g_, r_ = [bgr[..., i].astype(int) for i in range(3)]
    fg = (d > 0.22) & (g_ - np.maximum(r_, b_) < 10)
    bg = d < 0.05
    out = {"fg_share": round(float(fg.mean()), 3), "bg_share": round(float(bg.mean()), 3)}
    out["fg_alpha"] = round(float(alpha[fg].mean()), 4) if fg.sum() > 0.01 * fg.size else None
    out["fg_semi"] = round(float(((alpha[fg] > 0.05) & (alpha[fg] < 0.95)).mean()), 4) if fg.sum() > 0.01 * fg.size else None
    out["bg_alpha"] = round(float(alpha[bg].mean()), 4) if bg.sum() > 0.01 * bg.size else None
    rgb_g = (rgba[..., 1].astype(int) - np.maximum(rgba[..., 0], rgba[..., 2]).astype(int) > 40) & (rgba[..., 1] > 110)
    out["green_visible"] = round(float(((alpha > 0.5) & rgb_g).mean()), 4)
    ok = (out["fg_alpha"] is None or (out["fg_alpha"] >= pl.get("key_fg_alpha_min", 0.97) and out["fg_semi"] <= pl.get("key_semi_max", 0.05)))
    ok = ok and (out["bg_alpha"] is None or out["bg_alpha"] <= pl.get("key_bg_alpha_max", 0.04)) and out["green_visible"] <= 0.003
    out["ok"] = bool(ok)
    out["score"] = round((out["fg_alpha"] or 1.0) - (out["fg_semi"] or 0) - 2 * (out["bg_alpha"] or 0) - 20 * out["green_visible"], 4)
    return out


def _agg(per):
    f = [x["fg_alpha"] for x in per if x["fg_alpha"] is not None]
    return {"fg_alpha_min": round(min(f), 4) if f else None, "fg_semi_max": max([x["fg_semi"] or 0 for x in per]),
            "bg_alpha_max": max([x["bg_alpha"] or 0 for x in per]), "green_visible_max": max(x["green_visible"] for x in per),
            "ok": all(x["ok"] for x in per), "score": round(sum(x["score"] for x in per) / len(per), 4)}


def tune_key(src, color, start_s, end_s, lim, n=6):
    """Try the candidate settings on n real frames; first one that passes wins, else the best (if usable)."""
    times = _src_times(src, start_s, end_s, n)
    srcs = []
    for t in times:
        srcs.append((t, _png_frame(["-ss", str(t), "-i", str(src)])[..., :3]))
    best = None
    tried = []
    for sim, bl, ds in KEY_CANDIDATES:
        per = []
        for t, bgr in srcs:
            rgba = _png_frame(["-ss", str(t), "-i", str(src), "-vf", chroma_chain(color, sim, bl, ds) + ",format=rgba"])
            per.append(key_quality(bgr, rgba, color, lim))
        a = _agg(per)
        tried.append({"similarity": sim, "blend": bl, "despill": ds, **a})
        if best is None or a["score"] > best[1]["score"]:
            best = ((sim, bl, ds), a)
        if a["ok"]:
            return (sim, bl, ds), a, tried
    return best[0], best[1], tried


def verify_webm(src, webm, color, start_s, end_s, lim, n=3):
    """After the real encode: decode the WebM (libvpx keeps alpha) and judge it against the source again."""
    times = _src_times(src, start_s, end_s, n)
    off = start_s or 0.0
    per = []
    for t in times:
        bgr = _png_frame(["-ss", str(t), "-i", str(src)])[..., :3]
        rgba = _png_frame(["-c:v", "libvpx-vp9", "-ss", str(round(t - off, 2)), "-i", str(webm)])
        if rgba.ndim < 3 or rgba.shape[2] != 4:
            raise RuntimeError("the keyed WebM has no alpha channel")
        per.append(key_quality(bgr, rgba, color, lim))
    return _agg(per)


def _set_aside(path):
    """A failed output is renamed, never deleted (the repo has no delete calls), so it can never be reused as a good key."""
    path = Path(path)
    if path.exists():
        path.replace(path.with_name(path.name + ".failed"))


def chroma_key(src, out_dir, opts=None, lim=None):
    """Green-screen clip -> VP9 WebM with alpha at FULL source size, voice kept (opus). Tuned + verified on real frames.
    opts: color, similarity/blend/despill (skip tuning), start_s/end_s (only that window is keyed: samples are fast)."""
    lim = lim or limits()
    opts = opts if isinstance(opts, dict) else {}
    src, out_dir = Path(src), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    start_s, end_s = opts.get("start_s"), opts.get("end_s")
    color = (opts.get("color") or key_color(src, start_s=start_s, end_s=end_s)).lstrip("#").upper()
    manual = all(k in opts for k in ("similarity", "blend", "despill"))
    g_mode = opts.get("grade_mode", "auto")
    tag = f"{color}{opts.get('similarity')}{opts.get('blend')}{opts.get('despill')}{start_s}{end_s}g{g_mode}{opts.get("grade_strength")}s{SOLID}"
    dst = out_dir / f"{src.stem}.key.{_key(src, tag)}.webm"
    side = dst.with_suffix(".quality.json")
    if dst.exists() and side.exists():
        q = json.loads(side.read_text())
        return dst, color, q
    if manual:
        params = (float(opts["similarity"]), float(opts["blend"]), float(opts["despill"]))
        q = {"tuned": False, "params": params}
    else:
        params, agg, tried = tune_key(src, color, start_s, end_s, lim)
        q = {"tuned": True, "params": params, "frames": agg, "tried": len(tried)}
        if not agg["ok"] and ((agg["fg_alpha_min"] or 1) < 0.9 or agg["bg_alpha_max"] > 0.15 or agg["green_visible_max"] > 0.02):
            raise RuntimeError(f"chroma key quality too low on the real clip: {agg} (tried {len(tried)} settings). Light/green spill needs a manual look.")
    sim, bl, ds = params
    m = lim.get("matte", {})
    cube, g_rep = None, {"mode": g_mode}
    try:
        cube, g_rep = person_grade(src, color, start_s, end_s, g_mode, opts.get("grade_ref"), opts.get("grade_strength"), lim, out_dir)
    except Exception as e:  # noqa: BLE001  (a grading problem must never kill the key)
        g_rep = {"mode": g_mode, "error": f"{type(e).__name__}: {e}"[:200]}
    q["grade"] = g_rep
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if start_s:
        cmd += ["-ss", str(start_s)]
    cmd += ["-i", str(src)]
    if end_s:
        cmd += ["-t", str(round(end_s - (start_s or 0), 3))]
    cmd += ["-filter_complex", chroma_filter(color, sim, bl, ds, cube), "-map", "[v]", "-map", "0:a?",
            "-c:a", "libopus", "-b:a", "192k",
            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", str(m.get("key_crf", 18)),
            "-row-mt", "1", "-deadline", "good", "-cpu-used", str(m.get("key_cpu_used", 5)), "-auto-alt-ref", "0", str(dst)]
    rc, _, err = run_cmd(cmd, timeout=int(m.get("key_timeout_s", 3 * 3600)))
    if rc != 0:
        _set_aside(dst)
        raise RuntimeError("chroma key failed: " + tail(err, 3))
    v = verify_webm(src, dst, color, start_s, end_s, lim)
    q["verified"] = v
    if (v["fg_alpha_min"] or 1) < 0.9 or v["bg_alpha_max"] > 0.15:
        _set_aside(dst)
        raise RuntimeError(f"keyed WebM failed the check on real frames: {v}")
    try:
        q["check_image"] = key_check_image(src, dst, start_s, end_s, dst.with_suffix(".keycheck.jpg")).name
    except Exception as e:  # noqa: BLE001
        q["check_image_error"] = f"{type(e).__name__}: {e}"[:150]
    side.write_text(json.dumps(q), encoding="utf-8")
    return dst, color, q
