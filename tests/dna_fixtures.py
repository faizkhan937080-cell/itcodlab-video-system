"""Valid v2 DNA examples for tests (small but complete)."""


def _conf(keys, tag="measured"):
    return {k: tag for k in keys}


def editing_dna(job_id):
    return {"type": "editing", "schema_version": 2, "source": {"job_id": job_id},
            "format": {"width": 1916, "height": 1078, "fps": 30.0, "duration_s": 58.3, "orientation": "landscape"},
            "cut_rhythm": {"asl_s": 3.644, "median_shot_s": 3.667, "std_shot_s": 1.465, "min_shot_s": 1.2,
                           "max_shot_s": 7.6, "cuts_per_min": 15.44, "pattern": "steady hard cuts",
                           "pace_curve": [{"part": "opening", "cuts_per_min": 20}, {"part": "middle", "cuts_per_min": 14},
                                          {"part": "closing", "cuts_per_min": 12}]},
            "shots": {"scale_mix": {"ms": 0.5, "cu": 0.3, "ws": 0.2}},
            "transitions": [{"type": "hard_cut", "share": 1.0}],
            "motion": {"camera": {"moves": ["static", "slow pan"], "intensity": "slow"}, "elements": {"easing": "ease-out"}},
            "text": {"present": True},
            "color": {"palette": [{"hex": "#0A070B", "share": 0.07}, {"hex": "#110E12", "share": 0.05},
                                  {"hex": "#32343A", "share": 0.04}],
                      "grade": {"look": "dark moody", "contrast": "medium", "temperature": "cool"}},
            "layout": {"orientation": "landscape"},
            "recipe": {"remotion_templates": ["image", "kinetic_text"], "typical_scene_s": 3.6},
            "evidence": [{"claim": "all cuts hard", "scenes": [2, 3]}, {"claim": "dark palette", "scenes": [14]},
                         {"claim": "text cards", "t": [3.9, 6.0]}],
            "confidence": {"format": "measured", "cut_rhythm": "measured", "shots": "judged", "transitions": "measured",
                           "motion": "judged", "text": "judged", "color": "measured", "layout": "measured",
                           "recipe": "estimated"}}


def scripting_dna(job_id, coverage=1.0, complete=True, wpm=190.0, structure_tag="judged"):
    return {"type": "scripting", "schema_version": 2, "source": {"job_id": job_id},
            "transcript_basis": {"coverage_ratio": coverage, "complete": complete},
            "framework": {"name": "hook-demo-cta"},
            "hook": {"kind": "result-promise", "duration_s": 8.0, "first_words": "ab aap bhi", "time_to_value_s": 3.0},
            "structure": [{"beat": "hook", "purpose": "promise", "start_s": 0, "end_s": 6, "share": 0.1},
                          {"beat": "demo", "purpose": "show", "start_s": 6, "end_s": 50, "share": 0.8},
                          {"beat": "cta", "purpose": "ask", "start_s": 50, "end_s": 58, "share": 0.1}],
            "voice": {"person": "second-person", "register": "casual", "energy": "high"},
            "language": {"primary": "hinglish", "script": "mixed"},
            "lexicon": {"signature_phrases": ["edit with claude"]},
            "pacing": {"words_per_min_speaking": wpm, "speech_ratio": 0.9, "sentence_words_mean": 7.0},
            "retention": {"open_loops": 1, "rehooks_at_s": [20.0]},
            "cta": {"type": "comment-keyword", "placement_s": 52.0, "repeats": 1},
            "evidence": [{"claim": "promise first", "quote": "ab aap bhi", "t": [0, 3]},
                         {"claim": "series naming", "quote": "episode one", "t": [3, 6]},
                         {"claim": "cta", "quote": "comment karo", "t": [52, 56]}],
            "confidence": {"transcript_basis": "measured", "framework": structure_tag, "hook": "measured",
                           "structure": structure_tag, "voice": structure_tag, "language": "measured",
                           "lexicon": structure_tag, "pacing": "measured", "retention": structure_tag,
                           "cta": structure_tag}}


def sound_dna(job_id):
    return {"type": "sound", "schema_version": 2, "source": {"job_id": job_id},
            "loudness": {"integrated_lufs": -16.2, "true_peak_dbtp": -1.5},
            "tempo": {"bpm": 103.4}, "beat_sync": {"share_within_80ms": 0.733, "cuts_checked": 15},
            "speech": {"speech_ratio": 0.9}, "silence": {"share": 0.0},
            "mix": {"voice_over_music": "voice dominant"},
            "evidence": [{"claim": "bed under voice", "t": [0, 58]}, {"claim": "no silence", "t": [0, 58]},
                         {"claim": "beat cuts", "scenes": [2, 3]}],
            "confidence": {"loudness": "measured", "tempo": "measured", "beat_sync": "measured",
                           "speech": "measured", "silence": "measured", "mix": "judged"}}


SCRIPT_METRICS = {"available": True, "coverage_ratio": 1.0, "complete": True, "words_per_min_speaking": 190.0,
                  "speech_ratio": 0.9, "sentences": {"words_mean": 7.0}}


def fit_editing(dna, summary):
    v, c = summary["video"], summary["cut_rhythm"]
    dna["format"].update(width=v["width"], height=v["height"], fps=v["fps"], duration_s=v["duration_s"])
    dna["cut_rhythm"].update(asl_s=c["shot_length_s"]["mean"], median_shot_s=c["shot_length_s"]["median"],
                             min_shot_s=c["shot_length_s"]["min"], max_shot_s=c["shot_length_s"]["max"],
                             cuts_per_min=c["cuts_per_min"])
    dna["cut_rhythm"].pop("beat_synced_share", None)
    return dna
