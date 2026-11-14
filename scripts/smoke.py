"""Preflight smoke test (Tester). Runs before any long job: 1 picture, 1 depth map, 1 collage, 1 tiny 3D clip, 1 Drive read.
Nothing is saved (tests never save). A failure here stops the long run in minutes, not after an hour."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(raw, stg, log=print):
    """Returns (ok, reason). Only runner-side modes are smoke-tested; GPU-queue modes are skipped (their queue is the cost)."""
    mode, eng = raw.get("mode"), raw.get("engine")
    if not ((mode == "image" and eng == "api") or mode == "parallax"):
        log("SMOKE skipped: mode needs a GPU queue, no cheap test")
        return True, "skipped"
    from . import parallax3d, stills_api
    from .blender3d import contact_sheet
    try:
        import bpy  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "bpy==4.5.3"], check=True)
    with tempfile.TemporaryDirectory(prefix="itcod-smoke-") as wd:
        wd = Path(wd)
        try:
            if mode == "image":
                spec = {**raw, "prompts": raw["prompts"][:1], "width": 256, "height": 448}
                stills_api.make(spec, wd / "st", log=log)
                sid = spec["prompts"][0]["id"]
                img, dep = wd / "st" / f"img_{sid}.png", wd / "st" / f"depth_{sid}.png"
            else:
                sc = raw["scenes"][0]
                img, dep = wd / "i.png", wd / "d.png"
                stg.fetch(f"{raw['stills']}/img_{sc['image']}.png", img)
                stg.fetch(f"{raw['stills']}/depth_{sc['image']}.png", dep)
            assert img.exists() and dep.exists(), "picture or depth map missing"
            rep = parallax3d.render_clip(img, dep, wd / "fr", 0.1, "push", 270, 480, 30)
            fs = sorted((wd / "fr").glob("f_*.png"))
            assert fs, "3D render made no frames"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "30", "-i", str(wd / "fr" / "f_%04d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(wd / "t.mp4")], check=True)
            assert (wd / "t.mp4").stat().st_size > 1000, "clip file empty"
            contact_sheet(wd / "fr", max_tiles=min(3, len(fs)))
            assert (wd / "fr" / "collage.jpg").exists(), "collage not made"
            stg.ensure_dir("output")   # Drive reachable (folder already exists, nothing new saved)
            log("SMOKE OK", json.dumps({"frames": rep.get("frames"), "sec_per_frame": rep.get("sec_per_frame")}))
            return True, "ok"
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {str(e)[:200]}"
