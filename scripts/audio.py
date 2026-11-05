"""Audio analysis (scripts only): beats, tempo, loudness, silence, cut/beat sync, optional transcript.
Voice/music separation (demucs) is NOT run in v1.
"""
from pathlib import Path

import numpy as np

from .common import limits, log, run_cmd, tail


def extract_wav(video, out_wav):
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    rc, _, err = run_cmd(["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "22050",
                          "-f", "wav", str(out_wav)])
    if rc != 0:
        raise RuntimeError("audio extract failed:\n" + tail(err))
    return out_wav


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
            "silences": silences[:20], "cut_beat_sync": sync}


def transcribe(wav):
    """Optional: faster-whisper. Never raises. Audio goes in as a librosa array (PyAV decoder clashes on Colab).
    Hinglish is often detected as Hindi/Urdu and written in Arabic script. If so, run again as English with a
    romanised-Hindi prompt so the text comes out in Latin letters."""
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return {"available": False}
    try:
        import re
        import librosa
        y, _ = librosa.load(str(wav), sr=16000, mono=True)
        model = WhisperModel(limits()["analysis"]["whisper_model"], device="auto", compute_type="int8")

        def run(**kw):
            segs, info = model.transcribe(y, vad_filter=True, **kw)
            return [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs], info

        out, info = run()
        text = " ".join(x["text"] for x in out)
        lang, redo = info.language, False
        if re.search(r"[\u0600-\u06FF]", text):  # Arabic/Urdu script = wrong for Hinglish
            out, info = run(language="en", initial_prompt="Hinglish: Hindi words written in English letters, like jaha pe duniya bhar.")
            text, lang, redo = " ".join(x["text"] for x in out), info.language, True
        log(f"transcript segments: {len(out)}" + (" (re-run romanised)" if redo else ""))
        return {"available": True, "language": lang, "romanised_rerun": redo, "segments": out, "text": text}
    except Exception as e:  # noqa: BLE001
        log(f"transcript skipped: {type(e).__name__}")
        return {"available": False, "error": tail(f"{type(e).__name__}: {e}", 3)}
