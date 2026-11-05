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
    """Optional: faster-whisper. Returns {'available': False} if not installed."""
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return {"available": False}
    model = WhisperModel(limits()["analysis"]["whisper_model"], device="auto", compute_type="int8")
    segs, info = model.transcribe(str(wav), vad_filter=True)
    out = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
    log(f"transcript segments: {len(out)}")
    return {"available": True, "language": info.language, "segments": out,
            "text": " ".join(x["text"] for x in out)}
