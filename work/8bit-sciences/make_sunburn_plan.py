"""8bit_sciences SUNBURN: beats-sunburn-v1.json -> one 60 s eightbit scene (props.scene='sunburn') + sample spec (middle of each beat).
Run: python3 work/8bit-sciences/make_sunburn_plan.py   (writes trigger/sample/8bit-sunburn-plan.json and -sample.json)"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
beats = json.loads((ROOT / "work/8bit-sciences/beats-sunburn-v1.json").read_text(encoding="utf-8"))
B = [{k: b[k] for k in ("id", "t", "label", "counter", "sound") if k in b} for b in beats["beats"]]
END = beats["format"]["seconds"]
VOICE = "8bit-sunburn-v1"
MUSIC = "assets/library/music/8bit-sunburn-loop.mp3"
scenes = [{"id": "s1", "duration_s": END, "template": "eightbit", "transition_in": {"type": "cut"},
           "props": {"scene": "sunburn", "start_s": 0.0, "beats": B}}]
audio, missing = [], []
for src, role, vol in ((f"output/voice/{VOICE}/{VOICE}.wav", "voice", 1.0), (MUSIC, "music", 0.18)):
    if (ROOT / src).exists():
        audio.append({"src": src, "at_s": 0, "role": role, "volume": vol})
    else:
        missing.append(src)
plan = {"title": "8bit sunburn", "fps": beats["format"]["fps"], "orientation": "portrait", "width": 1080, "height": 1920,
        "scenes": scenes, "captions": [], "audio": audio, "audio_target_lufs": -17, "vignette": 0.0, "grain": False}
d = ROOT / "trigger/sample"
d.mkdir(parents=True, exist_ok=True)
(d / "8bit-sunburn-plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
times = [round((b["t"][0] + b["t"][1]) / 2, 3) for b in B]
(d / "8bit-sunburn-sample.json").write_text(json.dumps({"name": "8bit-sunburn", "plan": "8bit-sunburn-plan.json", "seconds": END, "times": times}), encoding="utf-8")
print("scenes", [s["duration_s"] for s in scenes], "samples", len(times), "MISSING audio (omitted, not faked):", missing)
