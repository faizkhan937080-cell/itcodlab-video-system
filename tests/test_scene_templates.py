import re
from pathlib import Path

from scripts.dna import load_schema, validate

ROOT = Path(__file__).resolve().parent.parent
NEW = ["counter", "bar_chart", "checklist", "split_compare", "quote"]


def _plan(template, props):
    return {"title": "t", "fps": 30, "orientation": "portrait",
            "scenes": [{"id": "s1", "duration_s": 3, "template": template, "props": props}]}


def test_new_templates_validate():
    samples = {
        "counter": {"value": 120, "suffix": "%", "label": "growth"},
        "bar_chart": {"title": "Views", "items": [{"label": "A", "value": 10}, {"label": "B", "value": 20}]},
        "checklist": {"title": "Steps", "items": ["one", "two"]},
        "split_compare": {"left": {"title": "Before", "points": ["x"]}, "right": {"title": "After", "points": ["y"]}},
        "quote": {"text": "Hello", "author": "Faiz"},
        "stroke": {"text": "Important", "shape": "circle", "color": "coral"},
        "paper_cutout": {"src": "assets/pagoda.png", "caption": "China", "rotate_deg": -3, "size": 0.7, "seed": 5},
    }
    for tpl, props in samples.items():
        assert validate("scene", _plan(tpl, props)) == [], tpl


def test_unknown_template_still_rejected():
    assert validate("scene", _plan("nope", {}))


def test_every_schema_template_is_handled_in_main_tsx():
    enum = load_schema("scene")["properties"]["scenes"]["items"]["properties"]["template"]["enum"]
    main = (ROOT / "remotion/src/Main.tsx").read_text(encoding="utf-8")
    types = (ROOT / "remotion/src/lib/types.ts").read_text(encoding="utf-8")
    for tpl in enum:
        assert f"case '{tpl}'" in main, f"Main.tsx has no case for {tpl}"
        assert f"'{tpl}'" in types, f"types.ts misses {tpl}"
    for tpl in NEW:
        assert tpl in enum


def test_captions_validate_and_bad_style_rejected():
    plan = _plan("title", {"text": "x"})
    plan["captions"] = [{"text": "hello big world", "start_s": 0, "end_s": 1.5},
                        {"text": "again", "start_s": 1.6, "end_s": 2.0,
                         "words": [{"text": "again", "start_s": 1.6, "end_s": 2.0}]}]
    plan["caption_style"] = {"position": "center", "max_words": 3, "highlight": "coral", "size": 1.2}
    assert validate("scene", plan) == []
    plan["caption_style"]["position"] = "left"
    assert validate("scene", plan)


def test_captions_wired_into_main():
    main = (ROOT / "remotion/src/Main.tsx").read_text(encoding="utf-8")
    assert "<Captions" in main and "plan.captions" in main


def test_step_fps_range():
    plan = _plan("stroke", {"text": "x"})
    plan["step_fps"] = 8
    assert validate("scene", plan) == []
    plan["step_fps"] = 2
    assert validate("scene", plan)


def test_texture_overlay_validates():
    plan = _plan("title", {"text": "x"})
    plan["texture"] = {"src": "assets/paper.jpg", "opacity": 0.4, "blend": "multiply"}
    assert validate("scene", plan) == []
    plan["texture"]["blend"] = "difference"
    assert validate("scene", plan)
    main = (ROOT / "remotion/src/Main.tsx").read_text(encoding="utf-8")
    assert "plan.texture" in main


def test_wipe_and_overlap_transition():
    plan = _plan("title", {"text": "x"})
    plan["scenes"].append({"id": "s2", "duration_s": 2, "template": "quote", "props": {"text": "y"},
                           "transition_in": {"type": "wipe", "duration_s": 0.5, "overlap": True}})
    assert validate("scene", plan) == []
    plan["scenes"][1]["transition_in"]["type"] = "spin"
    assert validate("scene", plan)
    assert "nx.overlap" in (ROOT / "remotion/src/Main.tsx").read_text(encoding="utf-8")
