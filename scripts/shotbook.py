"""Shot book = frame-by-frame (micro) description of EVERY shot, written by the Director after looking at the reference
collages, and the prompt writer that turns one shot into one prompt that fits the image model.
Two layers: `spec` (long, every detail, feeds Blender/Remotion and the Checker) and `prompt` (<= CLIP_MAX tokens,
most important details first). A shot book that is generic or repeats itself is blocked by `validate`."""
import re

from .stills_api import cut_report

REQUIRED = ("t0", "t1", "size", "subject", "detail", "material", "light", "lens", "camera", "fx", "colour", "caption", "cut_in", "voice")
VAGUE = {"nice", "beautiful", "cool", "amazing", "good", "stunning", "awesome", "interesting"}
MIN_DETAIL_WORDS = 6
MAX_SIMILAR = 0.6


def _words(s):
    return set(re.findall(r"[a-z]+", str(s).lower()))


def _similar(a, b):
    x, y = _words(a["subject"] + " " + a["detail"]), _words(b["subject"] + " " + b["detail"])
    return len(x & y) / max(1, len(x | y))


def validate(shots, target_s=None, cuts_per_min=None):
    """-> (ok, problems). Every shot fully described, no vague words, no two shots alike, timings add up."""
    bad = []
    for i, s in enumerate(shots):
        miss = [k for k in REQUIRED if s.get(k) in (None, "", [])]
        if miss:
            bad.append(f"shot {i + 1}: missing {','.join(miss)}")
            continue
        if len(str(s["detail"]).split()) < MIN_DETAIL_WORDS:
            bad.append(f"shot {i + 1}: detail too thin (<{MIN_DETAIL_WORDS} words)")
        v = _words(" ".join(str(s[k]) for k in ("subject", "detail", "material", "light"))) & VAGUE
        if v:
            bad.append(f"shot {i + 1}: vague words {sorted(v)}")
        if s["t1"] <= s["t0"]:
            bad.append(f"shot {i + 1}: t1 must be after t0")
    for i in range(len(shots)):
        for j in range(i + 1, len(shots)):
            if all(shots[k].get(r) for k in (i, j) for r in ("subject", "detail")) and _similar(shots[i], shots[j]) > MAX_SIMILAR:
                bad.append(f"shots {i + 1} and {j + 1} look the same (similarity above {MAX_SIMILAR})")
    if target_s and shots and abs(shots[-1]["t1"] - target_s) > target_s * 0.05:
        bad.append(f"shots end at {shots[-1]['t1']}s, video is {target_s}s")
    if cuts_per_min and shots:
        rate = (len(shots) - 1) / max(1e-6, shots[-1]["t1"] - shots[0]["t0"]) * 60
        if abs(rate - cuts_per_min) > cuts_per_min * 0.35:
            bad.append(f"cut rate {rate:.0f}/min, reference {cuts_per_min:.0f}/min")
    return (not bad), bad


def micro_prompt(card, shot):
    """One shot -> {prompt (<=75 tokens), negative, spec}. Order = importance: size+subject, detail, material, light, lens, fx, finish."""
    look = card["look"]
    parts = [f"{shot['size']} of {shot['subject']}", shot["detail"], shot["material"], shot["light"], shot["lens"],
             shot["fx"], look.get("finish", "")]
    keep = [p.strip(" ,") for p in parts if p and str(p).strip()]
    while cut_report(", ".join(keep))[1] and len(keep) > 2:
        keep.pop()
    prompt = ", ".join(keep)
    return {"prompt": prompt, "negative": ", ".join(look.get("never", [])), "tokens": cut_report(prompt)[0], "spec": dict(shot)}
