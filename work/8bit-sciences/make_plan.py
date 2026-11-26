"""8bit_sciences bruise: beats-v1.json -> Remotion plan (2 scenes: skin b1-b12, end b13-b14) + short sample spec.
Run: python3 work/8bit-sciences/make_plan.py   (writes trigger/sample/8bit-bruise-*.json; audio only if the files exist)"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
beats = json.loads((ROOT / "work/8bit-sciences/beats-v1.json").read_text(encoding="utf-8"))
B = [{k: b[k] for k in ("id", "t", "label", "counter") if k in b} for b in beats["beats"]]
END = beats["format"]["seconds"]
cut = next(b["t"][0] for b in B if b["id"] == "b13")
VOICE = "8bit-bruise-v1"
MUSIC = "assets/library/music/8bit-bruise-loop.mp3"  # name set when `./run resolve` / library fetch finds the real track


def scene(i, sid, a, z, kind):
    return {"id": sid, "duration_s": round(z - a, 3), "template": "eightbit", "transition_in": {"type": "cut"},
            "props": {"scene": kind, "start_s": a, "beats": B}}


scenes = [scene(0, "s1", 0.0, cut, "skin"), scene(1, "s2", cut, END, "end")]
audio, missing = [], []
for src, role, vol in ((f"output/voice/{VOICE}/{VOICE}.wav", "voice", 1.0), (MUSIC, "music", 0.18)):
    if (ROOT / src).exists():
        audio.append({"src": src, "at_s": 0, "role": role, "volume": vol})
    else:
        missing.append(src)
plan = {"title": "8bit bruise", "fps": beats["format"]["fps"], "orientation": "portrait", "width": 1080, "height": 1920,
        "scenes": scenes, "captions": [], "audio": audio, "audio_target_lufs": -17, "vignette": 0.0, "grain": False}
d = ROOT / "trigger/sample"
d.mkdir(parents=True, exist_ok=True)
(d / "8bit-bruise-plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
times = [1.0, 3.7, 6.5, 8.6, 11.0, 14.5, 18.0, 21.0, cut + 0.2, cut + 0.5, END - 0.8]
(d / "8bit-bruise-sample.json").write_text(json.dumps({"name": "8bit-bruise", "plan": "8bit-bruise-plan.json", "seconds": END, "times": times}), encoding="utf-8")
print("scenes", [s["duration_s"] for s in scenes], "audio", len(audio), "MISSING audio (omitted, not faked):", missing)
