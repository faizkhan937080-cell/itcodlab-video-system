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
    from . import ambient, groove
    for a in plan.get("audio", []):
        if a.get("role") == "music" and not storage.exists(a["src"]):
            with tempfile.TemporaryDirectory() as td:
                if Path(a["src"]).stem.startswith("groove"):
                    f = groove.make(Path(td) / "bed.mp3", 60)
                    storage.put_file(f, a["src"])
                    log(f"MUSIC {a['src']} made own 143 bpm groove bed")
                    continue
                f = ambient.make(Path(td) / "bed.mp3", 60)
                storage.put_file(f, a["src"])
            log(f"MUSIC missing in library -> made own dark ambient bed at {a['src']}")


def ensure_sfx(plan, storage, log=print):
    """Meme sound effects the library lacks are made by scripts/sfx_synth.py (own, licence-free) and added by name."""
    from . import sfx_synth
    for a in plan.get("audio", []):
        if a.get("role") == "sfx":
            name = Path(a["src"]).stem
            if name in sfx_synth.RECIPES and not storage.exists(a["src"]):
                with tempfile.TemporaryDirectory() as td:
                    storage.put_file(sfx_synth.make(name, Path(td) / f"{name}.wav"), a["src"])
                log(f"SFX {name} missing in library -> made own and added at {a['src']}")


def run(spec, storage, log=print):
    from . import costs
    plan0 = json.loads(Path(spec["plan_file"]).read_text(encoding="utf-8"))
    final0 = spec.get("quality") == "final"
    media = {"duration_s": float(spec.get("seconds", 6.5)), "width": 2160 if final0 else plan0.get("width", 1080), "height": 3840 if final0 else plan0.get("height", 1920), "fps": plan0.get("fps", 30)}
    extra = {"scenes": len(plan0.get("scenes", [])), "audio_items": len(plan0.get("audio", [])), "voice_s": next((a.get("duration_s") for a in plan0.get("audio", []) if a.get("role") == "voice"), None)}
    with costs.track(storage, spec["name"], "render_final" if final0 else "render_preview", media=media, extra=extra):
        return _run(spec, storage, log)


def _prepared(spec, storage, log=print):
    """(plan to render, final?, seconds): same preparation for the single render and for every parallel shard."""
    from .common import stage
    plan = json.loads(Path(spec["plan_file"]).read_text(encoding="utf-8"))
    sec = float(spec.get("seconds", 6.5))
    with stage("assets"):
        ensure_music(plan, storage, log)
        ensure_sfx(plan, storage, log)
    final = spec.get("quality") == "final"   # full plan, full size, -14 LUFS, delivered to Drive (Faiz's Y)
    return (plan if final else trim_plan(plan, sec)), final, sec


def total_frames(p):
    fps = p.get("fps", 30)
    return sum(max(1, int(s["duration_s"] * fps + 0.5)) for s in p["scenes"])


def shard_ranges(n_frames, parts):
    k = -(-n_frames // parts)
    return [(i * k, min(n_frames, (i + 1) * k) - 1) for i in range(parts) if i * k < n_frames]


def shard(spec, storage, part, parts, outdir, log=print):
    """One parallel machine: a video-only piece (part 0..parts-1) or the one sound render (part == 'audio')."""
    from . import render
    p, final, _sec = _prepared(spec, storage, log)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    q = "final" if final else "preview"
    rng = shard_ranges(total_frames(p), parts)[int(part)]   # each piece keeps its own sound; join glues the sound sample-exactly
    res = render.render_plan(p, q, str(outdir / f"part{int(part):02d}.mp4"), storage=storage, frames=rng)
    log(f"SHARD {part}/{parts} ok={res.get('ok')}")
    return res


def join(spec, storage, parts_dir, log=print):
    """Glue the video pieces (stream copy, no re-encode, so quality equals one pass) + the sound, then the normal finish."""
    from . import costs
    plan0 = json.loads(Path(spec["plan_file"]).read_text(encoding="utf-8"))
    final0 = spec.get("quality") == "final"
    media = {"duration_s": float(spec.get("seconds", 6.5)), "width": 2160 if final0 else plan0.get("width", 1080), "height": 3840 if final0 else plan0.get("height", 1920), "fps": plan0.get("fps", 30)}
    with costs.track(storage, spec["name"], "render_final" if final0 else "render_preview", media=media, extra={"parallel": True}):
        return _finish(spec, storage, _glue(spec, parts_dir, log), final0, log)


def _glue(spec, parts_dir, log):
    import subprocess
    pd = Path(parts_dir)
    vids = sorted(pd.rglob("part*.mp4"))
    if not vids:
        raise RuntimeError("join: no video pieces")
    wd = Path(tempfile.mkdtemp(prefix="itcod-join-"))

    def ff(*args):
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("join failed:\n" + (r.stderr or "")[-600:])
    wavs = []
    for i, v in enumerate(vids):   # sound of every piece -> PCM (no AAC joins), then one clean AAC encode
        w = wd / f"a{i:02d}.wav"
        ff("-i", str(v), "-vn", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(w))
        wavs.append(w)
    (wd / "v.txt").write_text("".join(f"file '{v.resolve()}'\n" for v in vids), encoding="utf-8")
    (wd / "a.txt").write_text("".join(f"file '{w}'\n" for w in wavs), encoding="utf-8")
    ff("-f", "concat", "-safe", "0", "-i", str(wd / "a.txt"), "-c:a", "aac", "-b:a", "192k", str(wd / "audio.m4a"))
    out = wd / f"{spec['name']}-sample.mp4"
    ff("-f", "concat", "-safe", "0", "-i", str(wd / "v.txt"), "-i", str(wd / "audio.m4a"), "-map", "0:v:0", "-map", "1:a:0",
       "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out))
    log(f"joined {len(vids)} pieces")
    return out


def _run(spec, storage, log=print):
    from . import render
    from .common import stage
    p, final, sec = _prepared(spec, storage, log)
    wd = Path(tempfile.mkdtemp(prefix="itcod-sample-"))
    out = wd / f"{spec['name']}-sample.mp4"
    with stage("render"):
        res = render.render_plan(p, "final" if final else "preview", str(out), storage=storage)
    return _finish(spec, storage, out, final, log, res)


def _finish(spec, storage, out, final, log, res=None):
    from . import render, review
    from .common import stage
    out = Path(out)
    wd = out.parent
    sec = float(spec.get("seconds", 6.5))
    name = spec["name"]
    res = res or {"ok": out.exists() and out.stat().st_size > 0}
    if final and res.get("ok"):
        from . import finish
        res["loudness"] = finish.normalize_loudness(str(out), -14.0, wd)
        res["drive"] = storage.put_file(out, spec["deliver"])
        log(f"FINAL delivered to {spec['deliver']}")
    log(f"SAMPLE render ok={res.get('ok')} {sec}s")
    times = spec.get("times") or [round(sec * k / 7, 2) for k in range(1, 7)]
    sheet = wd / "frames.jpg"
    with stage("collage"):
        render.contact_sheet(str(out), times, str(sheet), cols=3)
    pack = wd / "pack"
    pack.mkdir()
    (pack / "collage_frames.jpg").write_bytes(sheet.read_bytes())
    (pack / "video.mp4").write_bytes(out.read_bytes())   # small preview, so Faiz can watch it
    for i, rp in enumerate(spec.get("ref_paths", []), 1):   # reference collages from Drive, so Claude can compare side by side
        storage.fetch(rp, pack / f"collage_ref_{i:02d}.jpg")
    with stage("review_publish"):
        pub = review.publish(pack, f"sample-{name}")
    log("REVIEW " + json.dumps(pub))
    return {"ok": bool(res.get("ok")), "check": {k: res.get(k) for k in ("loudness", "safe_zone") if k in res}, "review": pub}
