"""Final gates (point 5): what a video must pass BEFORE it reaches Faiz (rulebooks/16, video-director ideas).
Plan-level checks run before the build and again on the final plan; file-level checks stay in scripts/qa.py (loudness, dead air,
black/frozen frames, safe zone). `verdict` = DELIVER or BLOCK. A BLOCK is never sent to Faiz; the hints say what to change."""
from . import qa
from .common import limits

DEFAULT = {"min_font_frac": 0.045, "read_words_per_s": 3.0, "flash_max_per_s": 3, "flash_scene_s": 0.34, "warn_block": 4}
TEXT_KEYS = ("text", "title", "headline", "line", "quote", "label", "subtitle")


def _lim():
    return {**DEFAULT, **(limits().get("gates") or {})}


def scene_texts(sc):
    props = sc.get("props") or {}
    out = [str(props[k]) for k in TEXT_KEYS if props.get(k)]
    for k in ("lines", "items"):
        out += [str(x if not isinstance(x, dict) else x.get("text", "")) for x in props.get(k) or []]
    return [t for t in out if t.strip()]


def text_checks(plan):
    """Readable on a phone: font size (when the plan states it) and read time per scene."""
    lim, out = _lim(), []
    h = 1920 if plan.get("orientation") == "portrait" else 1080
    for sc in plan.get("scenes", []):
        texts = scene_texts(sc)
        if not texts:
            continue
        words = sum(len(t.split()) for t in texts)
        need = words / lim["read_words_per_s"]
        if sc["duration_s"] + 1e-9 < need:
            out.append(qa.f("fail", "read_time", f"scene {sc['id']}: {words} words need {need:.1f}s to read, scene lasts {sc['duration_s']}s"))
        fs = (sc.get("props") or {}).get("fontSize") or (sc.get("props") or {}).get("font_size")
        if fs is None:
            out.append(qa.f("info", "font_size", f"scene {sc['id']}: no fontSize in the plan; the frame check measures the real size"))
        elif float(fs) / h < lim["min_font_frac"]:
            out.append(qa.f("fail", "font_size", f"scene {sc['id']}: font {fs}px is under {lim['min_font_frac']:.1%} of the height; too small for a phone"))
    return out


def flash_check(plan):
    """Many very short scenes in one second = flashing (photosensitive viewers, and it looks cheap)."""
    lim, out, t, starts = _lim(), [], 0.0, []
    for sc in plan.get("scenes", []):
        if sc["duration_s"] < lim["flash_scene_s"]:
            starts.append(t)
        t += sc["duration_s"]
    for i, a in enumerate(starts):
        n = sum(1 for b in starts if a <= b < a + 1.0)
        if n > lim["flash_max_per_s"]:
            out.append(qa.f("fail", "flash", f"{n} scenes shorter than {lim['flash_scene_s']}s inside one second near {a:.1f}s"))
            break
    return out


def plan_gates(plan):
    base, _ = qa.plan_checks(plan)
    return base + text_checks(plan) + flash_check(plan)


def verdict(findings):
    """DELIVER only with no fail and fewer than warn_block warnings. Info never blocks."""
    lim = _lim()
    fails = [x for x in findings if x.get("level") == "fail"]
    warns = [x for x in findings if x.get("level") == "warn"]
    block = bool(fails) or len(warns) >= lim["warn_block"]
    why = [x.get("msg") for x in fails + warns][:6]
    return {"verdict": "BLOCK" if block else "DELIVER", "fails": len(fails), "warns": len(warns), "why": why}
