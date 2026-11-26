"""Number check that sound effects are really in a rendered video: loudness jump at every sfx cue time + music bed present.
Run: python -m scripts.audiocheck <video.mp4> <plan.json>. Claude never listens; this prints numbers only."""
import json
import math
import subprocess
import sys

import numpy as np

from . import sfx


def rms_db(x):
    return 20 * math.log10(max(float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0, 1e-6))


def run(video, plan_path):
    sr = 16000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    y = np.frombuffer(raw, dtype=np.float32)
    plan = json.loads(open(plan_path, encoding="utf-8").read())
    cues = sfx.plan_cues(plan)
    hits, rows = 0, []
    for c in cues:
        t = c["t"]
        a = y[int(max(0, t - 0.35) * sr): int(max(0, t - 0.03) * sr)]
        b = y[int(t * sr): int((t + 0.3) * sr)]
        jump = rms_db(b) - rms_db(a)
        ok = jump >= 1.5
        hits += ok
        rows.append((round(t, 2), c["kind"], round(jump, 1), ok))
    seconds = len(y) / sr
    quiet = sum(1 for i in range(int(seconds)) if rms_db(y[i * sr:(i + 1) * sr]) < -60)
    print(json.dumps({"seconds": round(seconds, 1), "overall_db": round(rms_db(y), 1), "silent_seconds": quiet,
                      "cues": len(cues), "cues_with_loudness_jump": hits, "weak": [r for r in rows if not r[3]]}, indent=1))


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
