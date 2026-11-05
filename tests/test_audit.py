from scripts import audit


def scenes(spec):
    out = []
    for i, (a, b, txt) in enumerate(spec, 1):
        out.append({"id": i, "start_s": a, "end_s": b, "duration_s": round(b - a, 3), "keyframe": f"k{i}.jpg",
                    "text": txt, "motion": {"class": "static"}})
    return out


INFO = {"duration_s": 120.0, "total_frames": 3600, "analysis_step": 1, "has_audio": True}


def test_clean_pack_passes_and_has_per_minute_rows():
    sc = scenes([(0, 40, ""), (40, 80, "hi"), (80, 120, "")])
    tr = {"coverage_ratio": 0.97, "segments": [{"start": 0, "end": 55, "text": "a b c d"}, {"start": 60, "end": 118, "text": "e f g"}]}
    cl = [{"cluster": 1, "rep_scene": 1, "members": [1, 2, 3], "in_collage": True}]
    a = audit.build(INFO, 3600, sc, cl, {"ebu_r128": {"integrated_lufs": -16}}, tr)
    assert a["pass"], a["warnings"]
    assert len(a["per_minute"]) == 2 and a["per_minute"][0]["cuts"] == 1 and a["per_minute"][1]["cuts"] == 1
    assert a["per_minute"][0]["words"] == 4 and a["per_minute"][1]["words"] == 3


def test_short_transcript_missing_frames_and_big_step_are_flagged():
    sc = scenes([(0, 120, None)])
    tr = {"coverage_ratio": 0.14, "segments": [{"start": 0, "end": 8, "text": "a b"}]}
    info = dict(INFO, analysis_step=2)
    a = audit.build(info, 1000, sc, [{"cluster": 1, "rep_scene": 1, "members": [1], "in_collage": True}], {}, tr)
    text = " ".join(a["warnings"])
    assert not a["pass"]
    for must in ("frames were analysed", "analysis step is 2", "transcript covers 0.14", "OCR", "LUFS", "minute 2: no words"):
        assert must in text, must
