"""Skills testing video: voice timings -> Remotion plan (7 parts). Run: python3 work/skilltest/make_plan.py"""
import json
from pathlib import Path

VOICE = "tbm-skilltest-v1"
T = [(0.2, 9.781), (10.031, 15.588), (15.838, 22.629), (22.879, 29.785), (30.035, 36.296), (36.546, 44.743), (44.993, 52.081)]
END = 52.6
starts = [0.0] + [round((T[i][0] + T[i - 1][1]) / 2, 3) for i in range(1, 7)] + [END]
B6 = ["tested", "tested", "tested", "tested"]  # updated after the sample look
P = [
    dict(part=1, name="claude-animated-shorts", status="tested", note="3D cartoon: rangeen sheher, kali outline (three.js + Remotion)"),
    dict(part=2, name="claude-blender-skills", status="not_tested", reason=["Is machine par Blender install nahi hai.", "Isliye Blender ka koi shot nahi bana.", "Nakli shot nahi dikhaya."]),
    dict(part=3, name="stickman-video-director", status="tested", note="Code Engine B1: saaf lakeeron wala stickman"),
    dict(part=4, name="rossark-motion-skill", status="tested", note="Patte apne jod par hilte hain, dheere aur shaant"),
    dict(part=5, name="Remotion 3D (3d.md)", status="tested", note="ThreeCanvas + lights, sab kuch frame se chalta hai"),
    dict(part=6, name="lottie + transitions + light-leaks + motion-blur", status="tested", beats=["Lottie", "Transitions", "Light leaks", "Motion blur"], beat_status=B6, note="Remotion ke chaar packages"),
    dict(part=7, name="viral-hooks-skill", status="tested", hook="Agar aap ab bhi still photo par zoom karte hain, to RUK JAIYE.", note="Hook formula se bani, script ki line"),
]
scenes = [{"id": f"s{i + 1}", "duration_s": round(starts[i + 1] - starts[i], 3), "template": "skilltest", "props": p, "transition_in": {"type": "cut"}} for i, p in enumerate(P)]
base = {"fps": 30, "orientation": "portrait", "width": 1080, "height": 1920}
plan = dict(title="Skills testing video", **base, scenes=scenes, captions=[],
            audio=[{"src": f"output/voice/{VOICE}/{VOICE}.wav", "at_s": 0, "role": "voice", "volume": 1.0},
                   {"src": "assets/library/music/tbm-dark-ambient.mp3", "at_s": 0, "duration_s": END, "role": "music", "volume": 0.15, "fade_in_s": 1.0, "fade_out_s": 2.0,
                    "duck": [{"from_s": a, "to_s": b, "gain": 0.45} for a, b in T]}],
            audio_target_lufs=-14, vignette=0.0, grain=False)
d = Path("trigger/sample")
(d / "skilltest-plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
two = round(starts[2], 3)  # parts 1 and 2
(d / "skilltest-sample.json").write_text(json.dumps({"name": "skilltest", "plan": "skilltest-plan.json", "seconds": two, "times": [1.0, 3.0, 5.0, 7.0, 9.0, two - 4.5, two - 3.0, two - 1.5, two - 0.3]}), encoding="utf-8")
# part 6 alone, silent (checks lottie / transitions / light leak / motion blur render on the runner)
p6 = dict(title="skilltest part 6", **base, scenes=[dict(scenes[5], id="s1", duration_s=round(starts[6] - starts[5], 3))], captions=[], audio=[], audio_target_lufs=-14, vignette=0.0, grain=False)
(d / "skilltest6-plan.json").write_text(json.dumps(p6, indent=1, ensure_ascii=False), encoding="utf-8")
(d / "skilltest6-sample.json").write_text(json.dumps({"name": "skilltest6", "plan": "skilltest6-plan.json", "seconds": p6["scenes"][0]["duration_s"], "times": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]}), encoding="utf-8")
print(two, [s["duration_s"] for s in scenes])
