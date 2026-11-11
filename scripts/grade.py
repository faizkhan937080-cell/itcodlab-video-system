"""Colour grading, pure numbers (numpy only). Rules: rulebooks/13-grade.md.
Modes: auto (default: fix + match the reference reel's look), natural (fix only), off (no look change).
Everything is measured and closed-loop: measure -> solve -> apply -> measure again. No taste, no guessing.
Pixels here are sRGB-encoded floats 0..1, shape (H, W, 3), RGB order. Tone/white-balance maths runs in linear light.
Measured defaults (limits.json `grade`): median luma ~0.45, black point ~0.02, white ~0.95, skin hue ~20 deg,
colourfulness acted on only outside a 25..95 band (Hasler-Suesstrunk), white balance = Shades-of-Gray(p=6) + White-Patch.
"""
import math

import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
DEFAULTS = {
    "median_luma": 0.45, "median_deadband": 0.05, "black": 0.02, "black_trigger": 0.04, "white": 0.95, "white_trigger": 0.80,
    "colourfulness_band": [25.0, 95.0], "skin_hue_deg": 20.0, "skin_hue_tol": 4.0, "skin_min_fraction": 0.02,
    "wb_limit": 0.15, "exposure_limit_stops": 1.0, "contrast_limit": [0.85, 1.25], "sat_limit": [0.7, 1.4],
    "hue_limit_deg": 8.0, "strength": 0.85, "spread_warn": 0.20, "levels_gain_max": 1.5, "wb_deadband": 0.02, "identity_eps": 0.012,
}
SKIN_CB, SKIN_CR = (77, 127), (133, 173)   # classic YCbCr skin locus (8-bit)


def cfg(lim=None):
    d = dict(DEFAULTS)
    d.update(((lim or {}).get("grade")) or {})
    return d


def to_linear(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055).astype(np.float32)


def luma(rgb):
    return rgb @ LUMA


# ------------------------------------------------------------------ measure
def _hsv_hue_sat(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(mx)
    m = d > 1e-6
    rc = m & (mx == r)
    gc = m & (mx == g) & ~rc
    bc = m & ~rc & ~gc
    h[rc] = ((g - b)[rc] / d[rc]) % 6
    h[gc] = (b - r)[gc] / d[gc] + 2
    h[bc] = (r - g)[bc] / d[bc] + 4
    return h * 60.0, s


def colourfulness(rgb):
    """Hasler & Suesstrunk (2003), 0..255 scale. ~0 grey, 25..95 normal, >95 very saturated."""
    p = rgb.reshape(-1, 3) * 255.0
    rg = p[:, 0] - p[:, 1]
    yb = 0.5 * (p[:, 0] + p[:, 1]) - p[:, 2]
    return float(math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean()))


def wb_gains(rgb):
    """Gains (linear light) that neutralise a colour cast: mean of Shades-of-Gray(p=6) and White-Patch estimates (log domain).
    White-Patch is skipped when highlights clip. Returned normalised so luma is unchanged."""
    lin = to_linear(rgb).reshape(-1, 3)
    sog = np.power(np.mean(np.power(lin, 6.0), axis=0), 1 / 6.0)
    est = [sog / max(float(sog.mean()), 1e-6)]
    hi = np.percentile(rgb.reshape(-1, 3), 99.5, axis=0)
    if float(hi.max()) < 0.98 and float(hi.min()) > 0.2:
        wp = to_linear(hi.astype(np.float32))
        est.append(wp / max(float(wp.mean()), 1e-6))
    e = np.exp(np.mean([np.log(np.maximum(x, 1e-6)) for x in est], axis=0))
    g = 1.0 / np.maximum(e, 1e-6)
    return g / float(g @ LUMA)


def skin(rgb):
    """-> (fraction of pixels in the skin locus, median hue deg or None)."""
    u8 = rgb * 255.0
    y = 0.299 * u8[..., 0] + 0.587 * u8[..., 1] + 0.114 * u8[..., 2]
    cb = 128 - 0.168736 * u8[..., 0] - 0.331264 * u8[..., 1] + 0.5 * u8[..., 2]
    cr = 128 + 0.5 * u8[..., 0] - 0.418688 * u8[..., 1] - 0.081312 * u8[..., 2]
    m = (cb >= SKIN_CB[0]) & (cb <= SKIN_CB[1]) & (cr >= SKIN_CR[0]) & (cr <= SKIN_CR[1]) & (y > 50) & (y < 235)
    frac = float(m.mean())
    if m.sum() < 50:
        return frac, None
    h, _ = _hsv_hue_sat(rgb[m])
    h = np.where(h > 180, h - 360, h)
    return frac, float(np.median(h))


def measure_frame(rgb):
    y = luma(rgb)
    p1, p50, p99 = (float(v) for v in np.percentile(y, [1, 50, 99]))
    mid = (y > 0.25) & (y < 0.75)
    mid_rgb = rgb[mid].mean(0) if mid.sum() > 100 else rgb.reshape(-1, 3).mean(0)
    ratio = mid_rgb / max(float(mid_rgb @ LUMA), 1e-6)
    sf, sh = skin(rgb)
    _, sat = _hsv_hue_sat(rgb)
    return {"p1": p1, "p50": p50, "p99": p99, "colourfulness": colourfulness(rgb), "saturation": float(sat.mean()),
            "wb_gains": [float(v) for v in wb_gains(rgb)], "mid_ratio": [float(v) for v in ratio],
            "skin_fraction": sf, "skin_hue": sh}


def _med(vals):
    v = [x for x in vals if x is not None]
    return float(np.median(v)) if v else None


def measure(frames, lim=None):
    """Median over sampled frames (one odd frame cannot move the grade). `spread` = how much brightness varies inside the clip:
    above limits.grade.spread_warn one global grade fits badly, and the report says so."""
    c = cfg(lim)
    ms = [measure_frame(f) for f in frames]
    if not ms:
        raise ValueError("no frames to measure")
    out = {k: _med([m[k] for m in ms]) for k in ("p1", "p50", "p99", "colourfulness", "saturation", "skin_fraction")}
    out["wb_gains"] = [_med([m["wb_gains"][i] for m in ms]) for i in range(3)]
    out["mid_ratio"] = [_med([m["mid_ratio"][i] for m in ms]) for i in range(3)]
    out["skin_hue"] = _med([m["skin_hue"] for m in ms if m["skin_fraction"] >= c["skin_min_fraction"]])
    out["contrast"] = out["p99"] - out["p1"]
    p50s = [m["p50"] for m in ms]
    out["spread"] = float(max(p50s) - min(p50s))
    out["frames"] = len(ms)
    out["warnings"] = ["brightness varies a lot inside this clip: one global grade fits it only roughly"] if out["spread"] > c["spread_warn"] else []
    return {k: (round(v, 5) if isinstance(v, float) else ([round(x, 5) for x in v] if k in ("wb_gains", "mid_ratio") else v))
            for k, v in out.items()}


# ------------------------------------------------------------------ apply
IDENTITY = {"gains": [1.0, 1.0, 1.0], "exposure": 1.0, "black_in": 0.0, "white_in": 1.0, "black_out": 0.0, "white_out": 1.0,
            "contrast": 1.0, "saturation": 1.0, "hue_deg": 0.0, "strength": 1.0}


def apply_params(rgb, p):
    """The one grade function: used for images, for the .cube table and for the closed-loop check (so all three agree)."""
    p = {**IDENTITY, **p}
    lin = to_linear(rgb) * (np.array(p["gains"], dtype=np.float32) * np.float32(p["exposure"]))
    e = to_srgb(lin)
    span_in = max(p["white_in"] - p["black_in"], 1e-3)
    e = (e - p["black_in"]) / span_in * (p["white_out"] - p["black_out"]) + p["black_out"]
    pivot = 0.45
    e = pivot + (e - pivot) * p["contrast"]
    y = (np.clip(e, 0, 1) @ LUMA)[..., None]
    e = y + (e - y) * p["saturation"]
    if abs(p["hue_deg"]) > 1e-6:                   # rotate chroma in the YIQ plane (keeps luma)
        a = math.radians(p["hue_deg"])
        yiq = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]], dtype=np.float32)
        rot = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]], dtype=np.float32)
        m = np.linalg.inv(yiq) @ rot @ yiq
        e = e @ m.T
    e = np.clip(e, 0.0, 1.0)
    s = p["strength"]
    return (rgb * (1 - s) + e * s).astype(np.float32) if s < 1.0 else e.astype(np.float32)


def is_identity(p, lim=None):
    """True when the grade would change nothing visible: then the clip is not re-encoded (no needless generation loss)."""
    eps = cfg(lim)["identity_eps"]
    q = {**IDENTITY, **p}
    d = [abs(g - 1) for g in q["gains"]] + [abs(q["exposure"] - 1), abs(q["black_in"] - q["black_out"]), abs(q["white_in"] - q["white_out"]),
                                             abs(q["contrast"] - 1), abs(q["saturation"] - 1), abs(q["hue_deg"]) / 90.0]
    return max(d) < eps or q["strength"] <= 0


# ------------------------------------------------------------------ solve
def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _median_after(pix, p):
    return float(np.median(luma(apply_params(pix, {**p, "strength": 1.0}))))


SKIN_LUMA = (0.48, 0.68)   # a face is exposed right between these (sRGB luma); outside -> exposure moves it to the nearest edge


def solve(stats, pixels, mode="auto", ref=None, lim=None, strength=None, face_pixels=None):
    """stats = measure(...) of the footage, pixels = a pooled sample (N,1,3) for the closed loop, ref = stats of the reference
    (same shape) or None. Returns (params, notes). `off` -> identity. `natural` -> fix only. `auto` -> fix + reference look."""
    c = cfg(lim)
    notes = []
    if mode == "off":
        return dict(IDENTITY), ["grade off: footage unchanged"]
    use_ref = mode == "auto" and ref is not None
    if mode == "auto" and ref is None:
        notes.append("no reference look given: fix-only (natural)")
    p = dict(IDENTITY)
    # 1) white balance (+ tint of the reference)
    g = np.array(stats["wb_gains"], dtype=np.float32)
    g = np.where(np.abs(g - 1) < c["wb_deadband"], 1.0, g)
    if use_ref:
        want = np.array(ref["mid_ratio"], dtype=np.float32) / np.maximum(np.array(stats["mid_ratio"], dtype=np.float32), 1e-3)
        g = g * (want ** 0.6)
        g = g / float(g @ LUMA)
    lim_w = c["wb_limit"]
    p["gains"] = [float(_clamp(v, 1 - lim_w, 1 + lim_w)) for v in g]
    # 2+4) contrast (reference only, bounded), then exposure + black/white point as a small closed loop:
    #      exposure is bounded to +-1 stop with a dead band (low-key looks survive); levels only fix hazy blacks / flat whites.
    if use_ref and stats["contrast"] > 0.05:
        p["contrast"] = float(_clamp(ref["contrast"] / stats["contrast"], *c["contrast_limit"]))
    target = float(_clamp(ref["p50"], 0.25, 0.65)) if use_ref else c["median_luma"]
    expo = pixels
    if face_pixels is not None and len(face_pixels) >= 500:
        # talking head: the FACE sets the exposure (a navy shirt and dark hair must not push the skin into white)
        expo = face_pixels
        target = float(_clamp(_median_after(expo, p), *SKIN_LUMA))
        notes.append(f"exposure judged on the face (median luma {_median_after(expo, p):.2f}, wanted {SKIN_LUMA[0]}..{SKIN_LUMA[1]})")
    base = _median_after(expo, p)
    for _ in range(3):
        if abs(_median_after(expo, p) - target) > c["median_deadband"]:
            lo, hi = -c["exposure_limit_stops"], c["exposure_limit_stops"]
            for _i in range(14):
                mid = (lo + hi) / 2
                p["exposure"] = float(2 ** mid)
                lo, hi = (mid, hi) if _median_after(expo, p) < target else (lo, mid)
        probe = {**p, "black_in": 0.0, "white_in": 1.0, "black_out": 0.0, "white_out": 1.0, "contrast": 1.0, "saturation": 1.0}
        y = luma(apply_params(pixels, {**probe, "strength": 1.0}))
        p1e, p99e = (float(v) for v in np.percentile(y, [1, 99]))
        p["black_in"] = float(p1e - c["black"]) if p1e > c["black_trigger"] else 0.0
        p["white_in"] = float(max(p99e / c["white"], 0.6)) if p99e < c["white_trigger"] else 1.0
        span = p["white_in"] - p["black_in"]
        if span < 1.0 / c["levels_gain_max"]:       # flat scene (white wall, fog): do not blow it up to full range
            mid = (p["white_in"] + p["black_in"]) / 2
            half = 0.5 / c["levels_gain_max"]
            p["black_in"], p["white_in"] = max(0.0, mid - half), min(1.0, mid + half)
    if p["exposure"] != 1.0:
        notes.append(f"exposure {math.log2(p['exposure']):+.2f} stop(s): median luma {base:.2f} -> ~{target:.2f}")
    if p["black_in"]:
        notes.append(f"black point lifted to ~{c['black']}")
    if p["white_in"] < 1.0:
        notes.append(f"white point stretched to ~{c['white']}")
    # 5) saturation: reference colourfulness, else only pull back / push up outside the 25..95 band
    cf = stats["colourfulness"]
    band = c["colourfulness_band"]
    if use_ref:
        p["saturation"] = float(_clamp(ref["colourfulness"] / max(cf, 1.0), *c["sat_limit"]))
    elif cf > band[1]:
        p["saturation"] = float(_clamp(band[1] / cf, *c["sat_limit"]))
    elif cf < band[0] and cf > 3.0:
        p["saturation"] = float(_clamp(band[0] / cf, *c["sat_limit"]))
    # 6) skin hue towards ~20 deg, small and only when skin is really in the picture
    if stats.get("skin_hue") is not None and stats["skin_fraction"] >= c["skin_min_fraction"]:
        off = c["skin_hue_deg"] - stats["skin_hue"]
        if abs(off) > c["skin_hue_tol"]:
            p["hue_deg"] = float(_clamp(off * 0.5, -c["hue_limit_deg"], c["hue_limit_deg"]))
            notes.append(f"skin hue {stats['skin_hue']:.0f} -> ~{c['skin_hue_deg']:.0f} deg ({p['hue_deg']:+.1f} turn)")
    p["strength"] = float(strength if strength is not None else (c["strength"] if use_ref else 1.0))
    return p, notes


def verify(pixels, params, stats_before, ref=None, lim=None):
    """Closed loop: apply, measure again, say how close we are. ok = brightness near target (or as near as the +-1 stop bound
    allows) and blacks not hazy, whites not clipped. `limited` tells the report when a bound stopped the grade."""
    c = cfg(lim)
    after = measure([apply_params(pixels, params)], lim)
    target = float(_clamp(ref["p50"], 0.25, 0.65)) if ref else c["median_luma"]
    tol = max(c["median_deadband"], 0.07)
    limited = abs(math.log2(max(params.get("exposure", 1.0), 1e-6))) >= c["exposure_limit_stops"] - 0.01
    closer = abs(after["p50"] - target) < abs(stats_before["p50"] - target)
    checks = {"median_luma": abs(after["p50"] - target) <= tol or abs(stats_before["p50"] - target) <= c["median_deadband"] or (limited and closer),
              "black_not_hazy": after["p1"] <= 0.08 or after["p1"] <= stats_before["p1"],
              "highlights_not_clipped": after["p99"] <= 0.995}
    return {"after": {k: after[k] for k in ("p1", "p50", "p99", "colourfulness", "saturation")}, "target_median": round(target, 3),
            "limited_by_bound": limited, "checks": checks, "ok": all(checks.values())}


# ------------------------------------------------------------------ 3D LUT (.cube)
def make_lut(params, size=33):
    """size^3 table, red varies fastest (the .cube order). Built with apply_params, so it is the same grade."""
    t = np.linspace(0.0, 1.0, size, dtype=np.float32)
    b, g, r = np.meshgrid(t, t, t, indexing="ij")
    grid = np.stack([r, g, b], axis=-1).reshape(-1, 1, 3)
    return apply_params(grid, params).reshape(-1, 3)


def write_cube(path, lut, title="itcodlab grade"):
    size = round(len(lut) ** (1 / 3))
    rows = "\n".join(f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in lut)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f'TITLE "{title}"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n{rows}\n')
    return path
