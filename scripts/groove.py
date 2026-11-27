"""Own upbeat bed (free, no licence, no network): 143 bpm, soft kick + hats + warm plucked chords + bass. numpy + ffmpeg only.
Made when the music library has no 'groove-*' track (same rule as ambient.py). Deterministic."""
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 143.0
# Am - F - C - G (pop minor loop), root notes in Hz and chord tones
CHORDS = [(110.0, [220.0, 261.63, 329.63]), (87.31, [174.61, 220.0, 261.63]), (130.81, [196.0, 261.63, 329.63]), (98.0, [196.0, 246.94, 293.66])]


def _env(n, a=0.005, d=0.25):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def _pluck(f, n):
    t = np.arange(n) / SR
    y = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 2, 3)) * 0.33
    return y * _env(n, 0.004, 0.22)


def make(out_path, seconds=60):
    beat = 60.0 / BPM
    total = int(seconds * SR)
    out = np.zeros(total + SR)
    rng = np.random.default_rng(7)
    nbeats = int(seconds / beat)
    for b in range(nbeats):
        t0 = int(b * beat * SR)
        bar = (b // 4) % 4
        # kick on every beat (soft)
        n = int(0.22 * SR)
        tt = np.arange(n) / SR
        kick = np.sin(2 * np.pi * (48 + 90 * np.exp(-tt * 28)) * tt) * np.exp(-tt * 13) * 0.55
        out[t0:t0 + n] += kick
        # off-beat hat
        h0 = t0 + int(beat * 0.5 * SR)
        nh = int(0.05 * SR)
        hat = rng.standard_normal(nh) * np.exp(-np.arange(nh) / SR * 70) * 0.10
        hat = np.diff(np.concatenate([[0], hat]))
        out[h0:h0 + nh] += hat
        # clap-ish snare on 2 and 4
        if b % 2 == 1:
            ns = int(0.12 * SR)
            sn = rng.standard_normal(ns) * np.exp(-np.arange(ns) / SR * 35) * 0.13
            out[t0:t0 + ns] += np.diff(np.concatenate([[0], sn])) * 2.0
        root, tones = CHORDS[bar]
        # bass on beat 1 and the 'and' of 3
        if b % 4 in (0, 2):
            nb = int(beat * 1.5 * SR)
            out[t0:t0 + nb] += np.sin(2 * np.pi * root * np.arange(nb) / SR) * _env(nb, 0.01, 0.5) * 0.30
        # chord stabs on off-beats 8th
        if b % 2 == 0:
            for sub in (0.5, 1.5):
                s0 = t0 + int(beat * sub * SR)
                ns = int(0.35 * SR)
                for f in tones:
                    out[s0:s0 + ns] += _pluck(f, ns) * 0.05
    y = out[:total]
    y = np.tanh(y * 1.3) * 0.85
    fade = int(2 * SR)
    y[:int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
    y[-fade:] *= np.linspace(1, 0, fade)
    st = np.stack([y, np.roll(y, 40)], 1)
    pcm = (np.clip(st, -1, 1) * 32767).astype("<i2")
    with tempfile.TemporaryDirectory() as td:
        w = Path(td) / "g.wav"
        with wave.open(str(w), "wb") as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(SR)
            f.writeframes(pcm.tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(w), "-b:a", "160k", str(out_path)], check=True, timeout=120)
    return str(out_path)
