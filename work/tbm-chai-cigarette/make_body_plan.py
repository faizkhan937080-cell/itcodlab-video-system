"""Tea + cigarette reel in the drawn anatomy (Sodhi) look: voice timings -> Remotion plan. Run: python3 work/tbm-chai-cigarette/make_body_plan.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from scripts.anchors import words_from_transcript  # noqa: E402
from scripts.director_build import captions_from  # noqa: E402

VOICE = "tbm-chai-cig-hinglish-slow"
T = [(0.2, 9.21), (9.71, 17.406), (17.806, 23.91), (24.36, 35.084), (35.584, 43.767), (44.217, 51.529), (52.029, 59.882), (60.282, 63.594)]
TXT = ["Chai ki ek chuski. Cigarette ka ek kash. Aapko lagta hai aap relax kar rahe ho... lekin body ke andar, chupchaap kuch galat ho raha hai.",
       "Painsath degree se zyada garam chai sirf gala nahi sekti. Wo aapki food pipe ki nazuk lining ko jala deti hai.",
       "Aur theek usi waqt, dhuan aata hai... aur usi zakhmi parat par baith jaata hai.",
       "Chaar lakh se zyada logon par hui ek study mein ye mila. Bahut garam chai, aur roz ki smoking, food pipe ke cancer ka risk lagbhag double kar deti hai.",
       "Ab aapka dil. Nicotine pulse badhata hai. Caffeine blood pressure badhata hai. Dono saath, to double jhatka.",
       "Aur asli jaal ye hai. Dhuan liver ko caffeine jaldi khatm karna sikha deta hai, isliye smoker ko cup pe cup chahiye.",
       "Chai chhodne ki zaroorat nahi. Bas thodi thandi hone do, aur cigarette chhod do. Aapki food pipe chupchaap thank you bolegi.",
       "Ye us dost ko bhejo jo hamesha dono saath karta hai."]
SEG = [(a, b, t) for (a, b), t in zip(T, TXT)]
END = 64.2
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
    {"shot": "hook", "headline": "Chai + Cigarette", "headline2": "Andar kya\nhota hai?", "turn_at_s": at(0, "lekin")},
    {"shot": "scald", "headline": "Bahut garam chai\nlining jala deti hai", "headline_at_s": at(1, "wo")},
    {"shot": "smoke_settle", "headline": "Dhuan zakhm par\nbaith jaata hai", "headline_at_s": at(2, "baith")},
    {"shot": "study", "big": "4,00,000+", "count_to": 400000, "count_suffix": "+", "locale": "en-IN", "big_at_s": at(3, "chaar"), "turn_at_s": at(3, "lagbhag"),
     "labels": ["Dono aadat nahi", "Bahut garam chai + roz smoking"], "headline": "Cancer ka risk\nlagbhag double", "headline_at_s": at(3, "lagbhag")},
    {"shot": "heart", "headline": "Dil par\ndouble jhatka", "headline_at_s": at(4, "dono"),
     "chips": [{"text": "Nicotine: pulse ↑", "at_s": at(4, "nicotine")}, {"text": "Caffeine: BP ↑", "at_s": at(4, "caffeine")}]},
    {"shot": "liver", "headline": "Asli jaal", "headline_at_s": at(5, "jaal"), "turn_at_s": at(5, "isliye"),
     "sub": "Smoker ka caffeine jaldi khatm", "sub_at_s": at(5, "jaldi")},
    {"shot": "cool", "headline": "Chai thandi karo.\nCigarette chhodo.", "headline_at_s": at(6, "bas"), "turn_at_s": at(6, "cigarette"),
     "labels": ["Thandi hone do"], "badge": "Food pipe theek hone lagti hai", "badge_at_s": at(6, "aapki")},
    {"shot": "end", "headline": "Us dost ko bhejo\njo dono karta hai", "headline_at_s": 0.3},
]
scenes = [{"id": f"b{i + 1}", "duration_s": round(starts[i + 1] - starts[i], 3), "template": "body", "props": p,
           "transition_in": {"type": "cut"}} for i, p in enumerate(P)]
plan = {
    "title": "Chai + cigarette: andar kya hota hai", "fps": 30, "orientation": "portrait", "width": 1080, "height": 1920,
    "scenes": scenes, "captions": captions_from(tr),
    "caption_style": {"look": "ext", "component": "caption-dim-progress", "font": "Montserrat", "y": 0.8, "max_width": 0.86,
                      "props": {"fontSize": 84, "fontWeight": 600, "color": "#F4EFC6", "dimOpacity": 1, "shadow": True, "combineTokensWithinMilliseconds": 1400}},
    "audio": [{"src": f"output/voice/{VOICE}/{VOICE}.wav", "at_s": 0, "role": "voice", "volume": 1.0},
              {"src": "assets/library/music/tbm-dark-ambient.mp3", "at_s": 0, "duration_s": END, "role": "music", "volume": 0.3, "fade_in_s": 1.0, "fade_out_s": 2.0,
               "duck": [{"from_s": a, "to_s": b, "gain": 0.45} for a, b, _ in SEG]}],
    "audio_target_lufs": -14, "vignette": 0.22, "grain": False,
}
out = Path("trigger/sample/body-chai-cig-hi-plan.json")
out.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
print(out, [s["duration_s"] for s in scenes], P[0]["turn_at_s"])
