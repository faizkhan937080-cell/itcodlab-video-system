from scripts import sfx


def plan():
    return {"fps": 30, "scenes": [
        {"id": "a", "duration_s": 2, "template": "title"},
        {"id": "b", "duration_s": 3, "template": "checklist", "props": {"items": ["x", "y", "z"]}, "transition_in": {"type": "slide"}},
        {"id": "c", "duration_s": 2, "template": "counter", "transition_in": {"type": "cut"}},
    ]}


def test_cues_are_exact_and_sorted():
    cues = sfx.plan_cues(plan())
    kinds = [(round(c["t"], 2), c["kind"]) for c in cues]
    assert kinds[0] == (0.0, "hit")
    assert (1.88, "whoosh") in kinds                  # 2.0 s cut minus 0.12 s lead
    assert sum(1 for _, k in kinds if k == "tick") == 3
    assert (5.1, "pop") in kinds                      # scene c starts at 5.0 s, +3 frames
    assert [c["t"] for c in cues] == sorted(c["t"] for c in cues)


def test_pick_keeps_only_commercial_short_and_prefers_cc0():
    res = [{"license": "by-nc", "duration": 1000, "url": "u1"},
           {"license": "by", "duration": 900, "url": "u2", "title": "T", "creator": "C"},
           {"license": "cc0", "duration": 3000, "url": "u3"},
           {"license": "cc0", "duration": 9000, "url": "u4"},
           {"license": "by-sa", "duration": 500, "url": "u5"}]
    item, credit = sfx.pick(res)
    assert item["url"] == "u3" and credit is None
    item, credit = sfx.pick([res[1]])
    assert item["url"] == "u2" and "C" in credit       # CC BY keeps a credit line
    assert sfx.pick([res[0], res[4]]) == (None, None)


def test_audio_defs_skip_missing_kinds():
    cues = sfx.plan_cues(plan())
    out = sfx.audio_defs(cues, {"hit": "assets/sfx/hit.mp3"})
    assert len(out) == 1 and out[0]["at_s"] == 0.0 and out[0]["volume"] == sfx.SFX_VOLUME
