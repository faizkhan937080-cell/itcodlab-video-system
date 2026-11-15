"""Sample first (rulebook 23): cut the plan to its first N seconds, render a preview on the runner, make a frames sheet,
publish it to branch `review` so Claude can LOOK before Faiz gets a full render. Nothing is saved to Drive."""
import copy
import json
import tempfile
from pathlib import Path


def trim_plan(plan, seconds):
    p = copy.deepcopy(plan)
    left, scenes = float(seconds), []
    for s in p["scenes"]:
        if left <= 1e-6:
            break
        s["duration_s"] = round(min(s["duration_s"], left), 3)
        left -= s["duration_s"]
        scenes.append(s)
    p["scenes"] = scenes
    caps = []
    for c in p.get("captions", []):
        if c["start_s"] >= seconds:
            continue
        c["words"] = [w for w in c["words"] if w["start_s"] < seconds]
        c["end_s"] = round(min(c["end_s"], seconds), 3)
        caps.append(c)
    p["captions"] = caps
    for a in p.get("audio", []):
        a["duration_s"] = round(min(a.get("duration_s", seconds), seconds - a.get("at_s", 0)), 3)
        a["duck"] = [d for d in a.get("duck", []) if d["from_s"] < seconds]
        if not a["duck"]:
            a.pop("duck", None)
    return p


def ensure_music(plan, storage, log=print):
    """A music file the library does not have is made by scripts/ambient.py and added by name (never stops the run)."""
    from . import ambient
    for a in plan.get("audio", []):
        if a.get("role") == "music" and not storage.exists(a["src"]):
            with tempfile.TemporaryDirectory() as td:
                f = ambient.make(Path(td) / "bed.mp3", 60)
                storage.put_file(f, a["src"])
            log(f"MUSIC missing in library -> made own dark ambient bed at {a['src']}")


def run(spec, storage, log=print):
    from . import render, review
    plan = json.loads(Path(spec["plan_file"]).read_text(encoding="utf-8"))
    sec = float(spec.get("seconds", 6.5))
    ensure_music(plan, storage, log)
    final = spec.get("quality") == "final"   # full plan, full size, -14 LUFS, delivered to Drive (Faiz's Y)
    p = plan if final else trim_plan(plan, sec)
    name = spec["name"]
    wd = Path(tempfile.mkdtemp(prefix="itcod-sample-"))
    out = wd / f"{name}-sample.mp4"
    res = render.render_plan(p, "final" if final else "preview", str(out), storage=storage)
    if final and res.get("ok"):
        from . import finish
        res["loudness"] = finish.normalize_loudness(str(out), -14.0, wd)
        res["drive"] = storage.put_file(out, spec["deliver"])
        log(f"FINAL delivered to {spec['deliver']}")
    log(f"SAMPLE render ok={res.get('ok')} {sec}s")
    times = spec.get("times") or [round(sec * k / 7, 2) for k in range(1, 7)]
    sheet = wd / "frames.jpg"
    render.contact_sheet(str(out), times, str(sheet), cols=3)
    pack = wd / "pack"
    pack.mkdir()
    (pack / "collage_frames.jpg").write_bytes(sheet.read_bytes())
    (pack / "video.mp4").write_bytes(out.read_bytes())   # small preview, so Faiz can watch it
    for i, rp in enumerate(spec.get("ref_paths", []), 1):   # reference collages from Drive, so Claude can compare side by side
        storage.fetch(rp, pack / f"collage_ref_{i:02d}.jpg")
    pub = review.publish(pack, f"sample-{name}")
    log("REVIEW " + json.dumps(pub))
    return {"ok": bool(res.get("ok")), "check": {k: res.get(k) for k in ("loudness", "safe_zone") if k in res}, "review": pub}
