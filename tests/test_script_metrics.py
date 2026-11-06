from scripts import script_metrics as sm


def tr(segs, cov=1.0, alt=None):
    t = {"available": True, "segments": segs, "text": " ".join(s["text"] for s in segs), "coverage_ratio": cov}
    if alt:
        t["alt_english"] = alt
    return t


def test_wpm_pauses_sentences_and_hook():
    segs = [{"start": 0.5, "end": 3.5, "text": "Aap bhi yeh bana sakte ho. Kya baat hai?"},
            {"start": 4.5, "end": 6.5, "text": "Comment karo aur follow karo 3 steps"}]
    m = sm.compute(tr(segs), 10.0)
    assert m["available"] and m["complete"]
    assert m["words"] == 16
    assert m["words_per_min_speaking"] == round(16 / (5 / 60), 1)
    assert m["words_per_min_overall"] == 96.0
    assert m["pauses"]["count_gt_0_5s"] == 1 and m["pauses"]["max_s"] == 1.0
    assert m["questions_per_min"] == 6.0
    assert m["hook"]["first_word_s"] == 0.5
    assert m["hook"]["words_in_first_3s"] == 7.5      # 9 words in 3 s segment, 2.5 s of it before 3.0
    assert "comment" in m["cta_words"] and "follow" in m["cta_words"]
    assert m["numbers_per_min"] == 6.0
    assert m["script_mix"]["latin_share"] == 1.0


def test_incomplete_transcript_is_flagged_and_devanagari_is_phonetic():
    segs = [{"start": 0, "end": 4, "text": "अब आप भी इस तरह की एनिमेशन बना सकते हो"}]
    m = sm.compute(tr(segs, cov=0.14), 58.3)
    assert m["complete"] is False and m["coverage_ratio"] == 0.14
    assert m["vocabulary_note"] == "phonetic"
    assert m["second_person_per_100w"] > 0


def test_unavailable_transcript():
    assert sm.compute({"available": False}, 10) == {"available": False}
    assert sm.compute(None, 10) == {"available": False}


def test_repeated_phrases_found():
    segs = [{"start": 0, "end": 5, "text": "edit with claude today. edit with claude again"}]
    m = sm.compute(tr(segs), 5)
    assert any(p["phrase"] == "edit with claude" and p["count"] == 2 for p in m["repeated_phrases"])


def test_repeated_lines_counted_once_with_count():
    segs = [{"start": 0, "end": 2, "text": "Comment karo"}, {"start": 2, "end": 4, "text": "Seedha kaam ki baat"},
            {"start": 4, "end": 6, "text": "comment  karo!"}]
    u = sm.dedup_sentences([s["text"] for s in segs])
    assert [x["count"] for x in u] == [2, 1] and u[0]["text"] == "Comment karo"
    m = sm.compute(tr(segs), 6)
    assert m["repeated_sentences"][0]["count"] == 2 and m["unique_sentence_share"] == round(2 / 3, 3)
    from scripts.pack import _unique_text
    assert _unique_text(segs) == "Comment karo (x2) | Seedha kaam ki baat"


def test_collapse_loops_keeps_real_repeats_and_flags_whisper_loops():
    clean, gone, loop = sm.collapse_loops("करेट करेट करेट करेट करेट करेट करेट करेट")
    assert clean == "करेट" and gone == 7 and loop
    clean, gone, loop = sm.collapse_loops("so so good and so on, go go go")  # 3x is natural speech, kept
    assert gone == 0 and not loop and clean.startswith("so so good")
    clean, gone, loop = sm.collapse_loops("hello world ok ok ok ok ok ok bye")
    assert clean == "hello world ok bye" and gone == 5 and not loop
    clean, gone, loop = sm.collapse_loops("a b a b a b a b a b end")  # two-word unit loop
    assert clean == "a b end" and gone == 8
    assert sm.collapse_loops("") == ("", 0, False)


def test_loop_segments_are_left_out_of_metrics():
    segs = [{"start": 0.0, "end": 5.0, "text": "hello there my friend how are you"},
            {"start": 5.0, "end": 9.0, "text": "करेट", "loop": True}]
    m = sm.compute(tr(segs), 9.0)
    assert m["words"] == 7
