"""Director (point 1). Faiz gives a small clue; the Director turns it into a brief card, loads the saved Tone/Style Profile of the
reference and freezes what must stay the same ("same tone and motion, new topic"). It asks Faiz only what is truly missing.
Profile = numbers from the reference, built once from the measured records (style_record, script_metrics, voice, motion30)
and saved to Drive `profiles/<ref_id>.json`, so a new topic never re-reads or re-measures the reference (token saving)."""
import json

from .common import now_iso

KEEP = {"tone", "motion", "voice", "script_formula", "colour", "sound"}
DEFAULT = {"length_s": 30, "language": "hinglish", "format": "reel 9:16", "keep": ["tone", "motion"]}
QUESTIONS = {   # asked in chat, short Hinglish, only when the field is really missing
    "topic": "Video kis topic par banani hai? (ek line)",
    "reference": "Kaun si reference video/reel ka style lena hai? (link)",
}
PROFILE_PARTS = ("style", "script", "voice", "motion30", "sound")


def brief_card(topic, reference=None, keep=None, change=("topic",), **extra):
    card = {**DEFAULT, **extra, "topic": (topic or "").strip(), "reference": reference,
            "keep": sorted(set(keep) if keep else set(DEFAULT["keep"])), "change": list(change), "created": now_iso()}
    return card


def missing(card):
    """-> list of short chat questions (empty = Director can go on without asking Faiz)."""
    out = []
    if not card.get("topic"):
        out.append(QUESTIONS["topic"])
    bad = [k for k in card.get("keep", []) if k not in KEEP]
    if bad:
        raise ValueError(f"unknown keep: {bad}; allowed {sorted(KEEP)}")
    if card.get("keep") and not card.get("reference"):
        out.append(QUESTIONS["reference"])
    return out


def build_profile(ref_id, style=None, script=None, voice=None, motion30=None, sound=None):
    """Compact profile. Only measured parts go in; a missing part is listed so the Director knows what is NOT frozen."""
    parts = {"style": style, "script": script, "voice": voice, "motion30": motion30, "sound": sound}
    prof = {"ref": ref_id, "built": now_iso(), "parts": {k: v for k, v in parts.items() if v},
            "missing": [k for k, v in parts.items() if not v]}
    return prof


def save_profile(storage, prof):
    storage.put_json(f"profiles/{prof['ref']}.json", prof, versioned=False)


def load_profile(storage, ref_id):
    try:
        return storage.read_json(f"profiles/{ref_id}.json")
    except Exception:  # noqa: BLE001
        return None


PART_OF = {"tone": ("voice", "script"), "motion": ("motion30", "style"), "voice": ("voice",), "script_formula": ("script",),
           "colour": ("style", "motion30"), "sound": ("sound",)}


def freeze(card, profile):
    """What stays identical for the new topic. -> {"frozen": {part: data}, "not_measured": [...], "free": card['change']}.
    A kept aspect whose part was never measured is reported, never guessed."""
    frozen, gap = {}, []
    for k in card.get("keep", []):
        for part in PART_OF[k]:
            if profile and profile["parts"].get(part):
                frozen[part] = profile["parts"][part]
            elif part not in gap:
                gap.append(part)
    return {"frozen": frozen, "not_measured": gap, "free": card.get("change", ["topic"]), "ref": (profile or {}).get("ref")}


def plan_brief(card, profile):
    """One call for the Director: questions to ask OR the frozen set to build from."""
    q = missing(card)
    if q:
        return {"ask": q}
    if card.get("reference") and not profile:
        return {"ask": [], "need": "profile", "note": f"analyse reference {card['reference']} first (style record, 30 fps measure), then build the profile"}
    return {"ask": [], **freeze(card, profile)}


def dumps(x):
    return json.dumps(x, ensure_ascii=False, indent=1)
