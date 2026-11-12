"""Clone mode (Faiz 2026-11-12: "99% like the reference"). A plan with protocol.clone is a copy of ONE reference reel:

  protocol.clone = {
    "reel": "DfMQ7zqkuxO",                                  reference reel id
    "ref_video": "creators/<h>/reel-<id>/source.mp4",        Drive path of the reference video
    "shots": [{"out": [a, b], "ref": [c, d], "what": "split: table card over talking head"}, ...],
    "min_score": 0.85                                        optional, never below limits clone.min_score
  }

Rules checked here (worker side, cannot be skipped):
  1. no in-house templates: only media (video, image, lottie) + `ext` (outside add-on from remotion/src/ext/REGISTRY.json)
     + `clone` (a replica component of THIS reel, registered with source clone:<reel>)
  2. captions use an outside caption component (caption_style.look = "ext") and a Google font
  3. the shot map covers the whole output, every shot points at a real moment of the reference
  4. protocol.reference is a complete style record (no 'none')
After each render: every shot is scored against its reference moment (layout + colour + structure) and a side-by-side
collage (ref | ours, with the score) is what Claude must look at. Any shot under min_score -> back to the plan.
"""
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .common import ROOT, limits

MEDIA = {"video", "image", "lottie"}
WRAPPERS = {"ext", "clone"}
FONTS_FILE = ROOT / "config" / "google_fonts.json"


def _registry():
    try:
        return json.loads((ROOT / "remotion" / "src" / "ext" / "REGISTRY.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _google_fonts():
    try:
        return set(json.loads(FONTS_FILE.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return set()


def _items(plan):
    """(where, template, props) for every scene, underlay and overlay."""
    for i, s in enumerate(plan.get("scenes", [])):
        yield f"scene {i + 1}", s.get("template"), s.get("props") or {}
        for k in ("underlays", "overlays"):
            for j, o in enumerate(s.get(k) or []):
                yield f"scene {i + 1} {k[:-1]} {j + 1}", o.get("template"), o.get("props") or {}


def _fonts_in(obj):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("font", "fontFamily", "font_family") and isinstance(v, str):
                out.append(v)
            else:
                out += _fonts_in(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _fonts_in(v)
    return out


def check_plan(plan, total_s, lim=None):
    b = plan.get("protocol") or {}
    c = b.get("clone")
    if not c:
        return []
    errs = []
    reel = c.get("reel")
    reg = _registry()
    if b.get("reference") in (None, "", "none"):
        errs.append("clone: protocol.reference must be the COMPLETE style record of the reference reel (never 'none').")
    for where, t, p in _items(plan):
        if t in MEDIA:
            continue
        if t not in WRAPPERS:
            errs.append(f"clone: {where} uses in-house template '{t}'. Clone mode allows only {sorted(MEDIA | WRAPPERS)}.")
            continue
        name = p.get("component")
        e = reg.get(name)
        if not e:
            errs.append(f"clone: {where} component '{name}' is not in remotion/src/ext/REGISTRY.json (add it with ./run addon add).")
        elif t == "ext" and e.get("source", "").startswith("clone:"):
            errs.append(f"clone: {where} '{name}' is a replica, use template 'clone' for it.")
        elif t == "clone" and e.get("source") != f"clone:{reel}":
            errs.append(f"clone: {where} replica '{name}' belongs to {e.get('source')}, not clone:{reel}.")
    cs = plan.get("caption_style") or {}
    if plan.get("captions"):
        if cs.get("look") != "ext" or not reg.get(cs.get("component", "")):
            errs.append("clone: captions must use an outside caption component (caption_style.look='ext', component=<registry name>).")
    gf = _google_fonts()
    for f in _fonts_in(plan) + ([cs["font"]] if cs.get("font") else []):
        if gf and f not in gf:
            errs.append(f"clone: font '{f}' is not a Google font from @remotion/google-fonts.")
    shots = sorted(c.get("shots") or [], key=lambda s: s["out"][0])
    if not shots:
        errs.append("clone: protocol.clone.shots (map of output time -> reference time) is empty.")
    else:
        t = 0.0
        for s in shots:
            a, bb = s["out"]
            if a - t > 0.15:
                errs.append(f"clone: output {t:.2f}-{a:.2f}s has no reference shot.")
            if not s.get("ref") or s["ref"][1] <= s["ref"][0]:
                errs.append(f"clone: shot {a}-{bb}s has no reference time.")
            t = max(t, bb)
        if total_s - t > 0.15:
            errs.append(f"clone: output {t:.2f}-{total_s:.2f}s has no reference shot.")
    if float(c.get("min_score", 1)) < float((lim or limits()).get("clone", {}).get("min_score", 0.85)):
        errs.append("clone: min_score below the system minimum (config/limits.json clone.min_score).")
    return errs


# ------------------------------------------------------------------ scoring
def _read(cap, t):
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000)
    ok, fr = cap.read()
    return fr if ok else None


def _norm(fr, w=90, h=160):
    return cv2.resize(fr, (w, h), interpolation=cv2.INTER_AREA)


def _ssim(a, b):
    a, b = a.astype(np.float64), b.astype(np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mu_a, mu_b = cv2.GaussianBlur(a, (7, 7), 1.5), cv2.GaussianBlur(b, (7, 7), 1.5)
    sa = cv2.GaussianBlur(a * a, (7, 7), 1.5) - mu_a ** 2
    sb = cv2.GaussianBlur(b * b, (7, 7), 1.5) - mu_b ** 2
    sab = cv2.GaussianBlur(a * b, (7, 7), 1.5) - mu_a * mu_b
    m = ((2 * mu_a * mu_b + c1) * (2 * sab + c2)) / ((mu_a ** 2 + mu_b ** 2 + c1) * (sa + sb + c2))
    return float(np.clip(m.mean(), 0, 1))


def score(ref_bgr, out_bgr):
    """0..1 per part. colour = Lab grid (6x10 cells, dE76 mapped: 0 -> 1, 40+ -> 0); layout = bright/dark zone map
    agreement; structure = SSIM of the blurred grey picture (big shapes, not small details or the face)."""
    r, o = _norm(ref_bgr), _norm(out_bgr)
    rl = cv2.cvtColor(r, cv2.COLOR_BGR2LAB).astype(np.float64)
    ol = cv2.cvtColor(o, cv2.COLOR_BGR2LAB).astype(np.float64)
    rg = cv2.resize(rl, (6, 10), interpolation=cv2.INTER_AREA)
    og = cv2.resize(ol, (6, 10), interpolation=cv2.INTER_AREA)
    rg[..., 0] *= 100 / 255
    og[..., 0] *= 100 / 255
    de = np.sqrt(((rg - og) ** 2).sum(-1))
    colour = float(np.clip(1 - de / 40, 0, 1).mean())
    rgr, ogr = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY), cv2.cvtColor(o, cv2.COLOR_BGR2GRAY)
    rz = cv2.resize(rgr, (9, 16), interpolation=cv2.INTER_AREA) > 128
    oz = cv2.resize(ogr, (9, 16), interpolation=cv2.INTER_AREA) > 128
    layout = float((rz == oz).mean())
    structure = _ssim(cv2.GaussianBlur(rgr, (5, 5), 0), cv2.GaussianBlur(ogr, (5, 5), 0))
    total = 0.4 * colour + 0.35 * layout + 0.25 * structure
    return {"colour": round(colour, 3), "layout": round(layout, 3), "structure": round(structure, 3), "total": round(total, 3)}


def _shot_times(s, step=1.0):
    """Frame-by-frame pairs (Faiz 2026-11-12): one pair about every `step` seconds of the shot, the reference time
    moving at the same rate as the shot map (ref time warped linearly onto output time)."""
    a, b = s["out"]
    c, d = s["ref"]
    n = max(1, int(round((b - a) / step)))
    out = []
    for k in range(n):
        f = (k + 0.5) / n
        out.append((round(a + (b - a) * f, 2), round(c + (d - c) * f, 2)))
    return out


def match(out_video, ref_video, clone, out_dir, lim=None):
    """Score every shot; write collage_match.jpg (pairs ref | ours with the score). Returns summary dict."""
    lim = lim or limits()
    floor = max(float(clone.get("min_score", 0)), float(lim.get("clone", {}).get("min_score", 0.85)))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    co, cr = cv2.VideoCapture(str(out_video)), cv2.VideoCapture(str(ref_video))
    rows = []
    for s in sorted(clone.get("shots") or [], key=lambda x: x["out"][0]):
        for to, tr in _shot_times(s):
            fo, fr = _read(co, to), _read(cr, tr)
            if fo is None or fr is None:
                rows.append({"out_t": to, "ref_t": tr, "what": s.get("what", ""), "error": "frame not readable", "total": 0.0})
                continue
            sc = score(fr, fo)
            rows.append({"out_t": to, "ref_t": tr, "what": s.get("what", ""), **sc, "_fr": fr, "_fo": fo})
    co.release()
    cr.release()
    pairs = [r for r in rows if "_fr" in r]
    path = None
    if pairs:   # at most 24 pairs on one sheet (collage cap), worst first so problems are seen
        pairs = sorted(pairs, key=lambda r: r["total"])[:24]
        tw, th = 180, 320
        cols = 4
        nrows = math.ceil(len(pairs) / cols)
        sheet = Image.new("RGB", (cols * tw * 2, nrows * (th + 18)), (40, 40, 40))
        d = ImageDraw.Draw(sheet)
        for i, r in enumerate(pairs):
            x, y = (i % cols) * tw * 2, (i // cols) * (th + 18)
            for j, fr in enumerate((r["_fr"], r["_fo"])):
                im = Image.fromarray(cv2.cvtColor(cv2.resize(fr, (tw, th)), cv2.COLOR_BGR2RGB))
                sheet.paste(im, (x + j * tw, y + 18))
            col = (0, 220, 0) if r["total"] >= floor else (255, 60, 60)
            d.text((x + 3, y + 3), f"ref {r['ref_t']:.1f}s | ours {r['out_t']:.1f}s | {r['total'] * 100:.0f}%", fill=col)
        path = out_dir / "collage_match.jpg"
        sheet.save(path, quality=88)
    for r in rows:
        r.pop("_fr", None)
        r.pop("_fo", None)
    tot = [r["total"] for r in rows]
    low = [r for r in rows if r["total"] < floor]
    return {"min_score": floor, "mean": round(float(np.mean(tot)), 3) if tot else 0.0, "min": round(min(tot), 3) if tot else 0.0,
            "pass": bool(rows) and not low, "low": [{k: r[k] for k in ("out_t", "ref_t", "what", "total")} for r in low][:8],
            "rows": rows, "collage": path.name if path else None,
            "sha": hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path else None}
