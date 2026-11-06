"""Instagram Reels safe zones (9:16). Numbers: config/limits.json -> safezone (strict = Meta guidance 14% top / 35% bottom / 6% sides;
hard = never put text there). The same numbers are in remotion/src/lib/safe.ts (a test keeps them equal).
lint(plan, size) -> findings [{level: 'hard'|'soft', where, msg}] about things the plan controls (captions, overlay boxes)."""
import math

from .common import limits


def is_portrait(w, h):
    return h / float(w) >= 1.5


def insets(w, h, lim=None, kind="strict"):
    """Margins in px {top, bottom, left, right}. Landscape / square: a plain title-safe margin."""
    z = (lim or limits())["safezone"]
    if not is_portrait(w, h):
        m = z["landscape_margin"]
        return {"top": h * m, "bottom": h * m, "left": w * m, "right": w * m}
    if kind == "hard":
        k = z["hard"]
        return {"top": h * k["top"], "bottom": h * k["bottom"], "left": w * k["left"], "right": w * k["right"]}
    k = z["strict"]
    return {"top": h * k["top"], "bottom": h * k["bottom"], "left": w * k["side"], "right": w * k["side"]}


def caption_findings(plan, w, h, lim=None):
    caps = plan.get("captions") or []
    if not caps:
        return []
    st = plan.get("caption_style") or {}
    unit = min(w, h) / 1080.0
    fs = 72 * float(st.get("size", 1.0)) * unit
    per = max(1, int(st.get("max_words", 4)))
    ins = insets(w, h, lim)
    avail_w = w - ins["left"] - ins["right"] - 120 * unit
    avail_h = h - ins["top"] - ins["bottom"]
    worst = 0
    for c in caps:
        words = c["text"].split()
        for i in range(0, len(words), per):
            chars = len(" ".join(words[i:i + per])) + 1
            worst = max(worst, math.ceil(chars * 0.56 * fs / max(avail_w, 1)))
    out = []
    if worst * fs * 1.15 > avail_h * 0.5:
        out.append({"level": "soft", "where": "captions", "msg": f"a caption page can take {worst} lines at this size; lower caption_style.size or max_words"})
    return out


def overlay_findings(plan, w, h, lim=None):
    """Overlays with a fixed box {x, y, w, h} (fractions) are checked against the zones; tracked ones follow the subject (not checked)."""
    out = []
    hard = insets(w, h, lim, "hard")
    for sc in plan.get("scenes", []):
        for i, ov in enumerate(sc.get("overlays") or []):
            b = ov.get("box")
            if not b or ov.get("follow"):
                continue
            x0, y0, x1, y1 = b["x"] * w, b["y"] * h, (b["x"] + b["w"]) * w, (b["y"] + b["h"]) * h
            if y0 < hard["top"] or y1 > h - hard["bottom"] or x0 < hard["left"] or x1 > w - hard["right"]:
                out.append({"level": "hard", "where": f"{sc['id']}.overlays[{i}]", "msg": "box overlaps the Instagram UI zone"})
    return out


def lint(plan, size, lim=None):
    w, h = size
    return caption_findings(plan, w, h, lim) + overlay_findings(plan, w, h, lim)
