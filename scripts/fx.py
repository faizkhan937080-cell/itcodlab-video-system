"""Editing effects the worker prepares BEFORE the Remotion render (rules: rulebooks/14-effects.md).
Scene props it understands (video scenes): stabilize ('light'|'normal'), speed (0.1..8), speed_ramp [{at_s, speed}] (source seconds),
smooth (frame blending for slow motion), clean_voice, remove_bg, reframe ('auto' | [{t, x}]), track_from {box|'face'}.
`expand_plan(plan)` returns a COPY whose `props.src` points at the prepared files; the stored plan is never changed.
A failing effect keeps the clip as shot and says so in the report: an effect problem never kills a render.
Order per clip: stabilize -> retime -> (voice clean) -> background removal -> reframe/track path (needs the final timing).
"""
import copy
import hashlib
import json
import re
import shutil
from pathlib import Path

from .common import limits, log, run_cmd, tail

CRF = 12                       # intermediate files: near lossless, the final render does the real compression
SPEED_MIN, SPEED_MAX = 0.1, 8.0
MAX_SEGMENTS = 24


# ------------------------------------------------------------------ speed ramp / slow motion
def _speed_at(keys, t):
    """Linear interpolation of speed between keyframes (held before the first / after the last)."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, s0), (t1, s1) in zip(keys, keys[1:]):
        if t <= t1:
            k = (t - t0) / max(t1 - t0, 1e-9)
            return s0 + (s1 - s0) * k
    return keys[-1][1]


def ramp_segments(ramp, start, end, step=0.25):
    """Keyframes [{at_s, speed}] -> [(a, b, speed)] covering [start, end] of the SOURCE clip. Neighbouring pieces with almost the
    same speed are merged; the number of pieces is capped (the step grows)."""
    keys = sorted((float(k["at_s"]), min(max(float(k["speed"]), SPEED_MIN), SPEED_MAX)) for k in ramp)
    if not keys:
        return [(start, end, 1.0)]
    step = max(step, (end - start) / MAX_SEGMENTS)
    segs, t = [], start
    while t < end - 1e-6:
        b = min(end, t + step)
        s = _speed_at(keys, (t + b) / 2)
        if segs and abs(segs[-1][2] - s) / segs[-1][2] < 0.03:
            segs[-1] = (segs[-1][0], b, segs[-1][2])
        else:
            segs.append((t, b, s))
        t = b
    return [(round(a, 4), round(b, 4), round(s, 4)) for a, b, s in segs]


def out_duration(segs):
    return round(sum((b - a) / s for a, b, s in segs), 4)


def atempo_chain(s):
    """ffmpeg atempo only takes 0.5..2: chain it for bigger changes."""
    parts = []
    while s > 2.0 + 1e-9:
        parts.append(2.0)
        s /= 2.0
    while s < 0.5 - 1e-9:
        parts.append(0.5)
        s /= 0.5
    parts.append(s)
    return ",".join(f"atempo={p:.5f}" for p in parts)


def retime_graph(segs, has_audio, smooth_fps=None):
    n = len(segs)
    g = []
    for i, (a, b, s) in enumerate(segs):
        g.append(f"[0:v]trim=start={a}:end={b},setpts=(PTS-STARTPTS)/{s}[v{i}]")
        if has_audio:
            g.append(f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,{atempo_chain(s)}[a{i}]")
    ins = "".join(f"[v{i}]" + (f"[a{i}]" if has_audio else "") for i in range(n))
    vout = "vcx" if smooth_fps else "vc"
    g.append(f"{ins}concat=n={n}:v=1:a={1 if has_audio else 0}[{vout}]" + ("[ac]" if has_audio else ""))
    if smooth_fps:
        g.append(f"[vcx]minterpolate=fps={smooth_fps}:mi_mode=mci:mc_mode=aobmc:vsbmc=1[vc]")
    return ";".join(g)


def retime_clip(src, dst, props, info):
    """info = probe(src). Returns the segment list. The trim window (trim_start_s / trim_end_s) is consumed here."""
    start = float(props.get("trim_start_s") or 0.0)
    end = float(props.get("trim_end_s") or info["duration_s"])
    if props.get("speed_ramp"):
        segs = ramp_segments(props["speed_ramp"], start, end)
    else:
        segs = [(start, end, min(max(float(props.get("speed", 1.0)), SPEED_MIN), SPEED_MAX))]
    slow = any(s < 0.7 for _, _, s in segs)
    smooth = round(info["fps"] * 2) if props.get("smooth") and slow else None
    graph = retime_graph(segs, info["has_audio"], smooth)
    maps = ["-map", "[vc]"] + (["-map", "[ac]"] if info["has_audio"] else [])
    rc, _, err = run_cmd(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-filter_complex", graph, *maps, "-c:v", "libx264",
                          "-crf", str(CRF), "-preset", "medium", "-c:a", "aac", "-b:a", "320k", str(dst)], timeout=60 * 60 * 2)
    if rc != 0:
        raise RuntimeError("retime failed: " + tail(err, 3))
    return segs


# ------------------------------------------------------------------ stabilisation
def has_filter(name):
    rc, out, _ = run_cmd(["ffmpeg", "-hide_banner", "-filters"], timeout=60)
    return rc == 0 and re.search(rf"\s{name}\s", out or "") is not None


def stabilize_clip(src, dst, level, work):
    """vidstab (two pass) when this ffmpeg has it, else deshake. Returns the method used."""
    level = "light" if level == "light" else "normal"
    if has_filter("vidstabdetect"):
        trf = Path(work) / (Path(dst).stem + ".trf")
        rc, _, err = run_cmd(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf",
                              f"vidstabdetect=shakiness={5 if level == 'normal' else 3}:accuracy=15:result={trf}", "-f", "null", "-"],
                             timeout=60 * 60)
        if rc != 0:
            raise RuntimeError("stabilize pass 1 failed: " + tail(err, 2))
        vf = f"vidstabtransform=input={trf}:smoothing={15 if level == 'normal' else 8}:optzoom=1,unsharp=5:5:0.6:3:3:0.3"
        method = "vidstab"
    else:
        vf = "deshake=rx=24:ry=24:edge=mirror"
        method = "deshake"
    rc, _, err = run_cmd(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, "-c:v", "libx264", "-crf", str(CRF), "-preset", "medium",
                          "-c:a", "copy", str(dst)], timeout=60 * 60 * 2)
    if rc != 0:
        raise RuntimeError("stabilize failed: " + tail(err, 2))
    return method


# ------------------------------------------------------------------ constant frame rate + denoise
DENOISE = {"light": "hqdn3d=1.5:1.0:2.0:2.0", "normal": "hqdn3d=3:2:4:3"}


def cfr_denoise_clip(src, dst, fps, denoise=None):
    """Phone footage is often variable frame rate (audio drifts later). Re-time to a constant rate; optional mild denoise
    (grainy low-light footage). Audio is copied untouched."""
    vf = DENOISE.get(denoise)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src)] + (["-vf", vf] if vf else []) + [
        "-fps_mode", "cfr", "-r", str(fps), "-c:v", "libx264", "-crf", str(CRF), "-preset", "medium", "-c:a", "copy", str(dst)]
    rc, _, err = run_cmd(cmd, timeout=60 * 60 * 2)
    if rc != 0:
        raise RuntimeError("frame-rate fix failed: " + tail(err, 2))


# ------------------------------------------------------------------ zoom / punch-in keyframes
def punch_keys(times, scale=1.12, up_s=0.08, down_s=0.35, x=0.5, y=0.5, hold_s=0.0):
    """Beat/word times (scene seconds) -> zoom keyframes: snap in fast, ease back slowly. For scene.zoom (Remotion applies them)."""
    keys = [{"at_s": 0.0, "scale": 1.0, "x": x, "y": y}]
    last = 0.0
    for t in sorted(float(v) for v in times):
        t0 = max(t, last + 0.01)
        if t0 - keys[-1]["at_s"] < 0.005:
            continue
        keys.append({"at_s": round(t0, 3), "scale": 1.0, "x": x, "y": y})
        keys.append({"at_s": round(t0 + up_s, 3), "scale": scale, "x": x, "y": y})
        last = t0 + up_s + hold_s + down_s
        if hold_s:
            keys.append({"at_s": round(t0 + up_s + hold_s, 3), "scale": scale, "x": x, "y": y})
        keys.append({"at_s": round(last, 3), "scale": 1.0, "x": x, "y": y})
    return keys


# ------------------------------------------------------------------ film grain tile
def grain_tile(path, size=1024, sd=38.0, seed=7):
    """Mid-grey Gaussian noise tile (deterministic). Remotion overlays it with 'overlay' blend and shifts it every frame."""
    import cv2
    import numpy as np
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        n = np.random.default_rng(seed).normal(128, sd, (size, size)).clip(0, 255).astype(np.uint8)
        cv2.imwrite(str(path), n)
    return str(path)


# ------------------------------------------------------------------ orchestration
def _sig(*a):
    return hashlib.sha1(json.dumps(a, sort_keys=True, default=str).encode()).hexdigest()[:10]


def expand_plan(plan, public_dir=None, work=None, lim=None, hooks=None):
    """-> (plan_copy, report). `hooks` lets tests replace heavy parts: {"matte": fn(src,dst), "face": fn, ...}."""
    from .analyze import probe
    from .render import REMOTION_DIR
    lim = lim or limits()
    pub = Path(public_dir or REMOTION_DIR / "public")
    work = Path(work or pub.parent / "_fx_work")
    work.mkdir(parents=True, exist_ok=True)
    (pub / "fx").mkdir(parents=True, exist_ok=True)
    hooks = hooks or {}
    from .plan_edit import apply_jl_cuts
    new, jl_notes = apply_jl_cuts(plan)             # before effects: needs the original trim windows
    rep = {"clips": {}, "errors": {}, "audio": {}, "jl_cuts": jl_notes}
    done = {}
    for sc in new.get("scenes", []):
        p = sc.get("props") or {}
        src = p.get("src")
        wants = [k for k in ("stabilize", "speed", "speed_ramp", "clean_voice", "remove_bg", "reframe", "track_from", "denoise") if p.get(k)]
        if isinstance(src, str) and sc.get("template") == "video" and (pub / src).exists() and (hooks.get("vfr") or _is_vfr)(pub / src):
            wants.insert(0, "cfr")
        if not wants or not isinstance(src, str):
            continue
        key = (sc["id"], src)
        r = rep["clips"].setdefault(sc["id"], {"effects": wants})
        try:
            cur = pub / src
            if not cur.exists():
                raise FileNotFoundError(f"{src} not staged")
            is_video = cur.suffix.lower() in (".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi")
            if is_video and ("cfr" in wants or p.get("denoise")):
                out = pub / "fx" / f"{cur.stem}.{_sig(src, p.get('denoise'), new.get('fps'))}.cfr.mp4"
                if not out.exists():
                    (hooks.get("cfr") or cfr_denoise_clip)(cur, out, new.get("fps", 30), p.get("denoise"))
                cur = out
                p["src"] = f"fx/{out.name}"
                src = p["src"]
                r["cfr"] = True
            if is_video and (p.get("stabilize") or p.get("speed") or p.get("speed_ramp")):
                tag = _sig(src, p.get("stabilize"), p.get("speed"), p.get("speed_ramp"), p.get("trim_start_s"), p.get("trim_end_s"), p.get("smooth"))
                out = pub / "fx" / f"{cur.stem}.{tag}.mp4"
                if not out.exists():
                    s_in = cur
                    if p.get("stabilize"):
                        mid = work / f"{cur.stem}.{tag}.stab.mp4"
                        r["stabilize"] = (hooks.get("stabilize") or stabilize_clip)(cur, mid, p["stabilize"], work)
                        s_in = mid
                    if p.get("speed") or p.get("speed_ramp"):
                        segs = (hooks.get("retime") or retime_clip)(s_in, out, p, probe(s_in))
                        r["segments"] = [list(s) for s in segs] if segs else None
                        r["out_duration_s"] = out_duration(segs) if segs else None
                    else:
                        shutil.copyfile(s_in, out)
                cur = out
                for k in ("trim_start_s", "trim_end_s", "speed", "speed_ramp", "smooth"):
                    p.pop(k, None)           # consumed: the new file already has that timing
                p["src"] = f"fx/{out.name}"
            if p.get("clean_voice") and is_video:
                from . import voice
                out = pub / "fx" / f"{Path(p['src']).stem}.voice.mp4"
                if not out.exists():
                    voice.clean_video_audio(pub / p["src"], out)
                p["src"] = f"fx/{out.name}"
                r["clean_voice"] = True
            if p.get("remove_bg"):
                from . import matte
                out = matte.process(pub / p["src"], pub / "fx", remover=hooks.get("matte"))
                p["src"] = f"fx/{out.name}"
                if out.suffix.lower() == ".webm":
                    p["transparent"] = True
                r["remove_bg"] = out.name
            if is_video and (p.get("reframe") or p.get("track_from")):
                from . import track
                info = probe(pub / p["src"])
                t_start, t_end = float(p.get("trim_start_s") or 0.0), p.get("trim_end_s")   # gone after a retime: then 0 / end
                if p.get("reframe") == "auto":
                    p["reframe_path"] = track.reframe_path(pub / p["src"], info, aspect=p.get("reframe_aspect", 9 / 16), start_s=t_start, end_s=t_end, t0=t_start, face=hooks.get("face"))
                    p["src_aspect"] = round(info["width"] / info["height"], 5)
                    r["reframe"] = len(p["reframe_path"])
                elif isinstance(p.get("reframe"), list):
                    p["reframe_path"] = p["reframe"]
                    p["src_aspect"] = round(info["width"] / info["height"], 5)
                if p.get("track_from"):
                    tf = p["track_from"]
                    p["follow"] = track.follow_path(pub / p["src"], tf.get("box") or "face", tf.get("start_s", t_start), tf.get("end_s", t_end), t0=t_start, face=hooks.get("face"))
                    r["follow_points"] = len(p["follow"])
        except Exception as e:  # noqa: BLE001
            rep["errors"][sc["id"]] = f"{type(e).__name__}: {e}"[:200]
            log(f"effect failed on scene {sc['id']}: {e}")
            sc["props"] = copy.deepcopy(next(s for s in plan["scenes"] if s["id"] == sc["id"]).get("props") or {})
            for k in ("stabilize", "speed", "speed_ramp", "clean_voice", "remove_bg", "reframe", "track_from", "denoise"):
                sc["props"].pop(k, None)     # keep the clip as shot, drop the effect that failed
    if new.get("grain") and not new.get("grain_src"):
        grain_tile(pub / "fx" / "grain.png")
        new["grain_src"] = "fx/grain.png"
    try:
        from . import voice
        new, rep["audio"] = voice.prepare_audio(new, pub, work, hooks=hooks)
    except Exception as e:  # noqa: BLE001
        rep["errors"]["audio"] = f"{type(e).__name__}: {e}"[:200]
    return new, rep


def _is_vfr(path):
    from .qa import vfr
    return vfr(path)


def summary_line(rep):
    n = len(rep.get("clips", {}))
    bad = len(rep.get("errors", {}))
    return f"effects: {n} clip(s) prepared" + (f", {bad} problem(s) (kept as shot)" if bad else "")
