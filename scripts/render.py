"""Remotion render wrapper + output checks. Claude never renders; this script does.
Preview = scale 0.5 of the output size. Final = full output size: same as the biggest raw clip (4K in -> 4K out),
else the 4K master default (limits.render.master).
"""
import json
import os
from pathlib import Path

from .analyze import probe
from .common import ROOT, limits, log, run_cmd, tail
from .dna import errors_tail, validate

REMOTION_DIR = ROOT / "remotion"


VIDEO_EXT = (".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi")


def _even(n):
    return int(n) // 2 * 2


def source_clips(plan):
    """Raw video clips used by the plan (scene props.src ending in a video extension)."""
    return sorted({(sc.get("props") or {}).get("src") for sc in plan["scenes"]
                   if isinstance((sc.get("props") or {}).get("src"), str)
                   and (sc.get("props") or {}).get("src").lower().endswith(VIDEO_EXT)})


def master_size(plan, lim=None, source_dims=None):
    """Output size. Order: plan.output > largest raw clip (match_source) > master default for the orientation.
    4K raw in -> 4K out. Never upscales a clip beyond itself, never exceeds max_long_edge_px."""
    lim = lim or limits()
    r = lim["render"]
    if plan.get("output"):
        w, h = plan["output"]["width"], plan["output"]["height"]
    elif r.get("match_source") and source_dims:
        w, h = max(source_dims, key=lambda d: d[0] * d[1])
        cap = r.get("max_long_edge_px", 7680)
        if max(w, h) > cap:
            k = cap / float(max(w, h))
            w, h = w * k, h * k
        w, h = _even(w), _even(h)
    else:
        m = r["master"][plan["orientation"]]
        w, h = m["width"], m["height"]
    return w, h


def probe_sources(plan, public_dir=None):
    """Display size of every staged raw clip (rotation-aware). Missing files are skipped."""
    pub = Path(public_dir or REMOTION_DIR / "public")
    dims = []
    for rel in source_clips(plan):
        f = pub / rel
        if f.exists():
            p = probe(f)
            dims.append((p["width"], p["height"]))
    return dims


def plan_duration_s(plan):
    return round(sum(s["duration_s"] for s in plan["scenes"]), 3)


def _asset_paths(node, found):
    if isinstance(node, dict):
        for v in node.values():
            _asset_paths(v, found)
    elif isinstance(node, list):
        for v in node:
            _asset_paths(v, found)
    elif isinstance(node, str) and node.startswith(("assets/", "input/")):
        found.add(node)


def stage_assets(plan, storage):
    """Copy Drive files referenced as 'assets/...' or 'input/...' (raw footage) into remotion/public/ (never deletes)."""
    found = set()
    _asset_paths(plan, found)
    for rel in sorted(found):
        dest = REMOTION_DIR / "public" / rel
        if not dest.exists():
            storage.fetch(rel, dest)
    return sorted(found)


def ensure_node_deps():
    if (REMOTION_DIR / "node_modules" / ".bin" / "remotion").exists():
        return
    log("installing Remotion dependencies (first run only)")
    rc, out, err = run_cmd(["npm", "install", "--no-audit", "--no-fund"], cwd=str(REMOTION_DIR), timeout=900)
    if rc != 0:
        raise RuntimeError("npm install failed:\n" + tail(err or out))


def check_output(out_path, plan, quality, lim=None, size=None):
    lim = lim or limits()
    out_path = Path(out_path)
    problems = []
    if not out_path.exists() or out_path.stat().st_size == 0:
        return {"ok": False, "problems": ["output file missing or empty"], "probe": None}
    p = probe(out_path)
    w, h = size or master_size(plan, lim)
    scale = lim["render"]["preview_scale"] if quality == "preview" else 1.0
    ew, eh = int(round(w * scale)), int(round(h * scale))
    if (p["width"], p["height"]) != (ew, eh):
        problems.append(f"size {p['width']}x{p['height']} != expected {ew}x{eh}")
    if p["codec"] != "h264":
        problems.append(f"codec {p['codec']} != h264")
    tol = lim["render"]["duration_tolerance_s"]
    if abs(p["duration_s"] - plan_duration_s(plan)) > max(tol, 2.0 / plan["fps"]):
        problems.append(f"duration {p['duration_s']}s != planned {plan_duration_s(plan)}s")
    return {"ok": not problems, "problems": problems, "probe": p}


def render_plan(plan, quality, out_path, storage=None, concurrency=None):
    """plan: dict (already validated). Returns check dict. Raises RuntimeError on render failure."""
    lim = limits()
    errs = validate("scene", plan)
    if errs:
        raise RuntimeError("plan invalid:\n" + errors_tail(errs))
    if storage is not None:
        stage_assets(plan, storage)
    ensure_node_deps()
    w, h = master_size(plan, lim, probe_sources(plan))
    scale = lim["render"]["preview_scale"] if quality == "preview" else 1.0
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    props = dict(plan)
    props["width"], props["height"] = w, h
    props_file = out_path.with_suffix(".props.json")
    props_file.write_text(json.dumps(props), encoding="utf-8")
    m = lim["render"]["master"]
    cmd = ["npx", "remotion", "render", "src/index.ts", "Main", str(out_path),
           f"--props={props_file}", f"--codec={m['codec']}", f"--crf={m['crf']}",
           f"--pixel-format={m['pixel_format']}", f"--color-space={m['colorspace']}",
           f"--scale={scale}"]
    if concurrency or os.environ.get("ITCOD_RENDER_CONCURRENCY"):
        cmd.append(f"--concurrency={concurrency or os.environ['ITCOD_RENDER_CONCURRENCY']}")
    if os.environ.get("ITCOD_BROWSER"):  # use an installed Chromium instead of downloading one
        cmd += [f"--browser-executable={os.environ['ITCOD_BROWSER']}", "--chrome-mode=chrome-for-testing"]
    log(f"rendering {quality}: {w}x{h} x{scale}")
    rc, out, err = run_cmd(cmd, cwd=str(REMOTION_DIR), timeout=60 * 60 * 3)
    if rc != 0:
        raise RuntimeError("remotion render failed:\n" + tail(err or out))
    return check_output(out_path, plan, quality, lim, size=(w, h))
