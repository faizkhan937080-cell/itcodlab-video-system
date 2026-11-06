"""Deterministic script metrics from the transcript (scripts measure, Claude does not guess numbers).

Input: the dict from audio.transcribe (segments with start/end/text, optional alt_english pass).
Output: compact numbers the scripting DNA must quote: speaking rate, pauses, sentence lengths, questions, script mix,
person markers, repeated phrases, hook timing. Everything is measured on the transcript text; if the transcript is
phonetic Hinglish, word counts are still right but vocabulary is only a gist (the result says so).
"""
import re
import statistics as st

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
LATIN = re.compile(r"[A-Za-z]")
WORD = re.compile(r"[\wऀ-ॿ']+", re.UNICODE)
SENT_END = re.compile(r"(?<=[.?!।])\s+")
SECOND_PERSON = {"you", "your", "aap", "apna", "apni", "aapko", "aapka", "tum", "tumhe", "tumhara",
                 "आप", "आपको", "आपका", "आपकी", "अपना", "तुम", "तुम्हें", "तुम्हारा"}
FIRST_PERSON = {"i", "me", "my", "we", "our", "main", "mai", "mera", "meri", "hum", "hamara",
                "मैं", "मेरा", "मेरी", "हम", "हमारा"}
FILLERS = {"so", "basically", "like", "actually", "okay", "ok", "right", "yaar", "bhai", "matlab", "toh",
           "तो", "मतलब", "यानी", "अच्छा", "देखो", "बस", "यार", "भाई"}
CTA_WORDS = {"comment", "follow", "subscribe", "share", "save", "dm", "link", "bio", "like",
             "कमेंट", "फॉलो", "शेयर", "सेव", "लिंक", "डीएम"}


def _words(text):
    return [w for w in WORD.findall(text or "")]


def collapse_loops(text, min_repeat=4, max_n=4):
    """Whisper sometimes loops ("करेट करेट करेट ..."). Collapse any 1-4 word unit repeated >= min_repeat times in a row
    to one copy. Returns (clean_text, removed_words, is_loop) where is_loop = the segment is (almost) only a loop, i.e. removed copies >= 3x the words kept."""
    toks = (text or "").split()
    out, removed, i = [], 0, 0
    while i < len(toks):
        hit = False
        for n in range(1, max_n + 1):
            unit = toks[i:i + n]
            if len(unit) < n:
                break
            reps, j = 1, i + n
            while toks[j:j + n] == unit:
                reps += 1
                j += n
            if reps >= min_repeat:
                out.extend(unit)
                removed += (reps - 1) * n
                i, hit = j, True
                break
        if not hit:
            out.append(toks[i])
            i += 1
    return " ".join(out), removed, bool(out) and removed >= 3 * len(out)


def _pct(vals, q):
    if not vals:
        return None
    s = sorted(vals)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 2)


def words_before(segments, t):
    """Words spoken before time t (words spread evenly inside a segment)."""
    n = 0.0
    for s in segments:
        w = len(_words(s["text"]))
        if s["end"] <= t:
            n += w
        elif s["start"] < t:
            span = max(s["end"] - s["start"], 1e-6)
            n += w * (t - s["start"]) / span
    return round(n, 1)


def _repeated_phrases(words, n=3, min_count=2, top=8):
    low = [w.lower() for w in words]
    counts = {}
    for i in range(len(low) - n + 1):
        g = " ".join(low[i:i + n])
        counts[g] = counts.get(g, 0) + 1
    rep = [(g, c) for g, c in counts.items() if c >= min_count]
    rep.sort(key=lambda x: (-x[1], x[0]))
    return [{"phrase": g, "count": c} for g, c in rep[:top]]


def _norm(sent):
    return " ".join(w.lower() for w in _words(sent))


def dedup_sentences(sentences):
    """Repeated lines are kept ONCE (first position) with a count. Returns (unique list of {text, count})."""
    seen, order = {}, []
    for x in sentences:
        k = _norm(x)
        if not k:
            continue
        if k in seen:
            seen[k]["count"] += 1
        else:
            seen[k] = {"text": x.strip(), "count": 1}
            order.append(k)
    return [seen[k] for k in order]


def compute(transcript, duration_s):
    """Return a metrics dict, or {"available": False}."""
    if not transcript or not transcript.get("available") or not transcript.get("segments"):
        return {"available": False}
    segs = [s for s in transcript["segments"] if s.get("text") and not s.get("loop")]
    text = " ".join(s["text"] for s in segs)
    words = _words(text)
    if not words:
        return {"available": False}
    speech_s = sum(max(s["end"] - s["start"], 0) for s in segs)
    gaps = [segs[i + 1]["start"] - segs[i]["end"] for i in range(len(segs) - 1)]
    gaps = [g for g in gaps if g > 0]
    sentences = [x for x in SENT_END.split(text) if x.strip()]
    if len(sentences) <= 1:  # no punctuation (common in Hindi output): fall back to segments
        sentences = [s["text"] for s in segs]
    s_lens = [len(_words(x)) for x in sentences]
    minutes = max(duration_s / 60.0, 1e-6)
    low = [w.lower() for w in words]
    dev, lat = len(DEVANAGARI.findall(text)), len(LATIN.findall(text))
    letters = max(dev + lat, 1)
    cov = transcript.get("coverage_ratio")
    out = {
        "available": True,
        "coverage_ratio": cov,
        "complete": bool(cov is not None and cov >= 0.9),
        "words": len(words),
        "words_per_min_speaking": round(len(words) / max(speech_s / 60.0, 1e-6), 1),
        "words_per_min_overall": round(len(words) / minutes, 1),
        "speech_ratio": round(min(speech_s / max(duration_s, 1e-6), 1.0), 3),
        "pauses": {"count_gt_0_5s": sum(g > 0.5 for g in gaps), "mean_s": round(st.mean(gaps), 2) if gaps else 0.0,
                   "max_s": round(max(gaps), 2) if gaps else 0.0},
        "sentences": {"count": len(sentences), "words_mean": round(st.mean(s_lens), 1),
                      "words_median": _pct(s_lens, 0.5), "words_p90": _pct(s_lens, 0.9)},
        "questions_per_min": round(text.count("?") / minutes, 2),
        "exclamations_per_min": round(text.count("!") / minutes, 2),
        "numbers_per_min": round(sum(any(c.isdigit() for c in w) for w in words) / minutes, 2),
        "script_mix": {"devanagari_share": round(dev / letters, 3), "latin_share": round(lat / letters, 3)},
        "second_person_per_100w": round(100 * sum(w in SECOND_PERSON for w in low) / len(words), 2),
        "first_person_per_100w": round(100 * sum(w in FIRST_PERSON for w in low) / len(words), 2),
        "fillers_per_100w": round(100 * sum(w in FILLERS for w in low) / len(words), 2),
        "cta_words": sorted({w for w in low if w in CTA_WORDS}),
        "repeated_phrases": _repeated_phrases(words),
        "repeated_sentences": [u for u in dedup_sentences(sentences) if u["count"] > 1][:8],
        "unique_sentence_share": round(len(dedup_sentences(sentences)) / max(len(sentences), 1), 3),
        "hook": {"first_word_s": round(segs[0]["start"], 2), "words_in_first_3s": words_before(segs, 3.0),
                 "words_in_first_5s": words_before(segs, 5.0), "first_12_words": " ".join(words[:12])},
        "vocabulary_note": "phonetic" if dev and not lat else "mixed" if dev else "roman",
    }
    alt = transcript.get("alt_english")
    if alt and alt.get("text"):
        aw = _words(alt["text"])
        out["english_pass"] = {"coverage_ratio": alt.get("coverage_ratio"), "words": len(aw),
                               "first_12_words": " ".join(aw[:12])}
    return out


def _clock(t):
    t = max(0.0, float(t))
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def transcript_txt(transcript):
    """Human-readable timed transcript (plain text) from transcript.json. Both passes, loop segments skipped."""
    if not transcript or not transcript.get("available"):
        return "Transcript not available for this reel.\n"
    blocks = [("MAIN PASS (language: %s)" % transcript.get("language", "?"), transcript)]
    if transcript.get("alt_english"):
        blocks.append(("ENGLISH PASS (English words come out right here)", transcript["alt_english"]))
    out = []
    for title, tr in blocks:
        out += [title, "=" * len(title)]
        for x in tr.get("segments", []):
            if x.get("loop") or not x.get("text"):
                continue
            out.append(f"[{_clock(x['start'])} - {_clock(x['end'])}] {x['text']}")
        out.append("")
    return "\n".join(out)
