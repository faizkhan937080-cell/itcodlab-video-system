"""After a render: (1) bring the loudness to the target, (2) measure OUR video with the same scripts and compare it
with the DNA it was made from (closed loop). Never raises: a problem here is reported, it does not kill the render.
"""
import json
import shutil
from pathlib import Path

from .common import log, run_cmd, tail
from .dna_check import clone_report

TP_LIMIT_DBTP = -1.0   # EBU R128 true-peak ceiling


def target_lufs(plan, dnas):
    if plan.get("audio_target_lufs") is not None:
        return float(plan["audio_target_lufs"])
    sound = dnas.get("sound") or {}
    v = (sound.get("loudness") or {}).get("integrated_lufs")
    return float(v) if v is not None else None


def normalize_loudness(video, target, work):
    """Gain the audio to `target` LUFS (video stream copied, no quality loss), limited to -1 dBTP.
    Returns {"changed": bool, "before": x, "after": y} or {"changed": False, "reason": ...}."""
    from .audio import extract_wav, loudness_ebu
    video, work = Path(video), Path(work)
    wav = extract_wav(video, work / "_norm_in.wav")
    m = loudness_ebu(wav)
    if not m:
        return {"changed": False, "reason": "no audio or too short"}
    gain = round(target - m["integrated_lufs"], 2)
    if abs(gain) < 0.5:
        return {"changed": False, "before": m["integrated_lufs"], "reason": "already within 0.5 LU"}
    out = work / (video.stem + "_norm.mp4")
    af = f"volume={gain}dB,alimiter=limit={10 ** (TP_LIMIT_DBTP / 20):.4f}:level=disabled"
    rc, _, err = run_cmd(["ffmpeg", "-y", "-i", str(video), "-map", "0", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
                          "-af", af, str(out)], timeout=1800)
    if rc != 0:
        return {"changed": False, "reason": "ffmpeg failed: " + tail(err, 2)}
    shutil.move(str(out), str(video))
    after = loudness_ebu(extract_wav(video, work / "_norm_out.wav"))
    reached = abs((after.get("integrated_lufs") or -99) - target) <= 1.0
    return {"changed": True, "before": m["integrated_lufs"], "after": after.get("integrated_lufs"), "gain_db": gain,
            "reached_target": reached,
            "note": "" if reached else "peaks hit the -1 dBTP ceiling before the target loudness (very peaky audio)"}


def clone_check(video, plan, dnas, work):
    """Analyse our output with the normal pipeline (no transcript, no review push) and compare per DNA type."""
    from .pack import run_pipeline
    res = {}
    try:
        r = run_pipeline(video, Path(work) / "selfcheck", job_id="selfcheck", mode="both", with_transcript=False)
        summary = json.loads((r["pack"] / "metrics_summary.json").read_text(encoding="utf-8"))
        for t in ("editing", "sound"):
            if dnas.get(t):
                res[t] = clone_report(t, dnas[t], summary)
        res["summary_audit_pass"] = bool((summary.get("audit") or {}).get("pass"))
    except Exception as e:  # noqa: BLE001
        log(f"clone check skipped: {type(e).__name__}: {e}")
        res["error"] = f"{type(e).__name__}: {e}"[:200]
    return res
