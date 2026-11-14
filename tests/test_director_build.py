

def test_captions_follow_segment_times_even_with_split_words():
    from scripts import director_build as D
    tr = {"available": True, "segments": [
        {"id": "a", "start": 0.0, "end": 2.0, "text": "You're hot... sixty-five now"},
        {"id": "b", "start": 3.0, "end": 4.0, "text": "Next one"}]}
    tr["passes"] = {"auto": {"segments": tr["segments"]}}
    caps = D.captions_from(tr)
    assert caps[0]["start_s"] == 0.0 and caps[1]["start_s"] == 3.0
    assert caps[1]["words"][0]["text"] == "Next" and caps[1]["words"][0]["start_s"] == 3.0
