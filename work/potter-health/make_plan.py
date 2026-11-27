"""Health reel (Semmelweis) in the Potter-reel editing style -> one-scene Remotion plan. Run: python3 work/potter-health/make_plan.py <voice-name> '<SEGTIMES json>' [sample_seconds]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from scripts.anchors import words_from_transcript  # noqa: E402

VOICE = sys.argv[1]
SEG = json.loads(sys.argv[2])                      # [[id,start,end],...] from the voice job log
SAMPLE = float(sys.argv[3]) if len(sys.argv) > 3 else None
S = json.load(open("work/potter-health/script-v1.json", encoding="utf-8"))["segments"]
tr = {"available": True, "segments": [{"start": a, "end": b, "text": s["text"]} for (_, a, b), s in zip(SEG, S)]}
W = words_from_transcript(tr)
assert len(W) == 94, len(W)
SP_END = SEG[-1][2]
END = round(SP_END + 3.0, 2)
LOGO_T = round(SP_END + 0.55, 2)


def tt(i):  # start time of token i (end of speech for i == len)
    return W[i]["start"] if i < len(W) else SEG[-1][2]


# caption = (token_from, token_to, lines); line = [(text, style, n_tokens)]
Cp = [
    (0, 4, [[("In", "s", 1), ("1847", "p", 3)]]),
    (4, 8, [[("one Vienna", "s", 2)], [("hospital ward", "b", 2)]]),
    (8, 14, [[("was losing nearly", "s", 3)], [("1 in 5", "p", 3)]]),
    (14, 16, [[("new", "s", 1)], [("mothers", "b", 1)]]),
    (16, 19, [[("Doctor Ignaz", "i", 2)], [("Semmelweis", "p", 1)]]),
    (19, 21, [[("noticed", "s", 1)], [("something", "b", 1)]]),
    (21, 27, [[("Doctors were walking from", "s", 4)], [("dead bodies", "p", 2)]]),
    (27, 32, [[("straight into the", "s", 3)], [("delivery room", "b", 2)]]),
    (32, 38, [[("So he told them to", "s", 5)], [("wash", "b", 1)]]),
    (38, 42, [[("their hands in", "s", 3)], [("chlorine", "p", 1)]]),
    (42, 45, [[("Deaths fell from", "s", 3)]]),
    (45, 47, [[("18%", "p", 2)]]),
    (47, 50, [[("to about", "s", 2)], [("2%", "p", 1)]]),
    (50, 54, [[("But the doctors", "s", 3)], [("laughed", "b", 1)]]),
    (54, 57, [[("They", "s", 1)], [("rejected him", "p", 2)]]),
    (57, 63, [[("and he died in an", "s", 5)], [("asylum", "b", 1)]]),
    (63, 68, [[("in", "s", 1), ("1865,", "p", 3)], [("forgotten", "b", 1)]]),
    (68, 73, [[("Today, the", "i", 2)], [("World Health", "b", 2)], [("Organization", "b", 1)]]),
    (73, 76, [[("says", "s", 1)], [("clean hands", "p", 2)]]),
    (76, 81, [[("can prevent up to", "s", 4)], [("half", "p", 1)]]),
    (81, 85, [[("of avoidable", "s", 2)], [("hospital infections", "b", 2)]]),
    (85, 90, [[("He wasn't selling", "s", 4)], [("soap", "p", 1)]]),
    (90, 94, [[("He was selling", "s", 3)], [("life", "p", 1)]]),
]
caps = []
pink_times = []
for k, (a, b, lines) in enumerate(Cp):
    i = a
    out = []
    for ln in lines:
        row = []
        for text, st, n in ln:
            row.append({"w": text, "st": st, "at": round(tt(i) - 0.05, 3)})
            if st == "p":
                pink_times.append(round(tt(i), 3))
            i += n
        out.append(row)
    assert i == b, (k, i, b)
    nxt = tt(Cp[k + 1][0]) if k + 1 < len(Cp) else SP_END + 0.3
    caps.append({"t0": round(tt(a) - 0.1, 3), "t1": round(nxt - 0.03, 3), "lines": out})
caps[0]["t0"] = 0.0
caps[-1]["t1"] = round(SP_END + 0.3, 3)

STD = {"x": 0.5, "y": 0.62, "w": 1.0, "h": 0.52}
BUST = {"x": 0.5, "y": 0.63, "w": 1.0, "h": 0.58}
O = [  # (object, token_from, token_to, box, decor)
    ("bed", 0, 8, STD, "dots"),
    ("five", 8, 16, STD, "brackets"),
    ("bust", 16, 21, BUST, "curves"),
    ("scalpel", 21, 27, STD, "cross"),
    ("bed", 27, 32, STD, "ring"),
    ("soap", 32, 42, STD, "brackets"),
    ("bars", 42, 50, STD, "dots"),
    ("gavel", 50, 57, STD, "frame"),
    ("hourglass", 57, 68, STD, "ring"),
    ("globe", 68, 76, STD, "brackets"),
    ("capsule", 76, 85, STD, "dots"),
    ("soap_pink", 85, 90, STD, "cross"),
    ("heart", 90, 94, BUST, "ring"),
]
objs = []
for k, (o, a, b, box, dec) in enumerate(O):
    t0 = 0.0 if k == 0 else round(tt(a) - 0.12, 3)
    t1 = round(tt(O[k + 1][1]) - 0.12 + 0.2, 3) if k + 1 < len(O) else round(LOGO_T, 3)   # 0.2 s overlap: the next one pops in while this one leaves
    objs.append({"obj": o, "t0": t0, "t1": t1, "box": box, "decor": dec})

props = {"caps": caps, "objs": objs, "end_s": END, "logo": {"src": "brand/integrity-logo.jpg", "t0": LOGO_T}}
total = SAMPLE or END
scenes = [{"id": "s1", "duration_s": total, "template": "potter", "props": props, "transition_in": {"type": "cut"}}]
SFX = "assets/library/sfx"


def sfx(name, at, vol, dur=0.8):
    return {"src": f"{SFX}/{name}.wav", "at_s": round(max(0.0, at), 3), "duration_s": dur, "role": "sfx", "volume": vol}


sf = [sfx("softpop", o["t0"] + 0.04, 0.6) for o in objs] + [sfx("swish", o["t0"] - 0.05, 0.22, 0.5) for o in objs[1::2]]
sf += [sfx("softpop", t, 0.32, 0.4) for t in pink_times]
sf.append(sfx("softpop", LOGO_T + 0.25, 0.6))
sf = [s for s in sf if s["at_s"] < total]
voice = {"src": f"output/voice/{VOICE}/{VOICE}.wav", "at_s": 0, "role": "voice", "volume": 1.0}
music = {"src": "assets/library/music/groove-143.mp3", "at_s": 0, "duration_s": total, "role": "music", "volume": 0.34, "fade_in_s": 0.4, "fade_out_s": 2.2,
         "duck": [{"from_s": a, "to_s": b, "gain": 0.62} for _, a, b in SEG]}
plan = {"title": "Semmelweis handwashing (health reel, potter style)", "fps": 30, "orientation": "portrait", "width": 1080, "height": 1920,
        "scenes": scenes, "captions": [], "audio": [voice, music] + sf, "audio_target_lufs": -17, "vignette": 0.0, "grain": False}
name = "health-sample" if SAMPLE else "health-full"
d = Path("trigger/sample")
(d / f"{name}-plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
times = [0.3, 1.0, 2.2, 3.5, 4.6, 5.6, 6.6, 7.9, 8.6, 9.3] if SAMPLE else sorted({round(min(END - 0.1, f), 2) for o in objs for f in (o["t0"] + 0.45, (o["t0"] + o["t1"]) / 2, o["t1"] - 0.45)} | {LOGO_T + 0.15, LOGO_T + 0.5, LOGO_T + 1.5, END - 0.3})
(d / f"{name}-sample.json").write_text(json.dumps({"name": name, "plan": f"{name}-plan.json", "seconds": total, "times": times, "cols": 6, "tile_w": 250} if not SAMPLE else {"name": name, "plan": f"{name}-plan.json", "seconds": total, "times": times}), encoding="utf-8")
print(name, total, len(objs), "objects", len(sf), "sfx", len(caps), "captions")
