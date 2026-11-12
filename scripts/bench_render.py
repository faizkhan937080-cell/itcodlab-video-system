"""Render speed benchmark with an equality proof (rulebook 17: a speed-up only counts if the output is identical).
Renders the same frames of a real plan at several Remotion concurrency values, times each, and compares every
decoded frame (ffmpeg framemd5). Report -> Drive costs/compare/render_bench_<utc>.json."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from .common import log, now_iso


def framemd5(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-f", "framemd5", "-"],
                       capture_output=True, text=True, timeout=900)
    return [ln.split(",")[-1].strip() for ln in r.stdout.splitlines() if ln and not ln.startswith("#")]


def run(plan, storage, frames=(0, 299), concurrencies=(2, 3, 4), quality="preview"):
    from .render import render_plan, stage_assets
    stage_assets(plan, storage)
    rows, ref = [], None
    with tempfile.TemporaryDirectory(prefix="itcod-bench-") as wd:
        for i, c in enumerate([concurrencies[0], *concurrencies]):   # first pass warms the bundle/cache, not counted
            out = Path(wd) / f"c{c}_{i}.mp4"
            t0 = time.time()
            render_plan(plan, quality, out, storage=None, concurrency=c, frames=frames)
            dt = round(time.time() - t0, 1)
            if i == 0:
                log(f"bench warm-up c={c}: {dt}s")
                continue
            md5 = framemd5(out)
            ref = ref or md5
            rows.append({"concurrency": c, "seconds": dt, "frames": len(md5), "identical_to_first": md5 == ref})
            log(f"bench c={c}: {dt}s, {len(md5)} frames, identical={md5 == ref}")
    ok = [r for r in rows if r["identical_to_first"]]
    best = min(ok, key=lambda r: r["seconds"]) if ok else None
    rep = {"ts": now_iso(), "cpus": os.cpu_count(), "frames": list(frames), "quality": quality, "rows": rows,
           "best": best, "rule": "only identical outputs may be chosen (rulebook 17)"}
    rel = f"costs/compare/render_bench_{rep['ts'].replace(':', '').replace('-', '')}.json"
    try:
        storage.put_json(rel, rep)
    except Exception as e:  # noqa: BLE001
        log(f"bench report upload failed: {e}")
    print(json.dumps(rep, indent=1))
    return rep


def _psnr(a, b):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(a), "-i", str(b), "-lavfi", "[0:v][1:v]psnr", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=1800)
    line = [ln for ln in r.stderr.splitlines() if "PSNR" in ln and "average" in ln]
    return line[-1].split("average:")[1].split()[0] if line else "n/a"


def chunks(plan, storage):
    """Proof + speed of 'render only changed shots' on a real plan:
    A cold chunked render of plan P; B = P with its LAST shot changed, rendered warm (reuses A's pieces);
    C = the same B rendered cold (empty cache). B and C must have identical frames and sound.
    Also: chunked vs normal one-pass Remotion render of P (quality report, PSNR)."""
    import copy
    from . import render_chunks
    from .render import render_plan, stage_assets
    from .common import limits
    stage_assets(plan, storage)
    lim = limits()
    lim_on = dict(lim)
    rep = {"ts": now_iso(), "cpus": os.cpu_count()}
    p2 = copy.deepcopy(plan)
    und = p2["scenes"][0].get("underlays") or []
    if und:
        und[-1].setdefault("props", {})["_bench_touch"] = 1   # changes only the last shot's fingerprint
    with tempfile.TemporaryDirectory(prefix="itcod-chunks-") as wd:
        wd = Path(wd)
        os.environ["ITCOD_CHUNK_CACHE"] = str(wd / "cacheA")
        render_chunks.CACHE = wd / "cacheA"
        import scripts.render as R
        old = R.limits
        R.limits = lambda: {**lim_on, "render": {**lim_on["render"], "chunk_cache": True}}
        try:
            t = time.time(); render_plan(plan, "preview", wd / "A.mp4"); rep["A_cold_s"] = round(time.time() - t, 1)
            t = time.time(); render_plan(p2, "preview", wd / "B.mp4"); rep["B_warm_s"] = round(time.time() - t, 1)
            render_chunks.CACHE = wd / "cacheC"
            t = time.time(); render_plan(p2, "preview", wd / "C.mp4"); rep["C_cold_s"] = round(time.time() - t, 1)
        finally:
            R.limits = old
        os.environ["ITCOD_NO_CHUNKS"] = "1"
        t = time.time(); render_plan(plan, "preview", wd / "D.mp4"); rep["D_onepass_s"] = round(time.time() - t, 1)
        os.environ.pop("ITCOD_NO_CHUNKS", None)
        vb, vc = framemd5(wd / "B.mp4"), framemd5(wd / "C.mp4")
        def amd5(f):
            r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-map", "0:a:0", "-f", "md5", "-"],
                               capture_output=True, text=True, timeout=600)
            return r.stdout.strip()
        rep["B_equals_C_frames"] = vb == vc and len(vb) > 0
        rep["B_equals_C_sound"] = amd5(wd / "B.mp4") == amd5(wd / "C.mp4")
        rep["frames"] = len(vb)
        rep["psnr_chunked_vs_onepass"] = _psnr(wd / "A.mp4", wd / "D.mp4")
    rep["pass"] = rep["B_equals_C_frames"] and rep["B_equals_C_sound"]
    rel = f"costs/compare/chunks_bench_{rep['ts'].replace(':', '').replace('-', '')}.json"
    try:
        storage.put_json(rel, rep)
    except Exception as e:  # noqa: BLE001
        log(f"bench report upload failed: {e}")
    print(json.dumps(rep, indent=1))
    return rep
