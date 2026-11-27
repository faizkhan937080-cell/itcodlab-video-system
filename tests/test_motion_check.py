import copy
import json
import re
import pytest
from scripts import motion_check as M

SPEC = M.load_spec()
L = M.limits()


def plan(obj="globe", box=None, caps=None, t1=3.0):
    b = box or {"x": 0.5, "y": 0.62, "w": 1.0, "h": 0.52}
    return {"scenes": [{"template": "potter", "props": {"objs": [{"obj": obj, "t0": 0.0, "t1": t1, "box": b, "decor": "none"}],
                                                          "caps": caps or []}}]}


def test_gavel_swinging_through_the_plate_is_blocked():
    """Regression 2026-11-27: gavel swung THROUGH/UNDER the marble plate instead of tapping on top of it."""
    broken = json.loads((M.ROOT / "tests" / "fixtures_gavel_broken.json").read_text(encoding="utf-8"))
    issues = M.contact_check(broken, 2.6, L)
    assert issues and issues[0][0] == "BLOCK" and "sinks" in issues[0][1]


def test_fixed_gavel_in_the_real_spec_taps_and_stays_on_top():
    assert M.contact_check(SPEC["objects"]["gavel"], 2.6, L) == []


def test_gavel_that_taps_on_top_passes():
    g = copy.deepcopy(SPEC["objects"]["gavel"])
    g["pivot"]["vars"]["sw"] = "0.9*(sin(pi*c))**2"
    g["pivot"]["rot"] = "sw-0.12"            # lifts up, comes down and stops at contact on the pad
    g["pivot"]["dy"] = 0
    assert M.contact_check(g, 2.6, L) == []


def test_gavel_that_hovers_never_touching_is_blocked():
    g = copy.deepcopy(SPEC["objects"]["gavel"])
    g["pivot"]["rot"] = "0.5+0.3*sin(t*3)"
    g["pivot"]["dy"] = 0
    assert "never touches" in M.contact_check(g, 2.6, L)[0][1]


def test_object_must_move_and_settle():
    s = copy.deepcopy(SPEC["objects"]["globe"])
    s["signals"], s["pose"]["sway"], s["pose"]["spin"] = {}, 0.0, 0
    assert M.move_check(s, 3.0, L)[0][0] == "BLOCK"
    s["signals"] = {"x": ["t*0+1", False]}
    assert M.move_check(s, 3.0, L)[0][0] == "BLOCK"           # constant = no own motion
    s["signals"] = {"x": ["t", False]}
    assert any("not at rest" in m for _, m in M.move_check(s, 3.0, L))


def test_small_or_clipped_object_is_blocked():
    s = copy.deepcopy(SPEC["objects"]["gavel"])
    o = {"t0": 0, "t1": 3, "box": {"x": 0.5, "y": 0.62, "w": 1.0, "h": 0.52}}
    s["scale"] = 0.4
    assert any("too small" in m for _, m in M.frame_check(s, o, L)[0])
    s["scale"] = 1.0
    o["box"] = {"x": 0.5, "y": 0.62, "w": 1.0, "h": 0.12}
    assert any("clipped" in m for _, m in M.frame_check(s, o, L)[0])


def test_caption_overlap_and_empty_band():
    caps = [{"t0": 0, "t1": 3, "lines": [[{"w": "Hello", "st": "b", "at": 0}]], "y": 0.62}]
    out = M.layout_check({"t0": 0, "t1": 3}, (900, 1300, 0, 1080), caps, L)
    assert any("overlaps" in m for _, m in out)
    caps[0]["y"] = 0.05
    out = M.layout_check({"t0": 0, "t1": 3}, (1200, 1700, 0, 1080), caps, L)
    assert any("empty band" in m for _, m in out)


def test_unknown_object_and_changed_tsx_block(monkeypatch):
    assert M.check_plan(plan("nope"))[0][1] == "BLOCK"
    sp = copy.deepcopy(SPEC)
    sp["objects"]["globe"]["tsx_sha"] = "deadbeef0000"
    assert M.check_plan(plan("globe"), sp)[0][1] == "BLOCK"


def test_gate_stops_render_only_on_block():
    assert M.gate({"scenes": [{"template": "bars"}]}, lambda *_: None)
    bad = {"scenes": [{"template": "potter", "props": plan("gavel")["scenes"][0]["props"]}]}
    with pytest.raises(RuntimeError):
        M.gate(bad, lambda *_: None)


def test_look_gate_gives_three_moments_per_beat():
    p = plan("globe", t1=3.0)
    t = M.beat_times(p)
    assert len(t) == 3 and t == sorted(t) and 0 < t[0] < t[1] < t[2] < 3.0
    assert M.beat_times({"scenes": [{"template": "x"}]}) == []


def test_spec_mirrors_the_tsx_objects_and_poses():
    src = M.TSX.read_text(encoding="utf-8")
    names = re.search(r"export type ObjName = (.*?);", src).group(1)
    for n in re.findall(r"'(\w+)'", names):
        assert n in SPEC["objects"], f"no motion spec for {n}"
        m = re.search(r"\b%s: \{yaw: ([-\d.]+), sway: ([-\d.]+), spin: ([-\d.]+), tilt: ([-\d.]+), scale: ([-\d.]+)\}" % n, src)
        p = SPEC["objects"][n]["pose"]
        assert [p["yaw"], p["sway"], p["spin"], p["tilt"]] == [float(x) for x in m.groups()[:4]], n


def test_shipped_sample_plan_passes_the_gate():
    d = json.loads((M.ROOT / "trigger" / "sample" / "health-full-plan.json").read_text(encoding="utf-8"))
    ok, text = M.render(M.check_plan(d))
    assert ok, text
