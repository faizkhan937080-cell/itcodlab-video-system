"""Tea + cigarette reel in the drawn anatomy (Sodhi) look: voice timings -> Remotion plan. Run: python3 work/tbm-chai-cigarette/make_body_plan.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from scripts.anchors import words_from_transcript  # noqa: E402
from scripts.director_build import captions_from  # noqa: E402

VOICE = "tbm-chai-cig-en-slow"
SEG = [(0.2, 7.837, "A sip of tea. A drag of smoke. You think you're relaxing... but inside your body, something is quietly going wrong."),
       (8.337, 15.046, "Tea hotter than sixty-five degrees doesn't just warm your throat. It scalds the delicate lining of your food pipe."),
       (15.446, 20.594, "And at that exact moment, the smoke arrives... and settles right onto that wounded layer."),
       (21.044, 30.232, "A study of over four hundred thousand people found it. Burning hot tea, plus daily smoking, nearly doubled the risk of esophageal cancer."),
       (30.732, 38.328, "Now, your heart. Nicotine pushes your pulse up. Caffeine pushes your blood pressure up. Together, the hits stack."),
       (38.778, 46.514, "And here's the trap. Smoke trains your liver to burn through caffeine faster, so smokers crave cup after cup."),
       (47.014, 53.373, "You don't have to quit tea. Just let it cool, and drop the cigarette. Your food pipe will quietly thank you."),
       (53.773, 56.513, "Send this to the one friend who always does both.")]
END = 57.1
tr = {"available": True, "segments": [{"start": a, "end": b, "text": t} for a, b, t in SEG]}
words = words_from_transcript(tr)
starts = [0.0] + [round((SEG[i][0] + SEG[i - 1][1]) / 2, 3) for i in range(1, len(SEG))] + [END]


def at(i, word, nth=1):
    """seconds from the start of scene i to the nth time `word` is spoken inside it."""
    n = 0
    for w in words:
        if SEG[i][0] - 0.01 <= w["start"] <= SEG[i][1] and w["w"] == word:
            n += 1
            if n == nth:
                return round(w["start"] - starts[i], 2)
    raise SystemExit(f"word {word!r} not found in scene {i}")


P = [
    {"shot": "hook", "headline": "Tea + Cigarette", "headline2": "What happens\ninside you?", "turn_at_s": at(0, "but")},
    {"shot": "scald", "headline": "Too hot.\nIt burns the lining.", "headline_at_s": at(1, "it")},
    {"shot": "smoke_settle", "headline": "Smoke lands\non the wound", "headline_at_s": at(2, "settles")},
    {"shot": "study", "big": "400,000+", "count_to": 400000, "count_suffix": "+", "big_at_s": at(3, "four"), "turn_at_s": at(3, "nearly"),
     "headline": "Nearly double\nthe cancer risk", "headline_at_s": at(3, "nearly")},
    {"shot": "heart", "headline": "Your heart takes\nboth hits", "headline_at_s": at(4, "together"),
     "chips": [{"text": "Nicotine: pulse ↑", "at_s": at(4, "nicotine")}, {"text": "Caffeine: BP ↑", "at_s": at(4, "caffeine")}]},
    {"shot": "liver", "headline": "The craving trap", "headline_at_s": at(5, "trap"), "turn_at_s": at(5, "so"),
     "sub": "Smokers burn caffeine faster", "sub_at_s": at(5, "burn")},
    {"shot": "cool", "headline": "Let it cool.\nDrop the cigarette.", "headline_at_s": at(6, "just"), "turn_at_s": at(6, "drop"),
     "badge": "Your food pipe heals", "badge_at_s": at(6, "your")},
    {"shot": "end", "headline": "Send this to\nthat one friend", "headline_at_s": 0.3},
]
scenes = [{"id": f"b{i + 1}", "duration_s": round(starts[i + 1] - starts[i], 3), "template": "body", "props": p,
           "transition_in": {"type": "cut"}} for i, p in enumerate(P)]
plan = {
    "title": "Tea + cigarette: what happens inside", "fps": 30, "orientation": "portrait", "width": 1080, "height": 1920,
    "scenes": scenes, "captions": captions_from(tr),
    "caption_style": {"look": "ext", "component": "caption-dim-progress", "font": "Montserrat", "y": 0.78, "max_width": 0.86,
                      "props": {"fontSize": 54, "fontWeight": 600, "color": "#F4EFC6", "dimOpacity": 1, "shadow": True, "combineTokensWithinMilliseconds": 1400}},
    "audio": [{"src": f"output/voice/{VOICE}/{VOICE}.wav", "at_s": 0, "role": "voice", "volume": 1.0},
              {"src": "assets/library/music/tbm-dark-ambient.mp3", "at_s": 0, "duration_s": END, "role": "music", "volume": 0.3, "fade_in_s": 1.0, "fade_out_s": 2.0,
               "duck": [{"from_s": a, "to_s": b, "gain": 0.45} for a, b, _ in SEG]}],
    "audio_target_lufs": -14, "vignette": 0.22, "grain": False,
}
out = Path("trigger/sample/body-chai-cig-plan.json")
out.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
print(out, [s["duration_s"] for s in scenes], P[0]["turn_at_s"])
