"""Voiceover (scripts only): Kokoro-82M (Apache-2.0, free, CPU) via kokoro-onnx. Claude never listens; checks are numbers.

Input script JSON: {"voice": "am_michael", "speed": 1.05, "lang": "en-us", "target_lufs": -16,
                    "segments": [{"id": "s1", "text": "...", "pause_after_s": 0.3}, ...]}
Output: one wav (48 kHz mono, loudness-normalised) + timings JSON {segments: [{id, text, start_s, end_s}], duration_s, ...}.
One synthesis call per segment, so segment times are exact (captions and scene cuts are built from them).
Model files come from GitHub releases (Hugging Face is not reachable everywhere) and are cached in ~/.cache/itcod/kokoro.
"""
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from .common import log, run_cmd, tail

CACHE = Path.home() / ".cache" / "itcod" / "kokoro"
BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = {"kokoro-v1.0.onnx": "7d5df8ecf7d4b1878015", "voices-v1.0.bin": "bca610b8308e8d99f32e"}  # sha256 prefixes
MODEL_SR = 24000
OUT_SR = 48000


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ensure_model():
    CACHE.mkdir(parents=True, exist_ok=True)
    import urllib.request
    for name, pre in FILES.items():
        p = CACHE / name
        for attempt in range(2):
            if attempt or not p.exists() or p.stat().st_size == 0:
                log(f"tts: downloading {name}")
                urllib.request.urlretrieve(BASE + name, p)   # overwrites a bad copy in place
            if _sha(p).startswith(pre):
                break
        else:
            raise RuntimeError(f"tts model file {name} failed its checksum")
    return CACHE / "kokoro-v1.0.onnx", CACHE / "voices-v1.0.bin"


def _trim(y, sr, thr_db=-45.0, keep_s=0.04):
    """Cut leading/trailing near-silence, keep a few ms so consonants are not clipped."""
    if y.size == 0:
        return y
    env = np.abs(y)
    thr = np.max(env) * (10 ** (thr_db / 20))
    idx = np.where(env > thr)[0]
    if idx.size == 0:
        return y
    k = int(keep_s * sr)
    return y[max(0, idx[0] - k): min(len(y), idx[-1] + k)]


def _with_lexicon(k, text, lang, lex):
    """Names the phonemizer gets wrong: script 'lexicon' {word: IPA}. Returns phonemes for the whole text."""
    import re
    if not lex:
        return None
    keys = sorted(lex, key=len, reverse=True)
    pat = re.compile("(" + "|".join(re.escape(w) for w in keys) + ")")
    if not pat.search(text):
        return None
    out = []
    for part in pat.split(text):
        if not part:
            continue
        if part in lex:
            out.append(lex[part])
        elif part.strip():
            ph = k.tokenizer.phonemize(part, lang)
            out.append(ph if not part.startswith(" ") else " " + ph)
            if part.endswith(" "):
                out.append(" ")
        else:
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def synth(script, out_wav, out_json):
    from kokoro_onnx import Kokoro
    from scipy.signal import resample_poly
    import soundfile as sf
    from .common import to_native
    t0 = time.time()
    model, voices = ensure_model()
    k = Kokoro(str(model), str(voices))
    voice, speed, lang = script.get("voice", "am_michael"), float(script.get("speed", 1.0)), script.get("lang", "en-us")
    lead = float(script.get("lead_in_s", 0.15))
    parts = [np.zeros(int(lead * MODEL_SR), dtype=np.float32)]
    t, rows = lead, []
    for seg in script["segments"]:
        ph = _with_lexicon(k, seg["text"], lang, script.get("lexicon") or {})
        y, sr = k.create(ph or seg["text"], voice=seg.get("voice", voice), speed=float(seg.get("speed", speed)),
                         lang=lang, is_phonemes=bool(ph))
        y = _trim(np.asarray(y, dtype=np.float32), sr)
        d = len(y) / sr
        rows.append({"id": seg["id"], "text": seg["text"], "start_s": round(t, 3), "end_s": round(t + d, 3)})
        pause = float(seg.get("pause_after_s", 0.25))
        parts += [y, np.zeros(int(pause * sr), dtype=np.float32)]
        t += d + pause
    y = np.concatenate(parts)
    y = resample_poly(y, OUT_SR // MODEL_SR, 1).astype(np.float64)
    target = float(script.get("target_lufs", -16.0))
    out_wav, out_json = Path(out_wav), Path(out_json)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmpdir = tempfile.TemporaryDirectory(prefix="itcod-tts-")
    raw = Path(tmpdir.name) / "raw.wav"
    sf.write(str(raw), y.astype(np.float32), OUT_SR, subtype="FLOAT")
    lufs = None
    try:
        import pyloudnorm as pyln
        lufs = float(pyln.Meter(OUT_SR).integrated_loudness(y))
    except Exception:  # noqa: BLE001
        pass
    # EBU R128 loudness normalisation with a true-peak limiter (TTS is peaky: plain gain would clip or stay quiet).
    # One-pass loudnorm lands ~2 LU short on speech, so a second pass aims past the target by the measured miss.
    import pyloudnorm as pyln
    aim = target
    for _ in range(2):
        rc, _, err = run_cmd(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af",
                              f"loudnorm=I={aim}:TP=-1.5:LRA=11", "-ar", str(OUT_SR), "-ac", "1",
                              "-c:a", "pcm_s24le", str(out_wav)], timeout=600)
        if rc != 0:
            raise RuntimeError("tts loudness step failed:\n" + tail(err))
        y, _ = sf.read(str(out_wav))
        got = float(pyln.Meter(OUT_SR).integrated_loudness(y))
        if abs(got - target) <= 0.5:
            break
        aim = max(-9.0, aim + (target - got))
    tmpdir.cleanup()
    words = sum(len(s["text"].split()) for s in script["segments"])
    speech = sum(r["end_s"] - r["start_s"] for r in rows)
    res_lufs = round(got, 1)
    res = {"engine": "kokoro-82M onnx v1.0 (Apache-2.0)", "voice": voice, "speed": speed, "lang": lang,
           "duration_s": round(len(y) / OUT_SR, 3), "segments": rows, "words": words,
           "wpm_speaking": round(words / (speech / 60.0), 1) if speech else 0.0,
           "input_lufs": round(lufs, 1) if lufs is not None else None, "target_lufs": target, "output_lufs": res_lufs,
           "synth_s": round(time.time() - t0, 1)}
    out_json.write_text(json.dumps(to_native(res), ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"tts: {res['duration_s']} s of voice, {res['wpm_speaking']} wpm, in {res['synth_s']} s")
    return res
