import copy

from dna_fixtures import SCRIPT_METRICS, editing_dna, fit_editing, scripting_dna, sound_dna
from scripts.dna import validate
from scripts.dna_check import check
from scripts.dna_corpus import aggregate

SUMMARY = {"video": {"width": 1916, "height": 1078, "fps": 30.0, "duration_s": 58.3},
           "cut_rhythm": {"cuts_per_min": 15.44, "shot_length_s": {"mean": 3.644, "median": 3.667, "min": 1.2, "max": 7.6}},
           "audio": {"bpm": 103.4, "silence_share": 0.0, "cut_beat_sync": {"share_within_80ms": 0.733, "cuts_checked": 15},
                     "ebu_r128": {"integrated_lufs": -16.2, "true_peak_dbtp": -1.5}},
           "script_metrics": SCRIPT_METRICS}


def test_valid_candidates_pass_with_matching_numbers():
    assert check("editing", editing_dna("j"), SUMMARY) == []
    assert check("scripting", scripting_dna("j"), SUMMARY) == []
    assert check("sound", sound_dna("j"), SUMMARY) == []


def test_wrong_measured_number_is_caught():
    d = editing_dna("j")
    d["cut_rhythm"]["cuts_per_min"] = 30
    assert any("cuts_per_min" in p for p in check("editing", d, SUMMARY))
    s = sound_dna("j")
    s["loudness"]["integrated_lufs"] = -9
    assert any("integrated_lufs" in p for p in check("sound", s, SUMMARY))


def test_missing_confidence_for_a_section_is_caught():
    d = editing_dna("j")
    del d["confidence"]["color"]
    assert any("confidence missing for section 'color'" in p for p in check("editing", d, SUMMARY))


def test_incomplete_transcript_cannot_claim_judged_structure():
    sm = dict(SCRIPT_METRICS, coverage_ratio=0.14, complete=False)
    summ = dict(SUMMARY, script_metrics=sm)
    d = scripting_dna("j", coverage=0.14, complete=False)          # structure tagged judged -> refused
    probs = check("scripting", d, summ)
    assert any("incomplete transcript" in p for p in probs)
    ok = scripting_dna("j", coverage=0.14, complete=False, structure_tag="estimated")
    assert check("scripting", ok, summ) == []
    liar = scripting_dna("j", coverage=1.0, complete=True)          # claims complete but pack says 0.14
    assert any("transcript_basis" in p for p in check("scripting", liar, summ))


def test_no_transcript_means_no_scripting_dna():
    summ = dict(SUMMARY, script_metrics={"available": False})
    assert any("no script_metrics" in p for p in check("scripting", scripting_dna("j"), summ))


def test_v1_style_candidate_is_rejected_by_schema():
    old = {"type": "sound", "source": {"job_id": "j"}, "bpm": 120, "beat_sync": {"share_within_80ms": 0.6},
           "loudness_db": {"mean": -18}, "confidence": {"bpm": "measured"}}
    assert validate("sound", old) != []


def test_corpus_separates_signature_from_situational():
    dnas = []
    for i in range(12):
        d = scripting_dna(f"v{i}")
        d["pacing"]["words_per_min_speaking"] = 180 + (i % 3)          # stable
        d["cta"]["placement_s"] = 10.0 * (i + 1)                      # all over the place
        d["voice"]["register"] = "casual" if i < 10 else "formal"     # mostly casual
        d["lexicon"]["signature_phrases"] = ["edit with claude"] + (["dosto"] if i % 2 == 0 else [])
        dnas.append(d)
    c = aggregate("scripting", "creator1", dnas)
    assert validate("corpus", c) == []
    assert c["n_videos"] == 12 and c["provisional"] is False
    assert "pacing.words_per_min_speaking" in c["signature"]
    assert "cta.placement_s" in c["situational"]
    assert c["targets"]["voice.register"] == "casual"
    assert "edit with claude" in c["targets"]["lexicon.signature_phrases"]
    assert "dosto" in c["targets"]["lexicon.signature_phrases"]     # present in exactly 50% -> kept
    assert c["fields"]["pacing.words_per_min_speaking"]["median"] == 181.0


def test_corpus_small_sample_is_provisional_and_named_beats_flatten():
    c = aggregate("editing", "c", [fit_editing(editing_dna(f"v{i}"), SUMMARY) for i in range(3)])
    assert c["provisional"] is True
    assert "cut_rhythm.pace_curve[opening].cuts_per_min" in c["fields"]
    assert "color.palette[#0A070B].share" in c["fields"]
    assert copy.deepcopy(c)["creator"] == "c"


def test_clone_report_tolerates_small_drift_and_flags_big_and_size():
    from scripts.dna_check import clone_report
    dna = fit_editing(editing_dna("j"), SUMMARY)
    near = {"video": {"width": 1916, "height": 1078, "fps": 30.0, "duration_s": 58.3},
            "cut_rhythm": {"cuts_per_min": 16.5, "shot_length_s": {"mean": 3.5, "median": 3.7, "min": 1.2, "max": 7.6}}}
    assert clone_report("editing", dna, near)["pass"] is True
    small = dict(near, video={"width": 1280, "height": 720, "fps": 30.0, "duration_s": 58.3})
    r = clone_report("editing", dna, small)
    assert not r["pass"] and any("format.width" in d for d in r["differences"])
    fast = dict(near, cut_rhythm={"cuts_per_min": 30, "shot_length_s": near["cut_rhythm"]["shot_length_s"]})
    assert not clone_report("editing", dna, fast)["pass"]


def test_clone_report_accepts_corpus_targets():
    from scripts.dna_check import clone_report
    c = aggregate("editing", "c", [fit_editing(editing_dna(f"v{i}"), SUMMARY) for i in range(4)])
    out = {"cut_rhythm": {"cuts_per_min": 15.4, "shot_length_s": {"mean": 3.6, "median": 3.7, "min": 1.2, "max": 7.6}}}
    assert clone_report("editing", c, out)["pass"] is True


def test_dna_draft_prefills_measured_parts_that_pass_the_gate_once_completed():
    from scripts.dna_draft import DRAFTERS
    sm = dict(SUMMARY)
    sm["cut_rhythm"] = {"cuts_per_min": 15.44, "scene_count": 16, "transitions": {"hard_cut": 15},
                        "shot_length_s": {"mean": 3.644, "median": 3.667, "std": 1.465, "min": 1.2, "max": 7.6}}
    sm["saturation"], sm["brightness"] = {"mean": 0.227}, {"mean": 0.438}
    sm["palette"] = [{"hex": "#0A070B", "share": 0.07}, {"hex": "#110E12", "share": 0.05}, {"hex": "#32343A", "share": 0.04}]
    sm["scenes"] = [{"id": i, "t": [i * 3.6, i * 3.6 + 3.6]} for i in range(16)]
    sm["script_metrics"] = {"available": True, "coverage_ratio": 1.0, "complete": True, "words_per_min_speaking": 190.0,
                            "words_per_min_overall": 171.0, "speech_ratio": 0.9, "sentences": {"words_mean": 7.0, "words_p90": 12},
                            "pauses": {"mean_s": 0.4}, "questions_per_min": 1.0, "numbers_per_min": 0.5,
                            "hook": {"first_12_words": "ab aap bhi", "first_word_s": 0.2}, "vocabulary_note": "roman",
                            "repeated_phrases": [{"phrase": "edit with claude", "count": 3}]}
    e = DRAFTERS["editing"](sm, "j", creator="c")
    assert e["format"]["orientation"] == "landscape" and len(e["cut_rhythm"]["pace_curve"]) == 3
    assert e["transitions"] == [{"type": "hard_cut", "share": 1.0}]
    full = editing_dna("j")                       # Claude completes the judged sections
    for k in ("shots", "motion", "text", "layout", "recipe", "evidence"):
        e[k] = full[k]
    e["color"]["grade"].update(look="dark", contrast="medium", temperature="cool")
    e["cut_rhythm"]["pattern"] = "steady"
    e["confidence"].update(full["confidence"])
    assert check("editing", e, sm) == []
    sc = DRAFTERS["scripting"](sm, "j")
    assert sc["pacing"]["words_per_min_speaking"] == 190.0 and sc["transcript_basis"]["complete"] is True
    assert DRAFTERS["sound"](sm, "j")["loudness"]["integrated_lufs"] == -16.2
    import pytest
    with pytest.raises(ValueError):
        DRAFTERS["scripting"]({"script_metrics": {"available": False}}, "j")
