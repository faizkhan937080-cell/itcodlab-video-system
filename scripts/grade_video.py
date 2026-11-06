"""Colour grading, file side (ffmpeg / OpenCV). Maths lives in grade.py; rules in rulebooks/13-grade.md.
- reference_stats(video): the 'look' of a reference reel (written to <reel>/grade.json during analysis).
- grade_plan(plan, storage): before a render, grade the staged footage/images the plan uses and return a plan copy that points
  at the graded files (originals and the stored plan are never touched). Never raises: a failure keeps the ungraded clip and says so.
Standard delivery = SDR Rec.709, 8-bit 4:2:0, tagged bt709. HDR (iPhone HLG/PQ) is tone-mapped to SDR first, because Instagram's own
tone-mapping looks washed out. Footage and reference are both measured AFTER conversion to SDR, so a look is never compared across different transfer curves.
"""
import copy
import hashlib
import json
import shutil
from pathlib import Path

import cv2
import numpy as np

from . import grade as G
from .common import limits, log, run_cmd, tail

HDR_TRANSFERS = {"smpte2084": "pq", "arib-std-b67": "hlg"}
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
HDR_TO_SDR = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
              "zscale=t=bt709:m=bt709:r=tv:dither=error_diffusion,format=yuv420p")
TAG = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
LUT_CHAIN = ("scale=in_range=tv:in_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,format=gbrp,"
             "lut3d=file={cube}:interp=tetrahedral,"
             "scale=out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,format=yuv420p")


def transfer_of(video):
    """'sdr' | 'pq' | 'hlg' from the stream's colour tags (ffprobe)."""
    rc, out, _ = run_cmd(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                          "-of", "csv=p=0", str(video)], timeout=60)
    return HDR_TRANSFERS.get((out or "").strip().split(",")[0], "sdr") if rc == 0 else "sdr"


def has_zscale():
    rc, out, _ = run_cmd(["ffmpeg", "-hide_banner", "-filters"], timeout=60)
    return rc == 0 and " zscale " in (out or "")


def sdr_prefix(transfer):
    """Filter text that brings the picture to SDR Rec.709 before measuring/grading ('' when already SDR)."""
    return HDR_TO_SDR if transfer in ("pq", "hlg") else ""


def build_vf(transfer, cube=None):
    parts = []
    if transfer in ("pq", "hlg"):
        parts.append(HDR_TO_SDR)
    if cube:
        parts.append(LUT_CHAIN.format(cube=str(cube).replace("\\", "/").replace(":", r"\:")))
    return ",".join(parts)


def sample_frames(video, work, n=12, long_edge=320, transfer="sdr"):
    """n frames spread over the clip as float RGB arrays (small: the maths needs shape, not 4K)."""
    from .analyze import probe
    import tempfile
    Path(work).mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=work))          # fresh folder per call: nothing to clean up
    dur = max(probe(video)["duration_s"], 0.1)
    n = max(1, min(n, int(dur * 4) or 1))
    vf = ",".join(x for x in (sdr_prefix(transfer), f"fps={n}/{dur:.3f}", f"scale=-2:{long_edge}") if x)
    rc, _, err = run_cmd(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", vf, "-frames:v", str(n),
                          str(work / "gf_%03d.png")], timeout=900)
    if rc != 0:
        raise RuntimeError("frame sampling failed: " + tail(err, 2))
    return [cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0 for p in sorted(work.glob("gf_*.png"))]


def pool(frames, cap=60000):
    flat = np.concatenate([f.reshape(-1, 1, 3) for f in frames])
    return flat[:: max(1, len(flat) // cap)]


def reference_stats(video, work, lim=None):
    """Look of one reference reel. Stored with its transfer so it is never matched against a different curve."""
    t = transfer_of(video)
    if t != "sdr" and not has_zscale():
        return {"transfer": t, "usable": False, "reason": "HDR source but this ffmpeg has no zscale: look not measured"}
    st = G.measure(sample_frames(video, work, transfer=t), lim)
    st.update({"transfer": t, "usable": True, "measured_as": "sdr_rec709"})
    return st


# ------------------------------------------------------------------ one file
def _read_img(path):
    im = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def grade_image(src, dst, params):
    im = G.apply_params(_read_img(src), params)
    out = cv2.cvtColor((im * 255.0 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR)
    ok = cv2.imwrite(str(dst), out, [cv2.IMWRITE_JPEG_QUALITY, 97])
    if not ok:
        raise RuntimeError("could not write graded image")


def grade_video_file(src, dst, params, transfer, work, crf):
    """Re-encode once: [HDR->SDR] + 3D LUT, tagged bt709, audio copied. identity + SDR is never sent here (no generation loss)."""
    cube = None
    if not G.is_identity(params):
        cube = G.write_cube(Path(work) / (Path(dst).stem + ".cube"), G.make_lut(params))
    vf = build_vf(transfer, cube)
    if not vf:
        raise RuntimeError("nothing to do")
    rc, _, err = run_cmd(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
                          "-pix_fmt", "yuv420p", *TAG, "-c:a", "copy", "-movflags", "+faststart", str(dst)], timeout=60 * 60 * 2)
    if rc != 0:
        raise RuntimeError("ffmpeg grade failed: " + tail(err, 3))


def _key(rel, mode, ref, strength):
    return hashlib.sha1(json.dumps([rel, mode, ref, strength], sort_keys=True, default=str).encode()).hexdigest()[:10]


def grade_one(path, mode, ref, strength, work, lim):
    """-> (graded_path_or_None, report). None = keep the original."""
    path = Path(path)
    is_img = path.suffix.lower() in IMG_EXT
    transfer = "sdr" if is_img else transfer_of(path)
    rep = {"mode": mode, "transfer": transfer}
    if transfer != "sdr" and not has_zscale():
        rep["skipped"] = "HDR clip but no zscale in ffmpeg: left as is (needs a human look)"
        return None, rep
    if mode == "off":
        params = dict(G.IDENTITY)
        rep["notes"] = ["grade off"]
    else:
        frames = [_read_img(path)] if is_img else sample_frames(path, Path(work) / "samples", transfer=transfer)
        if is_img:
            h, w = frames[0].shape[:2]
            k = 320.0 / max(h, w)
            frames = [cv2.resize(frames[0], (max(1, int(w * k)), max(1, int(h * k))), interpolation=cv2.INTER_AREA)]
        stats = G.measure(frames, lim)
        params, notes = G.solve(stats, pool(frames), mode, ref, lim, strength)
        rep.update({"stats": {k: stats[k] for k in ("p1", "p50", "p99", "colourfulness", "skin_hue", "spread")},
                    "params": {k: (round(v, 4) if isinstance(v, float) else [round(x, 4) for x in v] if isinstance(v, list) else v) for k, v in params.items()},
                    "verify": G.verify(pool(frames), params, stats, ref, lim)})
        rep["notes"] = rep.get("notes", []) + notes + stats["warnings"]
    need = (transfer != "sdr") or not G.is_identity(params, lim)
    if not need:
        rep["changed"] = False
        return None, rep
    out_dir = Path(work) / "graded"
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"{path.stem}.{_key(str(path), mode, bool(ref), strength)}{path.suffix if is_img else '.mp4'}"
    if not dst.exists():
        if is_img:
            grade_image(path, dst, params)
        else:
            grade_video_file(path, dst, params, transfer, work, G.cfg(lim).get("intermediate_crf", 12))
    rep["changed"] = True
    return dst, rep


# ------------------------------------------------------------------ whole plan
def graded_targets(plan):
    """(scene index, key, rel) of footage / pictures the grade applies to. Graphics, paper cut-outs and text are never graded."""
    out = []
    for i, sc in enumerate(plan.get("scenes", [])):
        src = (sc.get("props") or {}).get("src")
        if isinstance(src, str) and sc.get("template") in ("video", "image") and src.startswith(("assets/", "input/")):
            out.append((i, src))
    return out


def grade_plan(plan, storage=None, public_dir=None, work=None, lim=None):
    """-> (plan_copy_for_render, report). report = {"mode", "files": {rel: report}, "errors": {...}}."""
    lim = lim or limits()
    g = plan.get("grade") or {}
    mode = g.get("mode", "auto")
    from .render import REMOTION_DIR
    pub = Path(public_dir or REMOTION_DIR / "public")
    work = Path(work or pub.parent / "_grade_work")
    work.mkdir(parents=True, exist_ok=True)
    ref = None
    if g.get("ref") and mode == "auto" and storage is not None:
        try:
            ref = storage.read_json(g["ref"])
            if not ref.get("usable", True):
                ref = None
        except Exception as e:  # noqa: BLE001
            log(f"grade reference not readable ({g['ref']}): {type(e).__name__}")
    new = copy.deepcopy(plan)
    report = {"mode": mode, "reference": g.get("ref") if ref else None, "files": {}, "errors": {}}
    cache = {}
    for i, rel in graded_targets(plan):
        if rel not in cache:
            f = pub / rel
            if not f.exists():
                report["errors"][rel] = "file not staged"
                cache[rel] = None
                continue
            try:
                dst, rep = grade_one(f, mode, ref, g.get("strength"), work, lim)
                report["files"][rel] = rep
                if dst is not None:
                    pub_rel = f"graded/{dst.name}"
                    (pub / "graded").mkdir(parents=True, exist_ok=True)
                    if not (pub / pub_rel).exists():
                        shutil.copyfile(dst, pub / pub_rel)
                    cache[rel] = pub_rel
                else:
                    cache[rel] = None
            except Exception as e:  # noqa: BLE001  (a grading problem must never kill the render)
                report["errors"][rel] = f"{type(e).__name__}: {e}"[:200]
                cache[rel] = None
        if cache.get(rel):
            new["scenes"][i]["props"]["src"] = cache[rel]
    return new, report


def summary_line(report):
    """One short line for the job note."""
    n = sum(1 for r in report.get("files", {}).values() if r.get("changed"))
    bad = len(report.get("errors", {}))
    return f"grade {report.get('mode')}: {n} file(s) changed" + (f", {bad} problem(s) (kept as shot)" if bad else "")
