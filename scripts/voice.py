"""Voice clean-up + music ducking (ffmpeg filters, worker). Rules: rulebooks/14-effects.md.
Chain (speech): high-pass 80 Hz -> noise reduction (afftdn) -> cut mud 250 Hz -> presence +2 dB at 3 kHz -> de-ess -> gentle compression.
Loudness to the target LUFS stays the job of finish.normalize_loudness (once, on the final mix).
Ducking: windows where the voice speaks (silencedetect) are written into the MUSIC tracks as `duck`; Remotion lowers the volume there."""
import re
from pathlib import Path

from .common import run_cmd, tail

CHAINS = {
    "normal": "highpass=f=80,afftdn=nr=12:nf=-35:tn=1,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3000:t=q:w=1:g=2,"
              "deesser=i=0.4,acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2",
    "light": "highpass=f=70,afftdn=nr=6:nf=-40:tn=1,acompressor=threshold=-22dB:ratio=2:attack=8:release=100:makeup=1",
}
DUCK_GAIN = 0.35         # about -9 dB under speech
SILENCE = "silencedetect=noise=-35dB:d=0.35"
MERGE_GAP_S = 0.4        # shorter pauses do not let the music pump back up


def chain(level="normal"):
    return CHAINS["light" if level == "light" else "normal"]


def clean_audio_file(src, dst, level="normal"):
    rc, _, err = run_cmd(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vn", "-af", chain(level), "-ar", "48000", "-c:a", "pcm_s16le", str(dst)],
                         timeout=1800)
    if rc != 0:
        raise RuntimeError("voice clean-up failed: " + tail(err, 2))
    return dst


def clean_video_audio(src, dst, level="normal"):
    rc, _, err = run_cmd(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-map", "0:v", "-map", "0:a?", "-c:v", "copy", "-af", chain(level),
                          "-c:a", "aac", "-b:a", "320k", str(dst)], timeout=3600)
    if rc != 0:
        raise RuntimeError("voice clean-up failed: " + tail(err, 2))
    return dst


def windows_from_silence(stderr, duration):
    """silencedetect log -> speech windows [(a, b)] (the complement of the silences), short gaps merged."""
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", stderr or "")]
    ends = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", stderr or "")]
    sil = []
    for i, s in enumerate(starts):
        sil.append((max(0.0, s), ends[i] if i < len(ends) else duration))
    out, t = [], 0.0
    for a, b in sil:
        if a - t > 0.05:
            out.append([t, a])
        t = max(t, b)
    if duration - t > 0.05:
        out.append([t, duration])
    merged = []
    for a, b in out:
        if merged and a - merged[-1][1] < MERGE_GAP_S:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(round(a, 3), round(b, 3)) for a, b in merged]


def speech_windows(path):
    from .analyze import probe
    dur = probe(path)["duration_s"]
    _, _, err = run_cmd(["ffmpeg", "-hide_banner", "-i", str(path), "-vn", "-af", SILENCE, "-f", "null", "-"], timeout=900)
    return windows_from_silence(err, dur)


def duck_for(track_at_s, windows_plan_time, gain=DUCK_GAIN):
    """Voice windows in PLAN time -> duck list in the music track's own time."""
    return [{"from_s": round(a - track_at_s, 3), "to_s": round(b - track_at_s, 3), "gain": gain}
            for a, b in windows_plan_time if b - track_at_s > 0]


def prepare_audio(plan, pub, work, hooks=None):
    """Plan copy with: role 'voice' entries cleaned, role 'music' entries given `duck` windows from every voice source
    (voice tracks + video scenes marked props.voice = true). -> (plan, report)."""
    hooks = hooks or {}
    pub = Path(pub)
    rep = {"cleaned": [], "voice_windows": 0, "ducked": 0}
    audio = plan.get("audio") or []
    if not any(a.get("role") in ("voice", "music") for a in audio):
        return plan, rep
    wins = []
    for a in audio:
        if a.get("role") != "voice":
            continue
        f = pub / a["src"]
        if a.get("clean", True) and f.exists():
            out = pub / "fx" / f"{f.stem}.clean.wav"
            if not out.exists():
                (hooks.get("clean_audio") or clean_audio_file)(f, out, a.get("clean_level", "normal"))
            a["src"] = f"fx/{out.name}"
            rep["cleaned"].append(a["src"])
            f = out
        w = (hooks.get("windows") or speech_windows)(f) if f.exists() else []
        shift = float(a.get("at_s", 0.0)) - float(a.get("trim_start_s", 0.0))
        lim_end = float(a.get("duration_s") or 1e9) + float(a.get("at_s", 0.0))
        wins += [(max(float(a.get("at_s", 0.0)), x + shift), min(lim_end, y + shift)) for x, y in w]
    t = 0.0
    for sc in plan.get("scenes", []):
        p = sc.get("props") or {}
        if p.get("voice") and isinstance(p.get("src"), str) and (pub / p["src"]).exists():
            w = (hooks.get("windows") or speech_windows)(pub / p["src"])
            wins += [(t + x, min(t + sc["duration_s"], t + y)) for x, y in w]
        t += sc["duration_s"]
    wins.sort()
    merged = []
    for a, b in wins:
        if merged and a - merged[-1][1] < MERGE_GAP_S:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    rep["voice_windows"] = len(merged)
    for a in audio:
        if a.get("role") == "music":
            a["duck"] = duck_for(float(a.get("at_s", 0.0)), merged, a.get("duck_gain", DUCK_GAIN))
            rep["ducked"] += 1
    return plan, rep
