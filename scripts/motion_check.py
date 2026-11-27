"""Motion-graphics QA gate (no rendering): reads the kinematic spec of every 3D object and the plan beats,
samples each beat at 12+ moments and BLOCKs the mistakes Faiz had to repeat: part sinks through its base, object
clipped by the frame/canvas, too small, empty band, caption/object overlap, object that does not move or never settles.
`./run motion-check <plan.json>`; also `./run gate-check motion-geom <plan.json>`. BLOCK = fix the object, never the gate."""
import hashlib
import json
import re
from pathlib import Path

from . import motion_geom as G

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "config" / "motion-specs" / "potter.json"
TSX = ROOT / "remotion" / "src" / "components" / "PotterObjects.tsx"
CW, CH = 1080, 1920
DEF = {"samples": 14, "pen_tol": 0.03, "contact_tol": 0.06, "min_fill": 0.20, "clip_frac": 0.04,
       "safe_margin": 0.03, "min_signal_range": 0.08, "min_sway": 0.3, "max_gap_frac": 0.22, "rest_eps": 0.02, "settle_s": 0.25}


def limits():
    try:
        d = json.loads((ROOT / "config" / "limits.json").read_text(encoding="utf-8")).get("motion_check", {})
    except (OSError, ValueError):
        d = {}
    return {**DEF, **d}


def load_spec(path=SPEC):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def tsx_sha(name, src=None):
    """Hash of one object's component source, so a changed TSX forces the spec to be re-verified."""
    s = src if src is not None else TSX.read_text(encoding="utf-8")
    cls = name[0].upper() + name[1:]
    m = re.search(r"const %s: React\.FC.*?\n\};" % cls, s, re.S)
    return hashlib.sha1(m.group(0).encode()).hexdigest()[:12] if m else ""


def _times(a, b, n):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def contact_check(spec, dur, L):
    """(a) a moving part must never sink below its base surface; (c-contact) a striker must reach it."""
    ts = _times(0.0, dur, max(L["samples"], 12) * 8)
    parts = spec["parts"]
    base = [p for p in parts if p["role"] == "base"]
    worst, gap_min, bad = 0.0, 9.0, ""
    for t in ts:
        for m in (p for p in parts if p["role"] in ("mover", "striker")):
            mx, my, mz, mhx, mhy, mhz, _ = G.part_box(m, spec, t)
            for b in base:
                bx, by, bz, bhx, bhy, bhz, _ = G.part_box(b, spec, t)
                if abs(mx - bx) >= mhx + bhx or abs(mz - bz) >= mhz + bhz:
                    continue
                top, low = by + bhy, my - mhy
                if my + mhy < by - bhy:
                    continue
                pen = top - low
                if pen > worst:
                    worst, bad = pen, f"{m['id']} sinks {pen:.2f} into {b['id']} at t={t:.2f}s"
                if m["role"] == "striker":
                    gap_min = min(gap_min, low - top)
    out = []
    if worst > L["pen_tol"]:
        out.append(("BLOCK", f"penetration: {bad} (tol {L['pen_tol']}); swing from a pivot above the surface, stop at contact"))
    if spec.get("contact") and gap_min > L["contact_tol"] and worst <= L["pen_tol"]:
        out.append(("BLOCK", f"striker never touches the base (closest gap {gap_min:.2f})"))
    return out


def move_check(spec, dur, L):
    """(c) object performs: an own signal with real range, and non-looping ones settle before the beat ends."""
    out = []
    ts = _times(0.3, max(dur, 0.8), max(L["samples"], 12))
    sig = spec.get("signals", {})
    if not sig:
        if spec["pose"]["sway"] >= L["min_sway"] or spec["pose"]["spin"] > 0:
            out.append(("WARN", "object itself is static, only camera sway/turn (give it its own motion)"))
        else:
            out.append(("BLOCK", "object does not move at all"))
        return out
    best = 0.0
    for name, (ex, loop) in sig.items():
        vv = spec.get("pivot", {}).get("vars")
        v = [G.ev(ex, t, vv) for t in ts]
        best = max(best, max(v) - min(v))
        if not loop:
            d_end = abs(G.ev(ex, ts[-1], vv) - G.ev(ex, ts[-1] - L["settle_s"], vv))
            if d_end > L["rest_eps"] and dur > 1.5:
                out.append(("WARN", f"{name} still moving at beat end (not at rest)"))
    if best < L["min_signal_range"]:
        out.append(("BLOCK", f"own motion too small (range {best:.2f} < {L['min_signal_range']})"))
    return out


def frame_check(spec, o, L):
    """(b) projected extent: inside the card canvas, inside the safe frame, and filling enough of the card."""
    b = o["box"]
    pw, ph = round(b["w"] * CW), round(b["h"] * CH)
    left, top = b["x"] * CW - pw / 2, b["y"] * CH - ph / 2
    P, sc0 = spec["pose"], spec["scale"]
    t0, t1 = 0.4, max(o["t1"] - o["t0"] - 0.25, 0.8)
    xs, ys, fills = [], [], []
    for lt in _times(t0, t1, L["samples"]):
        pose = (P["tilt"], P["yaw"] + P["sway"] * G.math.sin(lt * 1.5) + P["spin"] * lt, G.math.sin(lt * 2.0) * 0.04)
        pts = [G.project(c, pose, sc0, pw, ph) for p in spec["parts"] for c in G.corners(p, spec, lt)]
        x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
        y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
        xs += [x0, x1]
        ys += [y0, y1]
        fills.append((x1 - x0) * (y1 - y0) / (CW * CH))
    out = []
    sev = "WARN" if spec.get("approx") else "BLOCK"     # approx = coarse bounding boxes, so frame findings only warn
    ex, ey = L["clip_frac"] * pw, L["clip_frac"] * ph
    if min(xs) < -ex or max(xs) > pw + ex or min(ys) < -ey or max(ys) > ph + ey:
        out.append((sev, "object clipped by the card edge"))
    fx0, fx1 = left + min(xs), left + max(xs)
    m = L["safe_margin"] * CW
    if fx0 < -ex or fx1 > CW + ex:
        out.append((sev, f"outside safe frame (x {fx0:.0f}..{fx1:.0f} of {CW})"))
    f = sorted(fills)[len(fills) // 2]
    if f < L["min_fill"]:
        out.append(("BLOCK", f"object too small: fills {f:.0%} of the frame (min {L['min_fill']:.0%})"))
    return out, (top + min(ys), top + max(ys), fx0, fx1)


def caption_boxes(caps, t):
    boxes = []
    for c in caps:
        if c["t0"] <= t <= c["t1"]:
            cy = (c.get("y") or 0.235) * CH
            h = sum(1.25 * {"s": 96, "i": 96, "b": 124, "p": 156, "r": 98, "c": 124}.get(max(l, key=lambda w: len(w["w"]))["st"], 100) for l in c["lines"])
            boxes.append((cy - h / 2, cy + h / 2))
    return boxes


def layout_check(o, ext, caps, L):
    """(d) caption/object overlap and the biggest empty vertical band between caption and object."""
    out = []
    oy0, oy1 = ext[0], ext[1]
    tm = (o["t0"] + o["t1"]) / 2
    cb = caption_boxes(caps, tm) or caption_boxes(caps, o["t0"] + 0.8)
    for c0, c1 in cb:
        if min(c1, oy1) - max(c0, oy0) > 0.06 * CH:
            out.append(("BLOCK", f"caption overlaps object ({min(c1, oy1) - max(c0, oy0):.0f}px)"))
        gap = max(oy0 - c1, c0 - oy1)
        if gap > L["max_gap_frac"] * CH:
            out.append(("BLOCK", f"empty band {gap:.0f}px between caption and object (max {L['max_gap_frac'] * CH:.0f})"))
    return out


def check_plan(plan, spec=None, caps_scene=0):
    """-> list of (beat label, verdict, [reasons]). Verdict BLOCK > WARN > PASS."""
    spec = spec or load_spec()
    L = limits()
    sc = next(s for s in plan["scenes"] if s.get("template") == "potter")["props"]
    res = []
    for o in sc["objs"]:
        name = "soap" if o["obj"] == "soap_pink" else o["obj"]
        label = f"{o['obj']}@{o['t0']:.1f}s"
        sp = spec["objects"].get(name)
        if not sp:
            res.append((label, "BLOCK", ["no motion spec for this object (add it to config/motion-specs)"]))
            continue
        dur = o["t1"] - o["t0"]
        issues = []
        want = sp.get("tsx_sha")
        if want and TSX.exists() and tsx_sha(name) not in ("", want):
            issues.append(("BLOCK", "PotterObjects.tsx changed since the spec was verified (update spec, then --stamp)"))
        issues += contact_check(sp, dur, L) + move_check(sp, dur, L)
        fr, ext = frame_check(sp, o, L)
        issues += fr + layout_check(o, ext, sc["caps"], L)
        v = "BLOCK" if any(i[0] == "BLOCK" for i in issues) else "WARN" if issues else "PASS"
        res.append((label, v, [m for _, m in issues]))
    return res


def stamp(path=SPEC):
    d = load_spec(path)
    for n, sp in d["objects"].items():
        sp["tsx_sha"] = tsx_sha(n)
    Path(path).write_text(json.dumps(d, indent=1), encoding="utf-8")


def render(res):
    lines = [f"{v:5} {lab}" + ("  - " + "; ".join(r) if r else "") for lab, v, r in res]
    bad = sum(1 for _, v, _ in res if v == "BLOCK")
    lines.append(f"motion-check: {'BLOCK' if bad else 'PASS'} ({bad} of {len(res)} beats blocked)")
    return not bad, "\n".join(lines)


def gate(plan, log=print):
    """Render-time gate: plans without a potter scene pass; any BLOCK beat stops the render (raises)."""
    if not any(s.get("template") == "potter" for s in plan.get("scenes", [])):
        return True
    ok, text = render(check_plan(plan))
    log(text)
    if not ok:
        raise RuntimeError("motion-check BLOCK: fix the 3D objects, then re-run (see list above)")
    return True


def beat_times(plan, per=3):
    """Look-gate moments: `per` frames inside every 3D beat (25/55/85 % of the beat), so no beat is judged at one instant.
    Times are scene seconds; clipped to the plan's potter scene. Empty list = not a potter plan."""
    sc = next((s for s in plan.get("scenes", []) if s.get("template") == "potter"), None)
    if not sc:
        return []
    fr = [0.25, 0.55, 0.85][:per] if per <= 3 else [(i + 1) / (per + 1) for i in range(per)]
    return [round(o["t0"] + (o["t1"] - o["t0"]) * f, 2) for o in sc["props"]["objs"] for f in fr]


def chunk(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs), n)]
