import json
import subprocess
import sys
from pathlib import Path

from scripts.dna import validate

ROOT = Path(__file__).resolve().parent.parent


def test_make_plan_validates_and_has_two_scenes():
    out = subprocess.run([sys.executable, "-I", str(ROOT / "work/8bit-sciences/make_plan.py")], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-300:]
    plan = json.loads((ROOT / "trigger/sample/8bit-bruise-plan.json").read_text(encoding="utf-8"))
    assert validate("scene", plan) == []
    assert [s["template"] for s in plan["scenes"]] == ["eightbit", "eightbit"]
    assert abs(sum(s["duration_s"] for s in plan["scenes"]) - 25.0) < 0.01
    beats = plan["scenes"][0]["props"]["beats"]
    assert len(beats) == 14 and all(b["t"][0] < b["t"][1] for b in beats)


def test_no_still_zoom_in_pixel_parts():
    for f in ("PixelSkinSection", "PixelActors", "ScanlineGlitch", "DayCounter", "Callout", "PixelScene", "EightBitShots"):
        src = (ROOT / f"remotion/src/components/{f}.tsx").read_text(encoding="utf-8")
        assert "<Img" not in src and "staticFile" not in src, f
