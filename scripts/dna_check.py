"""Accuracy gate for DNA candidates: schema + honesty rules + cross-check against the measured numbers.

A candidate is refused (with a short list of problems) when:
  1. it does not match the v2 schema,
  2. a top-level section has no confidence tag, or is tagged `measured` but its numbers differ from the
     metrics summary the scripts produced (so Claude cannot mistype or invent a measured number),
  3. scripting is built on an incomplete transcript (coverage < 0.9) but claims `measured` structure/cta.
Standards: rulebooks/07-standards-editing.md, 08-standards-scripting.md, 09-standards-sound.md.
"""
from .dna import validate

SKIP = {"type", "schema_version", "source", "evidence", "confidence", "corpus", "notes"}
REL_TOL, ABS_TOL = 0.02, 0.06
_TOL = [REL_TOL, ABS_TOL]
CLONE_REL, CLONE_ABS = 0.10, 0.5   # how close an output must be to the DNA it was made from


def _close(a, b):
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return abs(a - b) <= max(_TOL[1], _TOL[0] * abs(b))


def _get(d, path):
    for k in path.split("."):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def _cmp(problems, dna, dpath, summary, spath, label=None):
    want, have = _get(summary, spath), _get(dna, dpath)
    if want is None or have is None:
        return
    if not _close(have, want):
        problems.append(f"{label or dpath} = {have} but measured {spath} = {want}")


def crosscheck(dna_type, dna, summary, tol=None):
    """Compare measured fields with metrics_summary.json (dict). Returns problems."""
    _TOL[0], _TOL[1] = tol or (REL_TOL, ABS_TOL)
    try:
        return _crosscheck(dna_type, dna, summary)
    finally:
        _TOL[0], _TOL[1] = REL_TOL, ABS_TOL


def _crosscheck(dna_type, dna, summary):
    p = []
    if not summary:
        return p
    conf = dna.get("confidence", {})
    if dna_type == "editing":
        _cmp(p, dna, "format.width", summary, "video.width")
        _cmp(p, dna, "format.height", summary, "video.height")
        _cmp(p, dna, "format.fps", summary, "video.fps")
        _cmp(p, dna, "format.duration_s", summary, "video.duration_s")
        _cmp(p, dna, "cut_rhythm.cuts_per_min", summary, "cut_rhythm.cuts_per_min")
        _cmp(p, dna, "cut_rhythm.asl_s", summary, "cut_rhythm.shot_length_s.mean")
        _cmp(p, dna, "cut_rhythm.median_shot_s", summary, "cut_rhythm.shot_length_s.median")
        _cmp(p, dna, "cut_rhythm.min_shot_s", summary, "cut_rhythm.shot_length_s.min")
        _cmp(p, dna, "cut_rhythm.max_shot_s", summary, "cut_rhythm.shot_length_s.max")
        _cmp(p, dna, "cut_rhythm.beat_synced_share", summary, "audio.cut_beat_sync.share_within_80ms")
    elif dna_type == "sound":
        _cmp(p, dna, "tempo.bpm", summary, "audio.bpm")
        _cmp(p, dna, "beat_sync.share_within_80ms", summary, "audio.cut_beat_sync.share_within_80ms")
        _cmp(p, dna, "beat_sync.cuts_checked", summary, "audio.cut_beat_sync.cuts_checked")
        _cmp(p, dna, "loudness.integrated_lufs", summary, "audio.ebu_r128.integrated_lufs")
        _cmp(p, dna, "loudness.true_peak_dbtp", summary, "audio.ebu_r128.true_peak_dbtp")
        _cmp(p, dna, "loudness.lra_lu", summary, "audio.ebu_r128.lra_lu")
        _cmp(p, dna, "silence.share", summary, "audio.silence_share")
        _cmp(p, dna, "mix.voice_minus_music_lu", summary, "audio.stems.voice_minus_music_lu")
        _cmp(p, dna, "speech.speech_ratio", summary, "script_metrics.speech_ratio")
        if not _get(summary, "audio.ebu_r128.integrated_lufs") and conf.get("loudness") == "measured":
            p.append("loudness tagged measured but the pack has no ebu_r128 numbers (re-run analysis)")
    elif dna_type == "scripting":
        sm = summary.get("script_metrics") or {}
        if not sm.get("available"):
            p.append("pack has no script_metrics (no transcript): scripting DNA cannot be measured")
            return p
        _cmp(p, dna, "pacing.words_per_min_speaking", sm, "words_per_min_speaking")
        _cmp(p, dna, "pacing.words_per_min_overall", sm, "words_per_min_overall")
        _cmp(p, dna, "pacing.speech_ratio", sm, "speech_ratio")
        _cmp(p, dna, "pacing.sentence_words_mean", sm, "sentences.words_mean")
        _cmp(p, dna, "pacing.pause_mean_s", sm, "pauses.mean_s")
        _cmp(p, dna, "pacing.questions_per_min", sm, "questions_per_min")
        _cmp(p, dna, "transcript_basis.coverage_ratio", sm, "coverage_ratio")
        complete = bool(sm.get("complete"))
        if bool(_get(dna, "transcript_basis.complete")) != complete:
            p.append(f"transcript_basis.complete must be {complete} (measured coverage {sm.get('coverage_ratio')})")
        if not complete:
            for sec in ("structure", "cta", "retention", "voice", "lexicon"):
                if conf.get(sec) in ("measured", "judged"):
                    p.append(f"{sec} cannot be {conf[sec]} on an incomplete transcript (coverage "
                             f"{sm.get('coverage_ratio')}); tag it estimated or re-run the analysis")
    return p


def check(dna_type, dna, summary=None):
    """Return a list of problems; empty = candidate passes."""
    errs = validate(dna_type, dna)
    if errs:
        return errs
    problems = []
    conf = dna.get("confidence", {})
    for sec in dna:
        if sec not in SKIP and sec not in conf:
            problems.append(f"confidence missing for section '{sec}'")
    for sec, tag in conf.items():
        if sec not in dna:
            problems.append(f"confidence names unknown section '{sec}'")
    problems += crosscheck(dna_type, dna, summary)
    return problems


def unflatten(targets):
    """corpus `targets` ({'pacing.words_per_min_speaking': 181.0, ...}) -> nested dict (plain paths only)."""
    out = {}
    for path, val in targets.items():
        if "[" in path:
            continue
        d = out
        keys = path.split(".")
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = val
    return out


def clone_report(dna_type, target, output_summary, rel=CLONE_REL, abs_=CLONE_ABS):
    """Closed loop: analyse OUR rendered video with the same scripts, then compare with the DNA it was made from.
    `target` = a v2 DNA dict, or a corpus dict (its `targets` are used). Returns {"pass", "differences"}.
    Resolution is checked too: output size must equal the source/target size (format.width/height)."""
    if target.get("type") == "corpus":
        target = unflatten(target.get("targets", {}))
    diffs = crosscheck(dna_type, target, output_summary, tol=(rel, abs_))
    diffs = [d for d in diffs if "transcript_basis" not in d]
    return {"pass": not diffs, "differences": diffs}
