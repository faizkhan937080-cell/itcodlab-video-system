import json

import numpy as np
import pytest

from scripts import anchors, beats, director, gates, notes, protocol, ref_measure

TR = {"available": True, "segments": [
    {"start": 0.0, "end": 3.0, "text": "This ship has been at war for 260 years"},
    {"start": 3.0, "end": 6.0, "text": "and she is still in commission"},
    {"start": 6.0, "end": 9.0, "words": [{"word": "Meet", "start": 6.0, "end": 6.4}, {"word": "Victory", "start": 6.5, "end": 7.2}],
     "text": "Meet Victory"}]}


def words():
    return anchors.words_from_transcript(TR)


def doc(**kw):
    d = {"id": "b1", "duration_s": 9.0, "beats": [
        {"id": "a", "anchor": {"phrase": "at war"}, "hold_s": 2.0, "zone": "left", "component": "title", "text": "At war"},
        {"id": "b", "anchor": {"phrase": "still in commission"}, "hold_s": 2.0, "zone": "bottom", "component": "banner", "text": "Still serving"}]}
    d.update(kw)
    return d


def test_phrase_time_uses_word_times_when_present_else_spread():
    w = words()
    assert anchors.find_phrase(w, "meet victory")["t"] == 6.0 and anchors.find_phrase(w, "meet victory")["exact"]
    hit = anchors.find_phrase(w, "at war")
    assert 0.9 < hit["t"] < 1.6 and hit["exact"] is False
    assert anchors.find_phrase(w, "not spoken anywhere") is None


def test_beats_valid_and_table():
    assert beats.validate(doc(), words()) == []
    assert "at war" in beats.table(doc(), words())


@pytest.mark.parametrize("mut,msg", [
    (lambda d: d["beats"][0]["anchor"].update(phrase="never said"), "anchor phrase not found"),
    (lambda d: d["beats"][0].update(hold_s=0.2), "too short"),
    (lambda d: d["beats"][0].update(text="one two three four five six seven eight", hold_s=1.0), "to read"),
    (lambda d: d["beats"][1].update(zone="left", anchor={"phrase": "at war"}), "overlap"),
    (lambda d: d["beats"][0].update(zone="middle"), "zone must be"),
    (lambda d: d["beats"][0].update(anchor={"t": 5.0}), "hook"),
])
def test_beats_problems_are_reported(mut, msg):
    d = doc()
    mut(d)
    if "hook" in msg:
        d["beats"] = d["beats"][:1]
    assert any(msg in e for e in beats.validate(d, words())), beats.validate(d, words())


def test_approval_breaks_when_beats_change():
    d = beats.approve(doc())
    assert beats.is_approved(d)
    d["beats"][0]["hold_s"] = 3.0
    assert not beats.is_approved(d)


class Store:
    def __init__(self, files):
        self.f = files

    def read_json(self, rel):
        return self.f[rel]


def plan(**kw):
    p = {"title": "t", "fps": 30, "orientation": "portrait",
         "scenes": [{"id": "s1", "duration_s": 3.0, "template": "title", "props": {"title": "At war", "fontSize": 120}}]}
    p.update(kw)
    return p


def test_director_plan_needs_approved_beats_and_passing_gates():
    base = protocol.stamp(plan(), "sample", "none", "no reference for this test", director="b1", beats_file="jobs/beats/b1.json")
    ok = beats.approve(doc())
    errs = protocol.check_plan(base, Store({"jobs/beats/b1.json": ok}))
    assert not any("beats" in e for e in errs), errs
    bad = dict(ok, beats=ok["beats"][:1])    # changed after the Y
    assert any("not approved" in e for e in protocol.check_plan(base, Store({"jobs/beats/b1.json": bad})))
    assert any("beats_file" in e for e in protocol.check_plan(base, Store({})))


def test_gates_block_unreadable_and_flashing_plans():
    p = plan()
    p["scenes"][0]["props"].update(title="one two three four five six seven eight nine ten", fontSize=40)
    v = gates.verdict(gates.plan_gates(p))
    assert v["verdict"] == "BLOCK" and v["fails"] >= 2
    flash = plan(scenes=[{"id": f"f{i}", "duration_s": 0.2, "template": "title", "props": {"title": "x", "fontSize": 120}} for i in range(5)])
    assert any(x["code"] == "flash" for x in gates.flash_check(flash))
    assert gates.verdict(gates.plan_gates(plan()))["verdict"] == "DELIVER"


def test_director_asks_only_what_is_missing_and_never_guesses():
    c = director.brief_card("", None)
    assert any("topic" in q for q in director.missing(c)) and any("reference" in q.lower() for q in director.missing(c))
    c = director.brief_card("HMS Victory", "ref1", keep=["motion", "voice"])
    prof = director.build_profile("ref1", style={"easing": "slow-in-out"}, motion30={"camera": {"moving_pct": 65}})
    out = director.plan_brief(c, prof)
    assert out["ask"] == [] and "motion30" in out["frozen"] and out["not_measured"] == ["voice"]
    assert director.plan_brief(c, None)["need"] == "profile"
    with pytest.raises(ValueError):
        director.missing(director.brief_card("x", "r", keep=["vibes"]))


def test_repeated_review_notes_become_one_rule(tmp_path):
    f = tmp_path / "n.jsonl"
    for t, x in [(3, "label covers his face"), (9, "the label is covering the face again"), (20, "music too loud at start")]:
        notes.add("job1", x, t, path=f)
    g = notes.digest(path=f)
    assert len(g) == 1 and g[0]["count"] == 2
    assert "M:" in notes.lesson_line(g[0]) and notes.lesson_line(g[0]).count("|") == 2


def test_ref_measure_sees_a_slow_push_that_a_still_check_misses(tmp_path):
    import cv2
    path = tmp_path / "m.mp4"
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (160, 90))
    rng = np.random.default_rng(1)
    base = (rng.random((90, 400, 3)) * 255).astype("uint8")
    for i in range(90):
        M = np.float32([[1, 0, -i * 0.4], [0, 1, 0]])      # 0.4 px per frame sideways, sub-pixel = a slow glide
        vw.write(cv2.warpAffine(base, M, (400, 90))[:, 100:260])
    vw.release()
    m = ref_measure.measure(path)
    assert m["camera"]["moving_pct"] > 50 and m["hard_cuts"] == [] and m["per_second"]
