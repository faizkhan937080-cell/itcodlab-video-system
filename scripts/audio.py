"""Audio analysis (scripts only): beats, tempo, loudness, silence, cut/beat sync, optional transcript.
Voice/music separation (demucs) is NOT run in v1.
"""
from pathlib import Path

import numpy as np

from .common import limits, log, run_cmd, tail


def extract_wav(video, out_wav):
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    rc, _, err = run_cmd(["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "48000",
                          "-f", "wav", str(out_wav)])
    if rc != 0:
        raise RuntimeError("audio extract failed:\n" + tail(err))
    return out_wav


def loudness_ebu(wav):
    """ITU-R BS.1770 / EBU R128 loudness: integrated LUFS, loudness range (LU), true peak (dBTP, 4x oversampled).
    Mono mix of the file. Returns {} if pyloudnorm is missing or the audio is too short. Never raises."""
    try:
        import pyloudnorm as pyln
        import soundfile as sf
        from scipy.signal import resample_poly
        data, sr = sf.read(str(wav), dtype="float64")
        if data.ndim > 1:
            data = data.mean(axis=1)
        if len(data) < sr * 0.5:
            return {}
        meter = pyln.Meter(sr)
        integrated = float(meter.integrated_loudness(data))
        tp = float(np.max(np.abs(resample_poly(data, 4, 1))))
        out = {"integrated_lufs": round(integrated, 1),
               "true_peak_dbtp": round(20 * np.log10(max(tp, 1e-9)), 1)}
        win, hop = int(3 * sr), int(1 * sr)
        st = []
        for a in range(0, max(len(data) - win, 0) + 1, hop):
            seg = data[a:a + win]
            if len(seg) >= win:
                v = float(meter.integrated_loudness(seg))
                if np.isfinite(v):
                    st.append(v)
        st = [v for v in st if v > -70.0]
        if st:
            rel = [v for v in st if v > integrated - 20.0] or st
            out["short_term_max_lufs"] = round(max(st), 1)
            if len(rel) >= 3:
                out["lra_lu"] = round(float(np.percentile(rel, 95) - np.percentile(rel, 10)), 1)
        out["method"] = "pyloudnorm BS.1770, mono mix"
        return out
    except Exception as e:  # noqa: BLE001
        log(f"loudness_ebu skipped: {type(e).__name__}")
        return {}


def separate_stems(wav, workdir):
    """Voice vs music/everything-else with demucs (two stems), then measure each in LUFS.
    Optional: returns {} when demucs is not installed or anything fails. Never raises."""
    import importlib.util
    import sys
    if importlib.util.find_spec("demucs") is None:
        return {}
    try:
        out = Path(workdir) / "stems"
        rc, _, err = run_cmd([sys.executable, "-m", "demucs.separate", "--two-stems=vocals", "-n", "htdemucs",
                              "-o", str(out), str(wav)], timeout=1500)
        if rc != 0:
            log("stems skipped: " + tail(err, 2))
            return {}
        base = out / "htdemucs" / Path(wav).stem
        v, m = loudness_ebu(base / "vocals.wav"), loudness_ebu(base / "no_vocals.wav")
        if not v or not m:
            return {}
        return {"vocals_lufs": v["integrated_lufs"], "music_lufs": m["integrated_lufs"],
                "voice_minus_music_lu": round(v["integrated_lufs"] - m["integrated_lufs"], 1), "engine": "demucs htdemucs"}
    except Exception as e:  # noqa: BLE001
        log(f"stems skipped: {type(e).__name__}")
        return {}


def analyze_audio(wav, cut_times, sr_target=22050):
    import librosa
    y, sr = librosa.load(str(wav), sr=sr_target, mono=True)
    if y.size < sr // 2:
        return {"has_audio": True, "too_short": True}
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    bpm = float(np.atleast_1d(tempo)[0])
    rms = librosa.feature.rms(y=y)[0]
    db = 20 * np.log10(np.maximum(rms, 1e-6))
    intervals = librosa.effects.split(y, top_db=40)
    dur = len(y) / sr
    silences = []
    prev_end = 0
    for s, e in intervals:
        if (s - prev_end) / sr >= 0.3:
            silences.append([round(prev_end / sr, 2), round(s / sr, 2)])
        prev_end = e
    if (len(y) - prev_end) / sr >= 0.3:
        silences.append([round(prev_end / sr, 2), round(dur, 2)])
    sync = None
    if len(beats) and len(cut_times):
        offs = [float(np.min(np.abs(beats - c))) for c in cut_times]
        sync = {"cuts_checked": len(offs), "share_within_80ms": round(sum(o <= 0.08 for o in offs) / len(offs), 3),
                "median_offset_s": round(float(np.median(offs)), 3)}
    return {"has_audio": True, "duration_s": round(dur, 2), "bpm": round(bpm, 1),
            "beat_count": int(len(beats)), "beat_times_first_20": [round(float(b), 2) for b in beats[:20]],
            "loudness_db_mean": round(float(db.mean()), 1), "loudness_db_max": round(float(db.max()), 1),
            "silences": silences[:20], "cut_beat_sync": sync, "ebu_r128": loudness_ebu(wav),
            "stems": separate_stems(wav, Path(wav).parent) if limits()["analysis"].get("stems") and dur <= 900 else {},
            "silence_share": round(sum(b - a for a, b in silences) / dur, 3) if dur else 0.0}


def transcribe(wav):
    """Optional: faster-whisper. Never raises. Audio goes in as a librosa array (PyAV decoder clashes on Colab).
    Deterministic settings (temperature 0, no carry-over between segments) because runs of the same reel gave
    full text once and only the first 8 s another time. Hinglish: pass A = auto language (often Devanagari with
    English words spelled phonetically); pass B = English + romanised-Hindi prompt (English terms come out right).
    Both are kept. `coverage_ratio` = last segment end / audio length, so a short transcript is visible."""
    import os
    if os.environ.get("ITCOD_KAGGLE_GPU") == "1":  # opt-in free GPU; same function runs there; None = fall back to CPU below
        try:
            from . import kaggle_gpu
            remote = kaggle_gpu.transcribe(wav) if kaggle_gpu.enabled() else None
        except Exception:  # noqa: BLE001
            remote = None
        if remote:
            return remote
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return {"available": False}
    try:
        import re
        import librosa
        y, sr = librosa.load(str(wav), sr=16000, mono=True)
        dur = float(len(y)) / float(sr) if sr else 0.0
        want_words = bool(limits()["analysis"].get("word_timestamps", True))
        model = WhisperModel(limits()["analysis"]["whisper_model"], device="auto", compute_type="int8")

        def run(**kw):
            segs, info = model.transcribe(y, vad_filter=True, temperature=0.0, condition_on_previous_text=False,
                                          beam_size=5, word_timestamps=want_words, **kw)
            out = []
            for s in segs:
                row = {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
                if want_words and getattr(s, "words", None):   # per-word times: emphasis, gaps, karaoke captions
                    row["words"] = [{"w": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2), "p": round(float(w.probability), 2)}
                                    for w in s.words if w.word.strip()]
                out.append(row)
            return out, info.language

        def pack(out, lang):
            from .script_metrics import collapse_loops
            looped = 0
            for x in out:  # whisper repetition loops: keep one copy, drop pure-loop segments from text and coverage
                x["text"], gone, is_loop = collapse_loops(x["text"])
                looped += gone
                if is_loop:
                    x["loop"] = True
            good = [x for x in out if not x.get("loop")]
            text = " ".join(x["text"] for x in good)
            cov = round((good[-1]["end"] / dur), 2) if good and dur else 0.0
            res = {"language": lang, "segments": out, "text": text, "coverage_ratio": cov}
            if looped:
                res["loop_words_removed"] = looped
            return res

        a_out, a_lang = run()
        a = pack(a_out, a_lang)
        res = {"available": True, **a}
        if a_lang in ("hi", "ur", "mr", "pa") or re.search(r"[\u0600-\u06FF\u0900-\u097F]", a["text"]):
            b_out, b_lang = run(language="en", initial_prompt="Hinglish: Hindi words written in English letters, "
                                "mixed with English tech words like animation, Claude, skill, free library.")
            res["alt_english"] = pack(b_out, b_lang)
        log(f"transcript segments: {len(a_out)}, coverage {a['coverage_ratio']}" + (", + english pass" if "alt_english" in res else ""))
        return res
    except Exception as e:  # noqa: BLE001
        log(f"transcript skipped: {type(e).__name__}")
        return {"available": False, "error": tail(f"{type(e).__name__}: {e}", 3)}
