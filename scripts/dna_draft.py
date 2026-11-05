"""Pre-fill the MEASURED parts of a DNA candidate from the pack, so Claude only adds the judged parts.
Saves tokens and removes typing mistakes. The result is NOT valid yet: Claude completes the missing sections
(shots, motion, text, recipe, voice, structure, evidence, ...), tags confidence, then runs `./run dna-check`.
"""
ORIENT = {True: "portrait", False: "landscape"}


def _src(job_id, link, creator):
    s = {"job_id": job_id}
    if link:
        s["link"] = link
    if creator:
        s["creator"] = creator
    return s


def _pace_curve(scenes, duration):
    if not isinstance(scenes, list) or not duration:
        return None
    starts = [r["t"][0] for r in scenes if isinstance(r, dict) and "t" in r][1:]
    third = duration / 3.0
    out = []
    for i, name in enumerate(("opening", "middle", "closing")):
        n = sum(1 for t in starts if i * third <= t < (i + 1) * third or (i == 2 and t >= 2 * third))
        out.append({"part": name, "cuts_per_min": round(n / (third / 60.0), 2)})
    return out


def draft_editing(sm, job_id, link="", creator=""):
    v, c = sm["video"], sm["cut_rhythm"]
    sl = c["shot_length_s"]
    d = {"type": "editing", "schema_version": 2, "source": _src(job_id, link, creator),
         "format": {"width": v["width"], "height": v["height"], "fps": v["fps"], "duration_s": v["duration_s"],
                    "orientation": "square" if abs(v["width"] - v["height"]) < 0.1 * v["width"]
                    else ORIENT[v["height"] > v["width"]], "aspect": f"{v['width']}:{v['height']}"},
         "cut_rhythm": {"asl_s": sl["mean"], "median_shot_s": sl["median"], "std_shot_s": sl["std"],
                        "min_shot_s": sl["min"], "max_shot_s": sl["max"], "cuts_per_min": c["cuts_per_min"]}}
    pc = _pace_curve(sm.get("scenes"), v["duration_s"])
    if pc:
        d["cut_rhythm"]["pace_curve"] = pc
    sync = (sm.get("audio") or {}).get("cut_beat_sync")
    if sync:
        d["cut_rhythm"]["beat_synced_share"] = sync["share_within_80ms"]
    tr = c.get("transitions") or {}
    tot = sum(tr.values()) or 1
    known = {"hard_cut", "dissolve", "fade_black", "wipe", "slide", "glitch"}
    d["transitions"] = [{"type": k if k in known else "other", "share": round(n / tot, 3)} for k, n in tr.items()]
    d["color"] = {"palette": sm.get("palette", [])[:6],
                  "grade": {"saturation_mean": sm["saturation"]["mean"], "brightness_mean": sm["brightness"]["mean"]}}
    d["confidence"] = {"format": "measured", "cut_rhythm": "measured", "transitions": "measured", "color": "measured"}
    return d


def draft_sound(sm, job_id, link="", creator=""):
    a = sm.get("audio") or {}
    sync, ebu = a.get("cut_beat_sync") or {}, a.get("ebu_r128") or {}
    d = {"type": "sound", "schema_version": 2, "source": _src(job_id, link, creator),
         "loudness": {k: ebu[k] for k in ("integrated_lufs", "true_peak_dbtp", "lra_lu", "short_term_max_lufs") if k in ebu},
         "tempo": {"bpm": a.get("bpm")},
         "beat_sync": {"share_within_80ms": sync.get("share_within_80ms"), "cuts_checked": sync.get("cuts_checked"),
                       "median_offset_s": sync.get("median_offset_s")},
         "silence": {"share": a.get("silence_share")},
         "confidence": {"loudness": "measured" if ebu else "unknown", "tempo": "measured",
                        "beat_sync": "measured", "silence": "measured"}}
    st = a.get("stems") or {}
    if st.get("voice_minus_music_lu") is not None:
        d["mix"] = {"voice_minus_music_lu": st["voice_minus_music_lu"]}
        d["confidence"]["mix"] = "measured"
    sp = (sm.get("script_metrics") or {}).get("speech_ratio")
    if sp is not None:
        d["speech"] = {"speech_ratio": sp}
        d["confidence"]["speech"] = "measured"
    return d


def draft_scripting(sm, job_id, link="", creator=""):
    m = sm.get("script_metrics") or {}
    if not m.get("available"):
        raise ValueError("no transcript in the pack: scripting cannot be drafted (re-run analysis)")
    d = {"type": "scripting", "schema_version": 2, "source": _src(job_id, link, creator),
         "transcript_basis": {"coverage_ratio": m["coverage_ratio"], "complete": m["complete"],
                              "phonetic_only": m.get("vocabulary_note") == "phonetic"},
         "hook": {"first_words": m["hook"]["first_12_words"], "first_word_s": m["hook"]["first_word_s"]},
         "pacing": {"words_per_min_speaking": m["words_per_min_speaking"], "words_per_min_overall": m["words_per_min_overall"],
                    "speech_ratio": m["speech_ratio"], "sentence_words_mean": m["sentences"]["words_mean"],
                    "sentence_words_p90": m["sentences"]["words_p90"], "pause_mean_s": m["pauses"]["mean_s"],
                    "questions_per_min": m["questions_per_min"], "numbers_per_min": m["numbers_per_min"]},
         "confidence": {"transcript_basis": "measured", "hook": "measured", "pacing": "measured"}}
    if m.get("repeated_phrases"):
        d["lexicon"] = {"signature_phrases": [p["phrase"] for p in m["repeated_phrases"]]}
        d["confidence"]["lexicon"] = "estimated"
    return d


DRAFTERS = {"editing": draft_editing, "sound": draft_sound, "scripting": draft_scripting}
