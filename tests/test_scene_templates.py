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
        "lottie": {"src": "library/motion/arrow.json", "size": 0.5, "loop": True},
        "audio_bars": {"src": "assets/music.mp3", "bars": 24, "color": "coral"},
        "meme_text": {"text": "bro what", "position": "bottom"},
        "sticker": {"text": "😂", "x": 0.8, "y": 0.2, "size": 0.25},
        "nt_bg": {"mode": "split"},
        "nt_card": {"layout": "split", "kicker": "Step 1", "title": "x", "rows": [{"text": "a", "icon": "check", "at_s": 1}]},
        "video": {"src": "a.mp4", "layout": [{"from_s": 0, "scale": 0.8, "offset_y": 0.15, "clip_top": 0.5}, {"from_s": 4, "hidden": True}]},
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


def test_scene_fx_validate_and_bad_rejected():
    plan = _plan("title", {"text": "x"})
    plan["scenes"][0]["fx"] = [{"type": "shake", "start_s": 0.5}, {"type": "rgb_split", "start_s": 1, "dur_s": 0.3, "strength": 1.5}]
    assert validate("scene", plan) == []
    plan["scenes"][0]["fx"] = [{"type": "explode", "start_s": 0}]
    assert validate("scene", plan)


def test_sfx_cues_add_meme_fx_idempotent_and_valid():
    from scripts import sfx
    plan = {"title": "t", "fps": 30, "orientation": "portrait", "scenes": [
        {"id": "a", "duration_s": 2, "template": "title", "props": {"text": "x"}},
        {"id": "b", "duration_s": 2, "template": "quote", "props": {"text": "y"}, "transition_in": {"type": "zoom"},
         "fx": [{"type": "glitch", "start_s": 1.0}]}]}
    cues = sfx.plan_cues(plan)
    n1 = sfx.fx_for_cues(plan, cues)
    first = [dict(f) for sc in plan["scenes"] for f in sc.get("fx", [])]
    n2 = sfx.fx_for_cues(plan, cues)
    assert n1 == n2 and n1 >= 4
    assert first == [f for sc in plan["scenes"] for f in sc.get("fx", [])]
    assert any(f["type"] == "glitch" and not f.get("auto") for f in plan["scenes"][1]["fx"])
    assert any(f["type"] == "rgb_split" and f["start_s"] == 0.0 for f in plan["scenes"][1]["fx"])
    assert validate("scene", plan) == []


def test_nt_caption_look_validates():
    plan = _plan("title", {"text": "x"})
    plan["caption_style"] = {"look": "nt", "max_words": 2, "y": 0.55, "y_by_time": [{"from_s": 0, "y": 0.12}, {"from_s": 4.5, "y": 0.545}]}
    assert validate("scene", plan) == []
