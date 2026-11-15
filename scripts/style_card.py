"""Style card = the STYLE of a reference as rules (not a copy of the reference), and the prompt writer that uses it.
Any new topic is built from the card; the reference itself is not needed. A card has measured parts (from the profile)
and `look` words the Director writes after looking at the collages."""
import json
import re
from pathlib import Path

from .stills_api import CLIP_MAX, cut_report


def from_profile(profile, look, captions, name):
    st, sc, vo, so = (profile["parts"].get(k, {}) for k in ("style", "script", "voice", "sound"))
    return {
        "name": name, "from_ref": profile.get("ref"),
        "look": look,   # {"subject_rules": [...], "materials": [...], "light": ..., "camera": ..., "smoke_or_fx": ..., "never": [...]}
        "palette": [p["hex"] for p in st.get("palette", [])[:6]],
        "brightness_mean": (st.get("brightness") or {}).get("mean"),
        "cut_rhythm": {"cuts_per_min": (st.get("cut_rhythm") or {}).get("cuts_per_min"), "transitions": (st.get("cut_rhythm") or {}).get("transitions")},
        "motion": st.get("motion_classes"),
        "captions": captions,
        "script": {"wpm_speaking": sc.get("words_per_min_speaking"), "person": "second", "questions": sc.get("questions_per_min", 0) > 0, "cta": bool(sc.get("cta_words"))},
        "voice": {"wpm_target": min(165, int(sc.get("words_per_min_speaking") or 150)), "expressiveness": (vo.get("global") or {}).get("expressiveness")},
        "sound": {"bpm": so.get("bpm"), "lufs": (so.get("ebu_r128") or {}).get("integrated_lufs"), "voice_over_music_lu": (so.get("stems") or {}).get("voice_minus_music_lu")},
    }


def shot_prompt(card, subject, action="", camera=None):
    """One image prompt that fits the model (<= CLIP_MAX tokens): subject FIRST, then the card's look in priority order.
    Returns {"prompt", "negative", "sheet"}; `sheet` is the long human-readable detail sheet for the scene list."""
    look = card["look"]
    parts = [subject]
    if action:
        parts.append(action)
    parts += [look.get("materials", [""])[0] if look.get("materials") else "", look.get("light", ""), camera or look.get("camera", ""), look.get("finish", "")]
    keep = [p.strip(" ,") for p in parts if p and p.strip()]
    prompt = ", ".join(keep)
    while cut_report(prompt)[1] and len(keep) > 2:   # drop the least important style piece until it fits
        keep.pop()
        prompt = ", ".join(keep)
    sheet = {"subject": subject, "action": action, "materials": look.get("materials"), "light": look.get("light"),
             "camera": camera or look.get("camera"), "fx": look.get("smoke_or_fx"), "palette": card["palette"], "never": look.get("never")}
    return {"prompt": prompt, "negative": ", ".join(look.get("never", [])), "sheet": sheet, "tokens": cut_report(prompt)[0]}


def save(card, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(card, indent=1, ensure_ascii=False), encoding="utf-8")
    return path
