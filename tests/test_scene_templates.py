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
