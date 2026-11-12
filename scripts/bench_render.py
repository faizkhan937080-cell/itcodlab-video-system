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
