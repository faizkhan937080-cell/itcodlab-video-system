"""Virality gate (Faiz 2026-11-14: "viralty bhi check karna hai"). Scores a script + beats BEFORE anything is rendered.
Checks are short-form retention rules taken from the 6 learning videos + measured reference numbers, each one a yes/no
with a fix line, so the Director rewrites instead of guessing. Score >= PASS -> go; lower -> BLOCK with fixes."""
import re

PASS = 80
FEAR = {"cancer", "burn", "burning", "scald", "scalds", "damage", "wrong", "risk", "danger", "toxic", "trap", "wounded",
        "dread", "die", "dying", "attack", "stroke", "poison", "hits"}
LOOP = ("but", "here's", "what", "why", "secret", "trap", "nobody", "until", "?", "...")
SHARE = ("send this", "share this", "tag", "save this", "show this")
NUM_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "twenty", "thirty", "forty",
             "fifty", "sixty", "hundred", "thousand", "million", "double", "doubled", "half", "triple"}


def _words(t):
    return re.findall(r"[A-Za-z0-9']+", t.lower())


def score(segments, beats_starts=None, wpm=165.0):
    """segments: [{"text", "start"?, "end"?}] in order. beats_starts: visual change times (s). -> dict with score, checks, fixes."""
    text = " ".join(s["text"] for s in segments)
    ws = _words(text)
    dur = segments[-1].get("end") or len(ws) / wpm * 60
    first = segments[0]["text"]
    first_w = _words(first)
    early = " ".join(s["text"] for s in segments[:2]).lower()
    last = " ".join(s["text"] for s in segments[-2:]).lower()
    checks = {
        "hook_short": (len(first_w) <= 22 and len(_words(first.split(".")[0])) <= 8, 15,
                       "first sentence must land in under 3 s: 8 words or fewer"),
        "hook_you": (any(w in first_w for w in ("you", "your", "you're")), 10, "talk to the viewer in the first line (you/your)"),
        "hook_stakes": (any(w in FEAR for w in first_w) or "wrong" in first.lower(), 10,
                        "first line needs a stake (something going wrong, a risk, a fear)"),
        "open_loop": (any(k in early for k in LOOP), 10, "open a question in the first 8 s (but / here's / why / ...)"),
        "proof_number": (any(w.isdigit() or w in NUM_WORDS for w in ws), 10, "add one hard number from a real study"),
        "emotion_words": (sum(w in FEAR for w in ws) >= 3, 10, "use at least 3 felt words (burn, risk, damage, trap)"),
        "visual_cadence": (bool(beats_starts) and max((b - a) for a, b in zip([0.0] + sorted(beats_starts), sorted(beats_starts) + [dur])) <= 9.0,
                           10, "change the picture at least every 9 s (reference: 7.6 s median shot)"),
        "length": (25 <= dur <= 65, 5, "keep it 25-65 s"),
        "payoff": (any(k in last for k in ("you don't", "just", "instead", "let it", "thank")), 10,
                   "end with one simple thing the viewer can do"),
        "share_trigger": (any(k in last for k in SHARE), 10, "last line: give a reason to send it to someone"),
    }
    total = sum(w for ok, w, _ in checks.values() if ok)
    return {"score": total, "verdict": "GO" if total >= PASS else "BLOCK", "duration_s": round(dur, 1),
            "checks": {k: ok for k, (ok, _, _) in checks.items()},
            "fixes": [fix for ok, _, fix in checks.values() if not ok]}
