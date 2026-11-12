"""Preview render that re-renders only the shots that changed (2026-11-12 speed-up, rulebook 17).

The timeline is cut at every shot boundary (layout segments, underlays, overlays). Each piece gets a fingerprint of
everything that can change its pixels: the Remotion code, the plan's global settings, the elements and caption
words around it, size and quality. Pieces are rendered as lossless PNG frames and kept on the worker
(~/.cache/itcod/frames/<fingerprint>/). A new plan version renders only pieces whose fingerprint is new, then
ONE ffmpeg encode makes the video from all frames + one audio render. Same frames + same encode = identical file
whether a piece came from the cache or was rendered fresh (tests/test_render_chunks.py, worker bench).
Previews only: the final render stays one full Remotion pass (rule 2)."""
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from .common import ROOT, log, tail

CACHE = Path(os.environ.get("ITCOD_CHUNK_CACHE", Path.home() / ".cache" / "itcod"))
REMOTION_DIR = ROOT / "remotion"
SKIP_KEYS = {"scenes", "captions", "protocol", "_clone", "_ref_record", "title", "audio"}


def _h(obj):
    return hashlib.sha1(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def code_hash():
    """Every file that can change a frame: remotion/src + lockfile + public/ files are referenced by path in plans."""
    h = hashlib.sha1()
    for p in sorted((REMOTION_DIR / "src").rglob("*")):
        if p.is_file():
            h.update(p.relative_to(REMOTION_DIR).as_posix().encode())
            h.update(p.read_bytes())
    for name in ("package-lock.json", "package.json", "remotion.config.ts"):
        f = REMOTION_DIR / name
        if f.exists():
            h.update(f.read_bytes())
    return h.hexdigest()


def eligible(plan):
    sc = plan.get("scenes") or []
    return len(sc) == 1 and not sc[0].get("transition_in")


def cut_points(plan, min_len_s=1.0):
    """Shot boundaries of a single-scene plan (seconds), short pieces merged into the one before."""
    sc = plan["scenes"][0]
    dur = float(sc["duration_s"])
    pts = {0.0, dur}
    for seg in (sc.get("props") or {}).get("layout") or []:
        pts.add(float(seg.get("from_s", 0)))
    for el in (sc.get("underlays") or []) + (sc.get("overlays") or []):
        for k in ("start_s", "end_s"):
            if isinstance(el.get(k), (int, float)):
                pts.add(float(el[k]))
    pts = sorted(p for p in pts if 0 <= p <= dur)
    out = [pts[0]]
    for p in pts[1:]:
        if p - out[-1] >= min_len_s or p == dur:
            out.append(p)
    if len(out) > 2 and out[-1] - out[-2] < min_len_s:
        out.pop(-2)
    return list(zip(out[:-1], out[1:]))


def piece_key(plan, a, b, fa, fb, extra):
    """Fingerprint of one piece [a, b) seconds = frames fa..fb inclusive."""
    sc = plan["scenes"][0]
    props = dict(sc.get("props") or {})
    layout = props.pop("layout", None) or []
    active = [s for s in layout if s.get("from_s", 0) <= a]
    segs = ([active[-1]] if active else []) + [s for s in layout if a < s.get("from_s", 0) < b]
    def over(el):
        s0 = el.get("start_s", 0)
        s1 = el.get("end_s", sc["duration_s"])
        return s0 < b and s1 > a
    els = [e for e in (sc.get("underlays") or []) if over(e)], [e for e in (sc.get("overlays") or []) if over(e)]
    caps = [c for c in plan.get("captions") or [] if c.get("start_s", 0) < b + 3 and c.get("end_s", 0) > a - 3]
    glob = {k: v for k, v in plan.items() if k not in SKIP_KEYS}
    scene_rest = {k: v for k, v in sc.items() if k not in ("props", "underlays", "overlays")}
    return _h({"v": 1, "frames": [fa, fb], "glob": glob, "scene": scene_rest, "props": props, "segs": segs,
               "els": els, "caps": caps, **extra})


def audio_key(plan, extra):
    """Sound depends on the clips, trims, volumes and audio tracks, not on captions or graphics."""
    sc = [{k: v for k, v in s.items() if k not in ("underlays", "overlays")} for s in plan["scenes"]]
    for s in sc:
        s["props"] = {k: v for k, v in (s.get("props") or {}).items() if k != "layout"}
    return _h({"v": 1, "scenes": sc, "audio": plan.get("audio"), "fps": plan.get("fps"),
               "lufs": plan.get("audio_target_lufs"), "code": extra["code"]})


def _remotion(args, timeout):
    cmd = ["npx", "remotion", "render", "src/index.ts", "Main", *args]
    if os.environ.get("ITCOD_BROWSER"):
        cmd += [f"--browser-executable={os.environ['ITCOD_BROWSER']}", "--chrome-mode=chrome-for-testing"]
    if os.environ.get("ITCOD_RENDER_CONCURRENCY"):
        cmd.append(f"--concurrency={os.environ['ITCOD_RENDER_CONCURRENCY']}")
    r = subprocess.run(cmd, cwd=str(REMOTION_DIR), capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("remotion render failed:\n" + tail(r.stderr or r.stdout))


def render(props_file, plan, out_path, scale, master, fps, total_frames, timeout_s):
    """-> report dict. props_file already holds the final props (width/height set)."""
    extra = {"code": code_hash(), "scale": scale, "w": plan.get("width"), "h": plan.get("height"),
             "crf": master["crf"], "pix": master["pixel_format"]}
    frames_dir = CACHE / "frames"
    t_start = time.time()
    pieces, fresh = [], 0
    for a, b in cut_points(plan):
        fa = int(a * fps + 0.5)                    # JS Math.round, like sceneFrames()
        fb = total_frames - 1 if b >= float(plan["scenes"][0]["duration_s"]) else min(int(b * fps + 0.5) - 1, total_frames - 1)
        if fb < fa:
            continue
        key = piece_key(plan, a, b, fa, fb, extra)
        d = frames_dir / key
        n = fb - fa + 1
        if not (d / "done").exists() or len(list(d.glob("*.png"))) != n:
            shutil.rmtree(d, ignore_errors=True)
            tmp = d.with_name("tmp_" + key)   # Remotion: a sequence folder name must have no extension
            shutil.rmtree(tmp, ignore_errors=True)
            tmp.mkdir(parents=True)
            _remotion([str(tmp), f"--props={props_file}", "--sequence", "--image-format=png", f"--frames={fa}-{fb}",
                       f"--scale={scale}"], timeout_s)
            got = sorted(tmp.glob("*.png"))
            if len(got) != n:
                raise RuntimeError(f"piece {fa}-{fb}: {len(got)} frames, expected {n}")
            for i, f in enumerate(got):
                f.rename(tmp / f"{i:06d}.png")
            (tmp / "done").write_text(key)
            tmp.rename(d)
            fresh += 1
        pieces.append((fa, fb, d))
    t_frames = time.time() - t_start
    # one audio render per sound fingerprint
    ak = audio_key(plan, extra)
    aud = CACHE / "audio" / f"{ak}.aac"
    if not aud.exists():
        aud.parent.mkdir(parents=True, exist_ok=True)
        tmp = aud.with_suffix(".tmp.aac")
        _remotion([str(tmp), f"--props={props_file}", "--codec=aac"], timeout_s)
        tmp.rename(aud)
    # all frames, in order, through ONE encoder pass (hard links: no copying)
    seq = Path(out_path).with_suffix(".seq")
    shutil.rmtree(seq, ignore_errors=True)
    seq.mkdir(parents=True)
    k = 0
    for _fa, _fb, d in pieces:
        for p in sorted(d.glob("*.png")):
            os.link(p, seq / f"{k:06d}.png")
            k += 1
    if k != total_frames:
        raise RuntimeError(f"{k} frames, expected {total_frames}")
    # fixed thread count: x264 output is then the same on every machine of this kind (identical-file proof)
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(fps), "-i", str(seq / "%06d.png"), "-i", str(aud),
           "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "medium", "-threads", "4",
           "-crf", str(master["crf"]), "-pix_fmt", master["pixel_format"],
           "-colorspace", master["colorspace"], "-color_primaries", master["colorspace"], "-color_trc", master["colorspace"],
           "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    shutil.rmtree(seq, ignore_errors=True)
    if r.returncode != 0:
        raise RuntimeError("encode failed:\n" + tail(r.stderr))
    rep = {"pieces": len(pieces), "fresh": fresh, "reused": len(pieces) - fresh,
           "frames_s": round(t_frames, 1), "total_s": round(time.time() - t_start, 1)}
    log(f"chunked preview: {rep}")
    return rep
