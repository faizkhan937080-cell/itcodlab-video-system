"""Measurement audit: did the analysis really look at EVERY frame, EVERY minute, EVERY word?

Produces `audit.json` (full, per minute) and a compact `audit` block in metrics_summary.json.
Claude reads the compact block first: any warning means the pack is not good enough for DNA yet.
"""
import math

MIN_COVERAGE = 0.9


def _overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def _words(text):
    return len((text or "").split())


def build(info, frames_n, scenes, clusters, audio_res, transcript):
    dur = float(info["duration_s"])
    step = int(info.get("analysis_step", 1) or 1)
    total = int(info.get("total_frames") or 0)
    warnings = []

    expected = math.ceil(total / step) if total else 0
    frame_cov = round(frames_n / expected, 3) if expected else 0.0
    if frame_cov < 0.98:
        warnings.append(f"only {frame_cov:.0%} of the frames were analysed (step {step})")
    if step > 1:
        warnings.append(f"analysis step is {step}: every {step}th frame only (long video); short cuts can be missed")

    covered = sum(s["duration_s"] for s in scenes)
    timeline_gap = round(abs(covered - dur), 2)
    if timeline_gap > max(0.5, dur * 0.01):
        warnings.append(f"scene timeline differs from video length by {timeline_gap}s")

    ocr_ok = [s for s in scenes if s.get("text") is not None]
    ocr_cov = round(len(ocr_ok) / max(len(scenes), 1), 3)
    if ocr_cov < 1.0:
        warnings.append("OCR did not run on every scene")
    kf_cov = round(sum(1 for s in scenes if s.get("keyframe")) / max(len(scenes), 1), 3)
    if kf_cov < 1.0:
        warnings.append("some scenes have no keyframe")
    reps = {c["rep_scene"] for c in clusters if c.get("in_collage")}
    members = {m for c in clusters for m in c["members"]}
    cluster_cov = round(len(members) / max(len(scenes), 1), 3)
    if cluster_cov < 1.0:
        warnings.append("some scenes are in no cluster")

    segs = (transcript or {}).get("segments") or []
    t_cov = (transcript or {}).get("coverage_ratio")
    has_audio = bool(info.get("has_audio"))
    if has_audio and not segs:
        warnings.append("audio exists but there is no transcript")
    elif has_audio and (t_cov is None or t_cov < MIN_COVERAGE):
        warnings.append(f"transcript covers {t_cov} of the audio (need >= {MIN_COVERAGE})")
    ebu = (audio_res or {}).get("ebu_r128") or {}
    if has_audio and not ebu.get("integrated_lufs"):
        warnings.append("no LUFS measurement (pyloudnorm missing or audio too short)")

    minutes = []
    for m in range(max(1, math.ceil(dur / 60.0))):
        a0, a1 = m * 60.0, min((m + 1) * 60.0, dur)
        span = max(a1 - a0, 1e-6)
        sc = [s for s in scenes if _overlap(s["start_s"], s["end_s"], a0, a1) > 0]
        starts = [s for s in scenes if a0 <= s["start_s"] < a1 and s["start_s"] > 0]
        words = 0.0
        speech = 0.0
        for g in segs:
            ov = _overlap(g["start"], g["end"], a0, a1)
            if ov:
                words += _words(g["text"]) * ov / max(g["end"] - g["start"], 1e-6)
                speech += ov
        motion = {}
        for s in sc:
            k = (s.get("motion") or {}).get("class", "?")
            motion[k] = motion.get(k, 0) + 1
        minutes.append({"minute": m + 1, "from_s": round(a0, 1), "to_s": round(a1, 1), "scenes": len(sc),
                        "cuts": len(starts), "cuts_per_min": round(len(starts) / (span / 60.0), 2),
                        "avg_shot_s": round(sum(_overlap(s["start_s"], s["end_s"], a0, a1) for s in sc) / len(sc), 2) if sc else 0,
                        "words": round(words), "speech_ratio": round(min(speech / span, 1.0), 2),
                        "ocr_scenes": sum(1 for s in sc if s.get("text")), "motion": motion})
        if has_audio and segs and span >= 10 and words == 0:
            warnings.append(f"minute {m + 1}: no words transcribed")

    return {"frames": {"total": total, "expected_analysed": expected, "analysed": frames_n, "step": step,
                       "coverage": frame_cov},
            "scenes": {"count": len(scenes), "timeline_gap_s": timeline_gap, "keyframe_coverage": kf_cov,
                       "cluster_coverage": cluster_cov, "in_collage": len(reps), "ocr_coverage": ocr_cov},
            "transcript_coverage": t_cov, "lufs_measured": bool(ebu.get("integrated_lufs")),
            "per_minute": minutes, "warnings": warnings, "pass": not warnings}
