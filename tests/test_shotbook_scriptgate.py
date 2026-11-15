import json
from pathlib import Path

from scripts import script_gate, shotbook

CARD = {"look": {"finish": "medical CGI, ultra detailed", "never": ["cartoon", "text"]}}


def shot(t0, t1, subject, detail, **kw):
    s = {"t0": t0, "t1": t1, "size": "extreme macro", "subject": subject, "detail": detail, "material": "wet glossy pink tissue",
         "light": "warm rim light from left", "lens": "100mm macro shallow depth", "camera": "slow push in", "fx": "thin smoke wisps",
         "colour": "pink red", "caption": "small cream low", "cut_in": "hard cut", "voice": "line"}
    s.update(kw)
    return s


def test_shotbook_blocks_thin_missing_and_duplicates():
    a = shot(0, 3, "nose lining", "tiny cilia hairs sway in a mucus film with capillaries")
    ok, bad = shotbook.validate([a])
    assert ok, bad
    assert not shotbook.validate([shot(0, 3, "x", "short")])[0]
    assert not shotbook.validate([{**a, "light": ""}])[0]
    b = shot(3, 6, "nose lining", "tiny cilia hairs sway in a mucus film with capillaries")
    assert any("look the same" in m for m in shotbook.validate([a, b])[1])
    assert any("vague" in m for m in shotbook.validate([shot(0, 3, "nice nose", "tiny cilia hairs sway in a mucus film")])[1])


def test_micro_prompt_fits_and_keeps_subject_first():
    p = shotbook.micro_prompt(CARD, shot(0, 3, "throat airway", "smoke drifting past ridged cartilage rings and glistening mucus"))
    assert p["prompt"].startswith("extreme macro of throat airway") and p["tokens"] <= 75 and "cartoon" in p["negative"]


REF = {"sentences": {"words_mean": 9.3}, "cta_words": []}
GOOD = ("Inside your nose every breath passes through a living filter. But one cigarette stops it for hours. "
        "Tiny hairs called cilia beat about twelve times each second. Smoke paralyses them, and then the dirt stays. "
        "Tea does something different to the same lining. Here is what happens next.")


def test_script_gate_good_and_bad():
    ok, bad = script_gate.check(GOOD, 20, REF)
    assert ok, bad
    ok, bad = script_gate.check("Welcome to this video about the human body and how it works in many different ways today. " * 3, 20, REF)
    assert not ok and any("hook" in m or "pace" in m for m in bad)


def test_script_gate_needs_sources_for_numbers():
    ok, bad = script_gate.check(GOOD, 20, REF, facts=[])
    assert not ok and any("research" in m for m in bad)
    ok, bad = script_gate.check(GOOD, 20, REF, facts=[{"number": "twelve", "source": "https://example.org/x"}])
    assert ok, bad
