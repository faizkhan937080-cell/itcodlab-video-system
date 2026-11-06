"""Full analysis pipeline + the small 'pack' Claude reads (collages + metrics_summary.json)."""
import json
from pathlib import Path

import numpy as np

from . import audio as audio_mod
from . import audit as audit_mod
from . import script_metrics
from .analyze import analyze_video, probe
from .collage import build_collages, capacity, pick_layout
from .common import json_default, limits, log, now_iso, to_native, write_json_local
from .dedup import dedup


def _stats(vals):
    if not vals:
        return {}
    a = np.array(vals, dtype=float)
    return {"mean": round(float(a.mean()), 3), "median": round(float(np.median(a)), 3),
            "std": round(float(a.std()), 3), "min": round(float(a.min()), 3), "max": round(float(a.max()), 3)}


def _overall_palette(scenes, k=6):
    acc = {}
    for s in scenes:
        for c in s.get("colors", []):
            acc[c["hex"]] = acc.get(c["hex"], 0) + c["share"] * s["duration_s"]
    tot = sum(acc.values()) or 1
    return [{"hex": h, "share": round(v / tot, 3)} for h, v in sorted(acc.items(), key=lambda x: -x[1])[:k]]


def _unique_text(segments):
    """Transcript for Claude: a repeated line appears once, with (xN) when it was said N times."""
    from .script_metrics import dedup_sentences
    return " | ".join(u["text"] + (f" (x{u['count']})" if u["count"] > 1 else "")
                      for u in dedup_sentences([s["text"] for s in segments]))


def build_summary(info, scenes, clusters, dedup_report, collage_idx, audio_res, transcript, lim, script_m=None, voice_res=None):
    durs = [s["duration_s"] for s in scenes]
    trans = {}
    for s in scenes[1:]:
        trans[s["transition_in"]] = trans.get(s["transition_in"], 0) + 1
    motion = {}
    for s in scenes:
        motion[s["motion"]["class"]] = motion.get(s["motion"]["class"], 0) + 1
    minutes = max(info["duration_s"] / 60.0, 1e-6)
    rows = [{"id": s["id"], "t": [s["start_s"], s["end_s"]], "in": s["transition_in"],
             "motion": s["motion"]["class"], "pan": s["motion"]["pan"], "zoom": s["motion"]["zoom_trend"],
             "cluster": s.get("cluster"), "colors": [c["hex"] for c in s.get("colors", [])[:2]],
             "text": " ".join(t["text"] for t in (s.get("text") or []))[:60] or None}
            for s in scenes]
    summary = {
        "generated": now_iso(),
        "video": {k: info[k] for k in ("width", "height", "fps", "duration_s", "has_audio",
                                       "total_frames", "analysis_step")},
        "cut_rhythm": {"scene_count": len(scenes), "cuts_per_min": round((len(scenes) - 1) / minutes, 2),
                       "shot_length_s": _stats(durs), "transitions": trans},
        "motion_classes": motion,
        "palette": _overall_palette(scenes),
        "brightness": _stats([s["brightness"] for s in scenes]),
        "saturation": _stats([s["saturation"] for s in scenes]),
        "ocr": "unavailable" if all(s.get("text") is None for s in scenes) else "available",
        "dedup": dedup_report,
        "clusters": clusters,
        "collages": [{"file": c["file"], "tiles": len(c["tiles"])} for c in collage_idx["collages"]],
        "scenes": rows,
        "audio": audio_res,
    }
    if transcript.get("available"):
        n = lim["pack"]["transcript_chars_in_summary"]
        summary["transcript"] = {"language": transcript["language"], "coverage_ratio": transcript.get("coverage_ratio"),
                                 "text": _unique_text(transcript["segments"])[:n]}
        if transcript.get("alt_english"):
            summary["transcript"]["english_pass"] = {"coverage_ratio": transcript["alt_english"].get("coverage_ratio"),
                                                      "text": transcript["alt_english"]["text"][:n]}
    else:
        summary["transcript"] = {"available": False}
    summary["script_metrics"] = script_m or {"available": False}
    if voice_res is not None:
        from .voice_dna import compact, finite
        summary["voice"] = finite(compact(voice_res))
    # keep it small: drop per-scene rows first, then trim clusters
    cap = lim["pack"]["max_summary_kb"] * 1024
    if len(json.dumps(summary, default=json_default)) > cap:
        summary["scenes"] = rows[:10] + [{"note": f"{len(rows) - 20} rows omitted (see scenes.json)"}] + rows[-10:]
    if len(json.dumps(summary, default=json_default)) > cap:
        summary["scenes"] = "omitted: see scenes.json"
    if len(json.dumps(summary, default=json_default)) > cap:
        summary["clusters"] = clusters[:60]
    return to_native(summary)


def _voice(wav, transcript):
    """Voice micro-analysis (scripts/voice_dna.py). Never fails the job."""
    from . import voice_dna
    v = voice_dna.finite(voice_dna.analyse(wav, transcript))
    log(voice_dna.summary_line(v))
    return v


def _listen(video, wav, lim):
    """The ears (scripts/listen.py): named music + sound events. Never fails the job: any problem = 'not found'."""
    import json
    import os
    from . import listen
    meta = {}
    info = Path(video).parent / "source.info.json"
    if info.exists():
        try:
            meta = json.loads(info.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            meta = {}
    scorer = None
    if lim["analysis"].get("listen_sound_events"):
        try:
            scorer = listen.clap_scorer()
        except Exception:  # noqa: BLE001  (model not installed here, e.g. local test box)
            scorer = None
    return listen.listen(wav, meta, os.environ.get("ACOUSTID_KEY"), scorer)


def _grade_look(video, out_root, lim):
    """The reel's colour look (grade.json): what 'make it like this reel' matches. Never fails the job."""
    import tempfile
    if not lim["analysis"].get("grade_look", True):
        return
    try:
        from . import grade_video
        with tempfile.TemporaryDirectory() as tmp:
            res = grade_video.reference_stats(video, tmp, lim)
    except Exception as e:  # noqa: BLE001
        res = {"usable": False, "reason": f"{type(e).__name__}: {e}"[:200]}
    write_json_local(Path(out_root) / "grade.json", res)


def _ears(video, out_root, lim, with_transcript):
    """Everything that listens and does not need the picture: wav, transcript, music/sound names, voice. Own thread."""
    wav = audio_mod.extract_wav(video, out_root / "audio.wav")
    transcript = audio_mod.transcribe(wav) if with_transcript else {"available": False}
    write_json_local(out_root / "transcript.json", transcript)
    (out_root / "transcript.txt").write_text(script_metrics.transcript_txt(transcript), encoding="utf-8")
    write_json_local(out_root / "listen.json", _listen(video, wav, lim))
    voice = _voice(wav, transcript)
    write_json_local(out_root / "voice.json", voice)
    return wav, transcript, voice


def _video_side(video, out_root, lim):
    info, frames, scenes, fps = analyze_video(video, out_root, lim)
    layout_key, layout = pick_layout(info["width"], info["height"], lim, len(scenes))
    clusters, rep = dedup(scenes, capacity(layout, lim), lim)
    write_json_local(out_root / "clusters.json", {"report": rep, "clusters": clusters})
    write_json_local(out_root / "scenes.json",
                     [{k: v for k, v in s.items() if not k.startswith("_")} for s in scenes])
    pack = out_root / "pack"
    idx = build_collages(video, pack, scenes, clusters, info, fps, lim)
    write_json_local(out_root / "collage_index.json", idx)
    return info, frames, scenes, fps, clusters, rep, pack, idx


def run_pipeline(video, out_root, job_id="local", mode="both", with_transcript=True):
    """Everything between 'video file' and 'pack ready'. Returns dict of paths.
    The ears (transcript, music names, voice) run in a second thread while the picture is analysed: same results, less waiting
    (analysis.parallel false = one after the other)."""
    from concurrent.futures import ThreadPoolExecutor
    lim = limits()
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    has_audio = probe(video)["has_audio"] and mode in ("audio", "both")
    wav, transcript, voice, audio_res = None, {"available": False}, None, {"has_audio": False}
    if has_audio and lim["analysis"].get("parallel", True):
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_ears, video, out_root, lim, with_transcript)
            side = _video_side(video, out_root, lim)
            wav, transcript, voice = fut.result()
    else:
        side = _video_side(video, out_root, lim)
        if has_audio:
            wav, transcript, voice = _ears(video, out_root, lim, with_transcript)
    info, frames, scenes, fps, clusters, rep, pack, idx = side
    if wav is not None:
        audio_res = audio_mod.analyze_audio(wav, [s["start_s"] for s in scenes[1:]])
        write_json_local(out_root / "audio.json", audio_res)
    if job_id != "selfcheck":
        _grade_look(video, out_root, lim)
    audit = audit_mod.build(info, len(frames), scenes, clusters, audio_res, transcript)
    write_json_local(out_root / "audit.json", audit)
    script_m = to_native(script_metrics.compute(transcript, info["duration_s"]))
    write_json_local(out_root / "script_metrics.json", script_m)
    summary = build_summary(info, scenes, clusters, rep, idx, audio_res, transcript, lim, script_m, voice)
    summary["audit"] = {k: audit[k] for k in ("frames", "scenes", "transcript_coverage", "lufs_measured", "warnings", "pass")}
    summary["audit"]["per_minute"] = audit["per_minute"][:30]
    write_json_local(pack / "metrics_summary.json", summary)
    manifest = {"job_id": job_id, "mode": mode, "created": now_iso(),
                "files": sorted(p.name for p in pack.iterdir()),
                "collage_count": idx["count"], "collage_max": idx["max_allowed"],
                "summary_bytes": (pack / "metrics_summary.json").stat().st_size,
                "collage_bytes": sum((pack / c["file"]).stat().st_size for c in idx["collages"])}
    write_json_local(pack / "manifest.json", manifest)
    log(f"pack ready: {idx['count']} collage(s), summary {manifest['summary_bytes']} bytes")
    return {"out_root": out_root, "pack": pack, "info": info, "scenes": scenes,
            "clusters": clusters, "dedup_report": rep, "manifest": manifest}
