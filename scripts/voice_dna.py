"""Voice micro-analysis: how the creator SPEAKS, in numbers (rules: rulebooks/09-standards-sound.md, 02-scripting.md).
Output voice.json: global voice profile + every sentence + every word flagged for emphasis + every gap + a timeline
(5 s windows for short reels, 60 s for long ones) + per-minute rows. Only measured numbers; labels are derived from the numbers
by fixed thresholds and say so. NO emotion guessing: an emotion label from a model would be a guess, so it is not written.
Pitch: Praat (parselmouth) when installed, else librosa.pyin. Speaker-relative units: semitones around the speaker's own median.
"""
import math

import numpy as np

HOP_S = 0.01
F0_FLOOR, F0_CEIL = 70.0, 450.0
MAX_ANALYSE_S = 1200          # a very long file is analysed in its first 20 minutes (stated in the output)
GAP_BINS = [(0.15, 0.3), (0.3, 0.6), (0.6, 1.0), (1.0, 99.0)]
RATE_LABELS = [(110, "slow"), (160, "medium"), (200, "fast"), (1e9, "very fast")]


# ------------------------------------------------------------------ frame tracks
def pitch_track(y, sr):
    """-> (times, f0_hz with nan = unvoiced, db, backend, quality{jitter, shimmer, hnr_db} or {})."""
    try:
        import parselmouth
        from parselmouth.praat import call
        snd = parselmouth.Sound(y.astype(np.float64), sampling_frequency=sr)
        pitch = snd.to_pitch(time_step=HOP_S, pitch_floor=F0_FLOOR, pitch_ceiling=F0_CEIL)
        t = pitch.xs()
        f0 = pitch.selected_array["frequency"].astype(float)
        f0[f0 <= 0] = np.nan
        inten = snd.to_intensity(minimum_pitch=F0_FLOOR, time_step=HOP_S)
        db = np.interp(t, inten.xs(), inten.values[0])
        q = {}
        try:
            pp = call(snd, "To PointProcess (periodic, cc)", F0_FLOOR, F0_CEIL)
            q["jitter_local"] = round(float(call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)), 4)
            q["shimmer_local"] = round(float(call([snd, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)), 4)
            q["hnr_db"] = round(float(call(snd.to_harmonicity(), "Get mean", 0, 0)), 1)
        except Exception:  # noqa: BLE001  (voice quality is a bonus; pitch must not depend on it)
            q = {}
        return t, f0, db, "praat", q
    except Exception:  # noqa: BLE001
        import librosa
        hop = int(sr * HOP_S)
        f0, _, _ = librosa.pyin(y, fmin=F0_FLOOR, fmax=F0_CEIL, sr=sr, frame_length=2048, hop_length=hop)
        rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop)[0]
        n = min(len(f0), len(rms))
        t = np.arange(n) * HOP_S
        return t, np.asarray(f0[:n], float), 20 * np.log10(np.maximum(rms[:n], 1e-6)), "librosa_pyin", {}


def to_semitones(f0, ref):
    with np.errstate(invalid="ignore", divide="ignore"):
        return 12.0 * np.log2(f0 / ref)


# ------------------------------------------------------------------ helpers
def _sel(t, a, b):
    return (t >= a) & (t < b)


def _nanstat(x, fn, default=None):
    x = x[~np.isnan(x)]
    return default if x.size == 0 else round(float(fn(x)), 2)


def span_stats(t, st, db, voiced_db_floor, a, b):
    """Pitch and loudness of one time span (semitones relative to the speaker's median)."""
    m = _sel(t, a, b)
    s, d = st[m], db[m]
    n = int(m.sum())
    return {
        "pitch_med_st": _nanstat(s, np.median), "pitch_range_st": _nanstat(s, lambda x: np.percentile(x, 90) - np.percentile(x, 10)),
        "pitch_std_st": _nanstat(s, np.std), "voiced_share": round(float((~np.isnan(s)).sum() / n), 2) if n else 0.0,
        "energy_db_mean": _nanstat(d[d > voiced_db_floor], np.mean), "energy_range_db": _nanstat(d[d > voiced_db_floor], lambda x: np.percentile(x, 95) - np.percentile(x, 10)),
    }


def contour(t, st, a, b, tail=0.3):
    """Shape of the end of a sentence: change in pitch (semitones) between the middle and the last part of the final 30 %."""
    L = b - a
    if L < 0.4:
        return {"ending": "too_short"}
    m1 = _sel(t, b - L * tail, b - L * tail / 2)
    m2 = _sel(t, b - L * tail / 2, b)
    p1, p2 = st[m1][~np.isnan(st[m1])], st[m2][~np.isnan(st[m2])]
    if len(p1) < 3 or len(p2) < 3:
        return {"ending": "unvoiced"}
    d = float(np.median(p2) - np.median(p1))
    return {"ending": "rising" if d >= 1.5 else "falling" if d <= -1.5 else "flat", "ending_change_st": round(d, 2)}


def rate_label(wpm):
    return next(lab for lim_, lab in RATE_LABELS if wpm < lim_)


def gap_stats(gaps):
    g = [x for x in gaps if x >= GAP_BINS[0][0]]
    return {"count": len(g), "total_s": round(sum(g), 2), "mean_s": round(float(np.mean(g)), 2) if g else 0.0,
            "max_s": round(max(g), 2) if g else 0.0,
            "bins": {f"{a}-{b if b < 99 else 'up'}": sum(a <= x < b for x in g) for a, b in GAP_BINS}}


def _words_of(seg):
    """Words with times: from whisper word timestamps if present, else spread evenly (flag words_timed False)."""
    ws = seg.get("words")
    if ws:
        return [{"w": w.get("w") or w.get("word", "").strip(), "start": float(w["start"]), "end": float(w["end"])} for w in ws if (w.get("w") or w.get("word", "")).strip()], True
    toks = (seg.get("text") or "").split()
    if not toks:
        return [], False
    a, b = float(seg["start"]), float(seg["end"])
    step = (b - a) / len(toks)
    return [{"w": w, "start": round(a + i * step, 3), "end": round(a + (i + 1) * step, 3)} for i, w in enumerate(toks)], False


def emphasis(words, t, st, db, floor, top_z=1.0):
    """Words said with more pitch, more energy and/or longer than the speaker's own average (z-scores inside this reel).
    Needs real word times. Returns [{w, t, z_pitch, z_energy, z_len, score}] for words with score >= top_z (>= 2 cues agree)."""
    rows = []
    for w in words:
        m = _sel(t, w["start"], w["end"])
        s, d = st[m][~np.isnan(st[m])], db[m]
        if len(s) < 2 or len(d) < 2:
            continue
        rows.append((w, float(np.max(s)), float(np.mean(d[d > floor])) if (d > floor).any() else float(np.mean(d)),
                     (w["end"] - w["start"]) / max(len(w["w"]), 1)))
    if len(rows) < 8:
        return []
    cols = np.array([[r[1], r[2], r[3]] for r in rows])
    mu, sd = cols.mean(0), cols.std(0) + 1e-9
    z = (cols - mu) / sd
    out = []
    for (w, *_), zz in zip(rows, z):
        cues = int((zz > 0.8).sum())
        score = float(zz.mean())
        if cues >= 2 and score >= top_z * 0.6:
            out.append({"w": w["w"], "t": round(w["start"], 2), "z_pitch": round(float(zz[0]), 2), "z_energy": round(float(zz[1]), 2),
                        "z_len": round(float(zz[2]), 2), "score": round(score, 2)})
    return sorted(out, key=lambda r: -r["score"])[:40]


# ------------------------------------------------------------------ main
def analyse(wav, transcript, duration_s=None):
    """-> voice dict (JSON-able). Never raises: any problem becomes {'available': False, 'reason': ...}."""
    try:
        import librosa
        y, sr = librosa.load(str(wav), sr=16000, mono=True)
        if y.size < sr:
            return {"available": False, "reason": "audio shorter than 1 s"}
        dur = len(y) / sr
        y = y[: int(MAX_ANALYSE_S * sr)]
        t, f0, db, backend, quality = pitch_track(y, sr)
        return build(t, f0, db, backend, quality, transcript, dur, analysed_s=len(y) / sr)
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"{type(e).__name__}: {e}"[:160]}


def build(t, f0, db, backend, quality, transcript, dur, analysed_s=None):
    analysed_s = analysed_s or dur
    voiced = f0[~np.isnan(f0)]
    if voiced.size < 20:
        return {"available": False, "reason": "no voiced speech found (music only or silence)"}
    ref = float(np.median(voiced))
    st = to_semitones(f0, ref)
    floor = float(np.percentile(db, 20)) + 3.0          # frames above this count as speech energy
    segs = [s for s in (transcript or {}).get("segments", []) if s.get("text") and not s.get("loop") and s["start"] < analysed_s]
    out = {"available": True, "backend": backend, "duration_s": round(dur, 2), "analysed_s": round(analysed_s, 2),
           "units": "pitch in semitones relative to the speaker's own median; energy in dB (relative, not LUFS)",
           "labels_note": "labels are fixed-threshold readings of the numbers, not emotion guesses"}
    g = span_stats(t, st, db, floor, 0, analysed_s)
    out["global"] = {
        "pitch_median_hz": round(ref, 1), "pitch_p10_hz": round(float(np.percentile(voiced, 10)), 1), "pitch_p90_hz": round(float(np.percentile(voiced, 90)), 1),
        **g, "expressiveness": ("monotone" if (g["pitch_std_st"] or 0) < 2.0 else "lively" if (g["pitch_std_st"] or 0) < 4.0 else "very expressive"),
        "voice_quality": quality or "needs parselmouth",
    }
    if not segs:
        out["sentences"], out["note"] = [], "no transcript: pitch/energy only"
        out["timeline"], out["per_minute"] = _timeline(t, st, db, floor, [], analysed_s), _per_minute(t, st, db, floor, [], analysed_s)
        return out
    rows, all_words, gaps, timed = [], [], [], True
    prev_end = None
    for i, s in enumerate(segs):
        a, b = float(s["start"]), float(s["end"])
        ws, wt = _words_of(s)
        timed = timed and wt
        all_words += ws
        n = len(ws)
        inner = [ws[k + 1]["start"] - ws[k]["end"] for k in range(n - 1)] if wt else []
        speak = max((b - a) - sum(x for x in inner if x >= 0.25), 0.2)
        before = round(a - prev_end, 2) if prev_end is not None else round(a, 2)
        if prev_end is not None and a - prev_end > 0:
            gaps.append(a - prev_end)
        gaps += [x for x in inner if x > 0]
        wpm = round(n / max((b - a) / 60.0, 1e-6), 1)
        rows.append({"i": i, "start": round(a, 2), "end": round(b, 2), "text": s["text"][:140], "words": n, "wpm": wpm,
                     "articulation_wpm": round(n / (speak / 60.0), 1), "rate": rate_label(wpm), "pause_before_s": max(before, 0.0),
                     **span_stats(t, st, db, floor, a, b), **contour(t, st, a, b)})
        prev_end = b
    for r, nxt in zip(rows, rows[1:]):
        r["pause_after_s"] = max(round(nxt["start"] - r["end"], 2), 0.0)
    if rows:
        rows[-1]["pause_after_s"] = round(max(analysed_s - rows[-1]["end"], 0.0), 2)
    wpms = [r["wpm"] for r in rows if r["words"] >= 3]
    out["sentences"] = rows
    out["tempo"] = {"wpm_mean": round(float(np.mean(wpms)), 1) if wpms else None, "wpm_min": min(wpms) if wpms else None,
                    "wpm_max": max(wpms) if wpms else None, "wpm_cv": round(float(np.std(wpms) / np.mean(wpms)), 2) if len(wpms) > 1 else None,
                    "rate": rate_label(float(np.mean(wpms))) if wpms else None,
                    "fastest_sentence": max(rows, key=lambda r: r["wpm"] if r["words"] >= 3 else 0)["i"] if wpms else None,
                    "slowest_sentence": min(rows, key=lambda r: r["wpm"] if r["words"] >= 3 else 1e9)["i"] if wpms else None}
    out["gaps"] = gap_stats(gaps)
    ends = [r["ending"] for r in rows if r.get("ending") in ("rising", "falling", "flat")]
    out["sentence_endings"] = {k: ends.count(k) for k in ("rising", "falling", "flat")}
    out["words_timed"] = bool(timed)
    out["emphasis"] = emphasis(all_words, t, st, db, floor) if timed else []
    if not timed:
        out["emphasis_note"] = "no word-level times in this transcript: emphasis not measured (turn on analysis.word_timestamps)"
    out["timeline"] = _timeline(t, st, db, floor, rows, analysed_s)
    out["per_minute"] = _per_minute(t, st, db, floor, rows, analysed_s)
    return out


def _window_rows(t, st, db, floor, rows, a, b):
    w = [r for r in rows if r["start"] < b and r["end"] > a]
    words = sum(r["words"] * (min(r["end"], b) - max(r["start"], a)) / max(r["end"] - r["start"], 1e-6) for r in w)
    spoken = sum(min(r["end"], b) - max(r["start"], a) for r in w)
    d = span_stats(t, st, db, floor, a, b)
    return {"from": round(a, 1), "to": round(b, 1), "wpm": round(words / max((b - a) / 60.0, 1e-6), 1) if rows else None,
            "speech_share": round(min(spoken / max(b - a, 1e-6), 1.0), 2) if rows else None, **d}


def _timeline(t, st, db, floor, rows, dur, short_step=5.0, long_step=60.0):
    step = short_step if dur <= 120 else long_step
    return [_window_rows(t, st, db, floor, rows, a, min(a + step, dur)) for a in np.arange(0, dur, step) if min(a + step, dur) - a >= 1.0]


def _per_minute(t, st, db, floor, rows, dur):
    return [_window_rows(t, st, db, floor, rows, a, min(a + 60.0, dur)) for a in np.arange(0, dur, 60.0) if min(a + 60.0, dur) - a >= 1.0]


def summary_line(v):
    """One short line for the pack summary / job note."""
    if not v.get("available"):
        return "voice: not measured (" + str(v.get("reason", "?")) + ")"
    g = v["global"]
    tp = v.get("tempo") or {}
    return (f"voice: pitch {g['pitch_median_hz']} Hz, {g['expressiveness']}, tempo {tp.get('wpm_mean')} wpm ({tp.get('rate')}), "
            f"{(v.get('gaps') or {}).get('count', 0)} gaps, {len(v.get('emphasis', []))} emphasised words")


def compact(v):
    """Small version for metrics_summary.json (the full file stays in voice.json)."""
    if not v.get("available"):
        return {k: v.get(k) for k in ("available", "reason")}
    return {"available": True, "backend": v["backend"], "global": v["global"], "tempo": v.get("tempo"), "gaps": v.get("gaps"),
            "sentence_endings": v.get("sentence_endings"), "emphasis_top": v.get("emphasis", [])[:8], "words_timed": v.get("words_timed")}


def finite(o):
    """JSON-safe, recursively: NaN / inf -> None, numpy numbers/arrays -> plain Python (np.int64 is not JSON)."""
    if isinstance(o, dict):
        return {k: finite(x) for k, x in o.items()}
    if isinstance(o, (list, tuple)):
        return [finite(x) for x in o]
    if hasattr(o, "item") and getattr(o, "shape", None) == ():
        o = o.item()
    elif hasattr(o, "tolist"):
        return finite(o.tolist())
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o
