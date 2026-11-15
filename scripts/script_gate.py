"""Script gate: measurable hook / retention / pace / research checks for a NEW script. Thresholds come from the
creator's measured script profile (not constants), so the gate never fights the style we copy. Judgement (is it a good
hook?) stays with the Director; this blocks what is measurable."""
import re
import statistics as st

from .guards import MAX_WPM

DEVICE = re.compile(r"\?|\b(but|until|then|except|instead|yet|never|only|without|why|what happens|here's|lekin|par|magar|phir|sirf|bina|kyun|kya|kab|kaise|asli|sabse)\b", re.I)
NUM = re.compile(r"\b\d[\d,.]*\b|\b(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|dozen|fifteen|twenty|thirty|forty|fifty|hundred|thousand|million|billion|teen|chaar|paanch|chhe|saat|aath|nau|das|dasvaan|aadha|sau|hazaar|lakh)\b", re.I)
YOU = re.compile(r"\b(you|your|you're|aap|aapne|aapka|aapki|aapke|tum|tumhari)\b", re.I)


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s.strip()]


def _density(text, window_words):
    """share of word-windows that hold a turn device (question, contrast word, number)."""
    w = text.split()
    wins = [" ".join(w[i:i + window_words]) for i in range(0, max(1, len(w) - window_words // 2), window_words)]
    return sum(1 for x in wins if DEVICE.search(x) or NUM.search(x)) / max(1, len(wins))


def check(text, seconds, ref, facts=None, window_s=20):
    """ref = profile['parts']['script'] of the creator. facts = [{"number": "..", "source": "https://.."}]. -> (ok, problems)"""
    bad, sents = [], _sentences(text)
    words = text.split()
    wpm = len(words) / (seconds / 60)
    if wpm > MAX_WPM:
        bad.append(f"pace {wpm:.0f} wpm is above {MAX_WPM}")
    first = sents[0] if sents else ""
    if not (YOU.search(" ".join(words[:12])) or "?" in first or NUM.search(" ".join(words[:12]))):
        bad.append("hook: first twelve words have no 'you', question or number")
    ref_sents = _sentences(ref.get("text", ""))
    ref_first = len(ref_sents[0].split()) if ref_sents else 15
    if len(first.split()) > max(15, ref_first + 3):
        bad.append(f"hook: first sentence has {len(first.split())} words (creator opens with {ref_first})")
    lens = [len(s.split()) for s in sents]
    mean_ref = (ref.get("sentences") or {}).get("words_mean")
    if mean_ref and abs(st.mean(lens) - mean_ref) > mean_ref * 0.25:
        bad.append(f"sentence length {st.mean(lens):.1f} words, creator {mean_ref}")
    per_win = max(1, int(wpm / 60 * window_s))
    mine = _density(text, per_win)
    theirs = _density(ref["text"], per_win) if ref.get("text") else 0.8
    if mine < theirs * 0.7:
        bad.append(f"retention: turns/questions/numbers in {mine:.0%} of {window_s}s windows, creator {theirs:.0%}")
    if ref.get("cta_words") and not re.search(r"\b(follow|comment|share|save|subscribe)\b", " ".join(words[-30:]), re.I):
        bad.append("creator ends with a call to action; script does not")
    if facts is not None:
        src = {str(f.get("number")).lower() for f in facts if str(f.get("source", "")).startswith("http")}
        for n in sorted({m.group(0).lower() for m in NUM.finditer(text)} - src):
            bad.append(f"research: number '{n}' has no source in facts file")
    return (not bad), bad
