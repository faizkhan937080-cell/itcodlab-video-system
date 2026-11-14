"""Word timing (point 2): graphics start on the spoken word, not on a guessed second.
words_from_transcript -> [{w, start, end, exact}] (exact = Whisper word time; False = spread inside its segment by letters).
find_phrase -> first time the phrase is spoken (optionally the nth, or after a time)."""
import re

from .script_metrics import best_pass

TOKEN = re.compile(r"\w+", re.UNICODE)


def norm(text):
    return [t.lower() for t in TOKEN.findall(text or "")]


def words_from_transcript(transcript):
    """Words with times. Uses Whisper word times when the transcript has them, else spreads each segment by letter count."""
    if not transcript or not transcript.get("available"):
        return []
    segs, _ = best_pass(transcript)
    out = []
    for s in segs:
        if s.get("loop") or not s.get("text"):
            continue
        ws = s.get("words")
        if ws and all("start" in w and "end" in w for w in ws):
            for w in ws:
                for tok in norm(w.get("word") or w.get("text") or ""):
                    out.append({"w": tok, "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3), "exact": True})
            continue
        toks = norm(s["text"])
        if not toks:
            continue
        a, b = float(s["start"]), float(s["end"])
        total = sum(len(t) for t in toks) or 1
        t = a
        for tok in toks:
            d = (b - a) * len(tok) / total
            out.append({"w": tok, "start": round(t, 3), "end": round(t + d, 3), "exact": False})
            t += d
    return out


def find_phrase(words, phrase, nth=1, after=0.0):
    """-> {"t", "t_end", "exact"} for the nth time the phrase is spoken after `after` seconds, else None."""
    want = norm(phrase)
    if not want:
        return None
    seen = 0
    for i in range(len(words) - len(want) + 1):
        if words[i]["start"] < after - 1e-9:
            continue
        if [x["w"] for x in words[i:i + len(want)]] == want:
            seen += 1
            if seen == nth:
                span = words[i:i + len(want)]
                return {"t": span[0]["start"], "t_end": span[-1]["end"], "exact": all(x["exact"] for x in span)}
    return None
