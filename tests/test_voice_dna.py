"""Voice micro-analysis on synthetic 'speech' (tones with known pitch / loudness / gaps)."""
import numpy as np
import soundfile as sf

from scripts import voice_dna as V

SR = 16000


def _tone(f, secs, amp=0.3):
    t = np.arange(int(SR * secs)) / SR
    # harmonic-rich so pitch trackers lock on
    return amp * sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 2, 3))


def _glide(f0, f1, secs, amp=0.3):
    n = int(SR * secs)
    f = np.linspace(f0, f1, n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (amp * sum(np.sin(k * ph) / k for k in (1, 2, 3))).astype(np.float32)


def _wave(parts):
    """parts: list of (freq|None, secs, amp)."""
    return np.concatenate([np.zeros(int(SR * s)) if f is None else _tone(f, s, a) for f, s, a in parts]).astype(np.float32)


def _tr(segs):
    return {"available": True, "segments": segs}


def test_pitch_median_close_to_known(tmp_path):
    y = _wave([(150, 2.0, 0.3), (None, 0.5, 0), (150, 2.0, 0.3)])
    p = tmp_path / "a.wav"
    sf.write(p, y, SR)
    v = V.analyse(p, _tr([{"start": 0.0, "end": 2.0, "text": "one two three four five six"}, {"start": 2.5, "end": 4.5, "text": "seven eight nine ten"}]))
    assert v["available"]
    assert abs(v["global"]["pitch_median_hz"] - 150) < 6
    assert v["global"]["expressiveness"] == "monotone"          # one fixed pitch


def test_rising_and_falling_endings(tmp_path):
    rise = np.concatenate([_tone(130, 1.2), _glide(130, 200, 0.8)]).astype(np.float32)
    fall = np.concatenate([_tone(200, 1.2), _glide(200, 130, 0.8)]).astype(np.float32)
    y = np.concatenate([rise, np.zeros(int(SR * 0.6), np.float32), fall])
    p = tmp_path / "b.wav"
    sf.write(p, y, SR)
    v = V.analyse(p, _tr([{"start": 0.0, "end": 2.0, "text": "is it really so"}, {"start": 2.6, "end": 4.6, "text": "yes it is so"}]))
    ends = [s["ending"] for s in v["sentences"]]
    assert ends == ["rising", "falling"]
    assert v["sentence_endings"] == {"rising": 1, "falling": 1, "flat": 0}


def test_tempo_gaps_and_pause_fields(tmp_path):
    y = _wave([(140, 1.5, 0.3), (None, 1.2, 0), (140, 1.5, 0.3)])
    p = tmp_path / "c.wav"
    sf.write(p, y, SR)
    v = V.analyse(p, _tr([{"start": 0.0, "end": 1.5, "text": "a b c d e f g h"}, {"start": 2.7, "end": 4.2, "text": "i j k"}]))
    s0, s1 = v["sentences"]
    assert s0["wpm"] == 320.0 and s0["rate"] == "very fast"
    assert s1["pause_before_s"] == 1.2 and s0["pause_after_s"] == 1.2
    assert v["gaps"]["bins"]["1.0-up"] == 1


def test_emphasis_needs_word_times_and_finds_loud_high_long_word(tmp_path):
    parts, words, t = [], [], 0.0
    for i in range(12):
        loud = i == 6
        parts.append((220 if loud else 130, 0.7 if loud else 0.3, 0.5 if loud else 0.2))
        words.append({"w": "BIG" if loud else f"w{i}", "start": t, "end": t + parts[-1][1]})
        t += parts[-1][1]
    p = tmp_path / "d.wav"
    sf.write(p, _wave(parts), SR)
    seg = {"start": 0.0, "end": t, "text": " ".join(w["w"] for w in words), "words": words}
    v = V.analyse(p, _tr([seg]))
    assert v["words_timed"] is True
    assert [e["w"] for e in v["emphasis"]][:1] == ["BIG"]
    seg2 = {k: x for k, x in seg.items() if k != "words"}
    v2 = V.analyse(p, _tr([seg2]))
    assert v2["words_timed"] is False and v2["emphasis"] == [] and "emphasis_note" in v2


def test_timeline_windows_and_per_minute(tmp_path):
    p = tmp_path / "e.wav"
    sf.write(p, _wave([(140, 12.0, 0.3)]), SR)
    v = V.analyse(p, _tr([{"start": 0.0, "end": 12.0, "text": " ".join(["w"] * 30)}]))
    assert [w["from"] for w in v["timeline"]] == [0.0, 5.0, 10.0][: len(v["timeline"])]
    assert v["timeline"][0]["wpm"] == 150.0
    assert len(v["per_minute"]) == 1


def test_silence_and_json_safe(tmp_path):
    p = tmp_path / "f.wav"
    sf.write(p, np.zeros(SR * 3, np.float32), SR)
    v = V.analyse(p, _tr([]))
    assert v["available"] is False
    ok = V.finite({"a": float("nan"), "b": [1.0, float("inf")]})
    assert ok == {"a": None, "b": [1.0, None]}


def test_compact_is_small(tmp_path):
    p = tmp_path / "g.wav"
    sf.write(p, _wave([(140, 3.0, 0.3)]), SR)
    v = V.analyse(p, _tr([{"start": 0.0, "end": 3.0, "text": "one two three"}]))
    import json
    assert len(json.dumps(V.finite(V.compact(v)))) < 3000
    assert V.summary_line(v).startswith("voice: pitch")


def test_librosa_fallback_when_praat_missing(tmp_path, monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "parselmouth", None)
    p = tmp_path / "h.wav"
    sf.write(p, _wave([(150, 2.5, 0.3)]), SR)
    v = V.analyse(p, _tr([{"start": 0.0, "end": 2.5, "text": "one two three four five"}]))
    assert v["available"] and v["backend"] == "librosa_pyin"
    assert abs(v["global"]["pitch_median_hz"] - 150) < 8
