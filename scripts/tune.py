"""Tuning hints: when our rendered video differs from the DNA it was made from, say WHICH plan number to change and by
how much (numbers only, from the same measurements). Claude/worker applies them in the next plan version; nothing here
re-renders by itself. Standards: rulebooks/07-standards-editing.md, 09-standards-sound.md.
"""
from .dna_check import unflatten

REL = 0.10


def _g(d, path):
    for k in path.split("."):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def _off(a, b, rel=REL):
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return b != 0 and abs(a - b) / abs(b) > rel


def tune_hints(dna_type, target, summary):
    """-> list of {"param", "change", "why"}; empty when the output already matches. `target` = DNA or corpus dict."""
    if target.get("type") == "corpus":
        target = unflatten(target.get("targets", {}))
    out = []
    if dna_type == "editing":
        w, h = _g(summary, "video.width"), _g(summary, "video.height")
        tw, th = _g(target, "format.width"), _g(target, "format.height")
        if None not in (w, h, tw, th) and (int(w), int(h)) != (int(tw), int(th)):
            out.append({"param": "plan.output", "change": {"width": int(tw), "height": int(th)},
                        "why": f"output is {w}x{h}, source/target is {tw}x{th}"})
        fps, tfps = _g(summary, "video.fps"), _g(target, "format.fps")
        if _off(fps, tfps, 0.02):
            out.append({"param": "plan.fps", "change": round(float(tfps), 3), "why": f"fps {fps} vs target {tfps}"})
        cpm, tcpm = _g(summary, "cut_rhythm.cuts_per_min"), _g(target, "cut_rhythm.cuts_per_min")
        if _off(cpm, tcpm):
            f = round(float(cpm) / float(tcpm), 2)
            out.append({"param": "scenes[].duration_s", "change": f"x{f}",
                        "why": f"cuts/min {cpm} vs target {tcpm}: {'shorter' if f < 1 else 'longer'} scenes"})
        share, tshare = _g(summary, "audio.cut_beat_sync.share_within_80ms"), _g(target, "cut_rhythm.beat_synced_share")
        bpm = _g(summary, "audio.bpm")
        if tshare is not None and share is not None and float(share) < float(tshare) - 0.1 and bpm:
            out.append({"param": "scenes[].start", "change": f"snap to {round(60 / float(bpm), 3)} s beat grid",
                        "why": f"beat-synced cuts {share} vs target {tshare}"})
    elif dna_type == "sound":
        lufs, tl = _g(summary, "audio.ebu_r128.integrated_lufs"), _g(target, "loudness.integrated_lufs")
        if lufs is not None and tl is not None and abs(float(lufs) - float(tl)) > 1.0:
            out.append({"param": "plan.audio_target_lufs", "change": float(tl),
                        "why": f"loudness {lufs} LUFS vs target {tl}"})
        bpm, tb = _g(summary, "audio.bpm"), _g(target, "tempo.bpm")
        if _off(bpm, tb, 0.05):
            out.append({"param": "plan.audio[].track", "change": f"music near {tb} BPM",
                        "why": f"tempo {bpm} vs target {tb}"})
    return out
