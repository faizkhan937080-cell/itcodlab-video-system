"""Quality check of a finished video, by numbers only (rules: rulebooks/16-pro-editing.md). Two parts:
- plan checks (before/after render): visual-change cadence, hook in the first seconds, captions present when someone speaks.
- file checks (after render): black frames, dead air, loudness + true peak, constant frame rate, captions vs speech.
Findings are {level: 'fail'|'warn'|'info', code, msg}. Nothing here changes the video; hints say what to change in the plan."""
import re

from .common import limits, run_cmd

CADENCE_MAX_S = 5.0        # something visible changes at least this often (cut, zoom, overlay, text)
HOOK_MAX_FIRST_SCENE_S = 3.5
DEAD_AIR_S = 0.8
CAPTION_COVERAGE_MIN = 0.85
LUFS_TOL = 1.5
TP_MAX = -1.0
DEFAULT_LUFS = -14.0       # Reels/Shorts/TikTok normalisation reference


def f(level, code, msg):
    return {"level": level, "code": code, "msg": msg}


# ------------------------------------------------------------------ plan checks
def change_times(plan):
    """Seconds (timeline) where the picture visibly changes: scene starts, zoom keys, overlays starting, caption pages."""
    t, out = 0.0, set()
    for sc in plan.get("scenes", []):
        out.add(round(t, 3))
        for k in sc.get("zoom") or []:
            if abs(k.get("scale", 1) - 1) > 0.02:
                out.add(round(t + k["at_s"], 3))
        for ov in sc.get("overlays") or []:
            out.add(round(t + ov.get("start_s", 0), 3))
        t += sc["duration_s"]
    for c in plan.get("captions") or []:
        out.add(round(c["start_s"], 3))
    return sorted(out), round(t, 3)


def cadence(plan, max_gap=CADENCE_MAX_S):
    ts, total = change_times(plan)
    pts = ts + [total]
    worst, at = 0.0, 0.0
    for a, b in zip(pts, pts[1:]):
        if b - a > worst:
            worst, at = b - a, a
    out = []
    if worst > max_gap:
        out.append(f("warn", "cadence", f"nothing changes on screen for {worst:.1f}s from {at:.1f}s (limit {max_gap}s): add a punch-in, cutaway, text or overlay"))
    return out, {"longest_still_s": round(worst, 2), "starts_at_s": round(at, 2)}


def hook(plan):
    sc = (plan.get("scenes") or [None])[0]
    if not sc:
        return []
    out = []
    if sc["duration_s"] > HOOK_MAX_FIRST_SCENE_S and not sc.get("zoom") and not sc.get("overlays"):
        out.append(f("warn", "hook", f"first scene lasts {sc['duration_s']}s with no movement: the hook must land inside the first 3 s"))
    first_cap = min((c["start_s"] for c in plan.get("captions") or []), default=None)
    has_text = sc["template"] not in ("video", "image", "paper_cutout") or (first_cap is not None and first_cap < 1.5)
    if not has_text:
        out.append(f("info", "hook", "no text or caption in the first 1.5 s: fine if the footage itself is the hook, otherwise add a headline"))
    return out


def plan_checks(plan):
    c, stats = cadence(plan)
    return c + hook(plan), stats


# ------------------------------------------------------------------ file checks
def parse_intervals(stderr, kind):
    """ffmpeg detect log -> [(start, end)]. kind: black | silence | freeze"""
    if kind == "black":
        return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+)\s+black_end:([\d.]+)", stderr or "")]
    key = "silence" if kind == "silence" else "lavfi.freezedetect.freeze"
    starts = [float(x) for x in re.findall(rf"{re.escape(key)}_start:\s*([\d.]+)", stderr or "")]
    ends = [float(x) for x in re.findall(rf"{re.escape(key)}_end:\s*([\d.]+)", stderr or "")]
    return list(zip(starts, ends))


def detect(video, has_audio=True):
    vf = "blackdetect=d=0.25:pix_th=0.10"
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vf", vf]
    if has_audio:
        cmd += ["-af", f"silencedetect=noise=-35dB:d={DEAD_AIR_S}"]
    rc, _, err = run_cmd(cmd + ["-f", "null", "-"], timeout=1800)
    return {"black": parse_intervals(err, "black"), "silence": parse_intervals(err, "silence")}


def overlap(a, b):
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def caption_coverage(plan, speech):
    """Share of speaking time that has a caption on screen (speech = [(start, end)] from the audio)."""
    total = sum(e - s for s, e in speech)
    if total <= 0:
        return None
    caps = [(c["start_s"], c["end_s"]) for c in plan.get("captions") or []]
    covered = sum(min(e - s, sum(overlap((s, e), c) for c in caps)) for s, e in speech)
    return round(covered / total, 3)


def file_checks(video, plan, probe, loud=None, det=None, target_lufs=None, check_measured=False):
    """probe = analyze.probe(video); loud = audio.loudness_ebu(wav) or {}; det = detect(video)."""
    out = []
    dur = probe["duration_s"]
    if det:
        for s, e in det["black"]:
            if s > 0.05 and e < dur - 0.05:
                out.append(f("warn", "black", f"black frames {s:.1f}-{e:.1f}s in the middle of the video"))
            elif s <= 0.05 and e - s > 0.3:
                out.append(f("warn", "black_start", f"video starts with {e - s:.1f}s of black"))
        for s, e in det["silence"]:
            if plan_has_voice(plan) and s > 0.1 and e < dur - 0.1:
                out.append(f("warn", "dead_air", f"dead air {s:.1f}-{e:.1f}s ({e - s:.1f}s of silence)"))
    if loud:
        tgt = DEFAULT_LUFS if target_lufs is None else target_lufs
        if abs(loud["integrated_lufs"] - tgt) > LUFS_TOL:
            out.append(f("warn", "loudness", f"loudness {loud['integrated_lufs']} LUFS, target {tgt} (±{LUFS_TOL})"))
        if loud.get("true_peak_dbtp") is not None and loud["true_peak_dbtp"] > TP_MAX + 0.5:
            out.append(f("warn", "true_peak", f"true peak {loud['true_peak_dbtp']} dBTP is above {TP_MAX}: it can distort after Instagram re-encodes"))
    elif probe.get("has_audio") and loud is not None and check_measured:
        out.append(f("info", "loudness", "loudness not measurable (audio too short?)"))
    if probe.get("vfr"):
        out.append(f("warn", "vfr", "variable frame rate output: audio can drift on some phones"))
    if det and plan.get("captions") is not None:
        speech = complement(det["silence"], dur)
        cov = caption_coverage(plan, speech)
        if cov is not None and cov < CAPTION_COVERAGE_MIN:
            out.append(f("warn", "captions", f"captions cover {cov:.0%} of the speech (want {CAPTION_COVERAGE_MIN:.0%}+): sound-off viewers miss words"))
    elif det and plan_has_voice(plan) and not plan.get("captions"):
        out.append(f("warn", "captions", "someone speaks but there are no captions: most Reels are watched without sound"))
    return out


def plan_has_voice(plan):
    return any(a.get("role") == "voice" for a in plan.get("audio") or []) or any(
        (s.get("props") or {}).get("voice") for s in plan.get("scenes", []))


def complement(silences, duration):
    out, t = [], 0.0
    for s, e in sorted(silences):
        if s - t > 0.05:
            out.append((t, s))
        t = max(t, e)
    if duration - t > 0.05:
        out.append((t, duration))
    return out


def vfr(video):
    rc, out, _ = run_cmd(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,avg_frame_rate", "-of", "csv=p=0", str(video)], timeout=60)
    try:
        a, b = out.strip().split(",")[:2]

        def val(x):
            n, d = x.split("/")
            return float(n) / float(d) if float(d) else 0.0
        return abs(val(a) - val(b)) > 0.05 * max(val(a), 1)
    except Exception:  # noqa: BLE001
        return False


def run(video, plan, work, target_lufs=None, check_loudness=True):
    """Full QA of a rendered file. Never raises."""
    from .analyze import probe
    from .audio import extract_wav, loudness_ebu
    res = {"findings": [], "stats": {}}
    try:
        pf, stats = plan_checks(plan)
        res["stats"]["cadence"] = stats
        p = probe(video)
        p["vfr"] = vfr(video)
        loud = loudness_ebu(extract_wav(video, __import__("pathlib").Path(work) / "_qa.wav")) if p["has_audio"] and check_loudness else {}
        det = detect(video, p["has_audio"])
        res["findings"] = pf + file_checks(video, plan, p, loud, det, target_lufs, check_measured=check_loudness)
        res["stats"]["loudness"] = loud
    except Exception as e:  # noqa: BLE001
        res["error"] = f"{type(e).__name__}: {e}"[:200]
    res["ok"] = not any(x["level"] == "fail" for x in res["findings"]) and "error" not in res
    res["warnings"] = sum(1 for x in res["findings"] if x["level"] == "warn")
    return res
