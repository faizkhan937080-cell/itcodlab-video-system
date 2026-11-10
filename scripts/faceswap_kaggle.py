"""Face swap test on a Kaggle GPU (FaceFusion 3.3.2, OpenRAIL-AS licence; models download from FaceFusion's own releases).

Input dataset: in.mp4 (the reel) + face.png (one face, front view) + spec.json. Output: video.mp4 + result.json.
Used only for quality TESTS (spec "test": true): the result goes to the review branch, never to Drive.
Quality defaults = highest: hyperswap_1b_256 at 1024 pixel boost, box+occlusion mask, GPEN 1024 enhancer, x264 crf 16 (visually lossless; quality 69 in FaceFusion scale).
"""

KERNEL_SRC_FACESWAP = r'''import glob, json, os, subprocess, sys, time, traceback
t0 = time.time()
src = os.path.dirname(glob.glob("/kaggle/input/**/spec.json", recursive=True)[0])
spec = json.load(open(os.path.join(src, "spec.json")))
res = {"ok": False, "mode": "faceswap", "steps": {}}
out = "/kaggle/working"
def sh(cmd, timeout=3600):
    p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "")[-1500:], (p.stderr or "")[-1500:]
try:
    print("step clone", flush=True)
    rc, o, e = sh("git clone -q --depth 1 --branch 3.3.2 https://github.com/facefusion/facefusion.git /kaggle/ff")
    res["steps"]["clone"] = rc
    # pins dropped: Kaggle's newer Python has no wheel for onnx==1.17 (run 1 failed building it); numpy stays Kaggle's own
    reqs = [l.split("==")[0].strip() for l in open("/kaggle/ff/requirements.txt")
            if l.strip() and not l.startswith(("onnxruntime", "numpy"))]
    rc, o, e = sh([sys.executable, "-m", "pip", "install", "-q", "--only-binary=onnx", *reqs, "onnxruntime-gpu"], 1800)
    res["steps"]["pip"] = {"rc": rc, "err": e[-400:]}
    print("step pip", rc, round(time.time() - t0), flush=True)
    # onnxruntime-gpu needs the CUDA/cuDNN libs that pip's nvidia-* wheels ship
    libs = [d for d in glob.glob(sys.prefix + "/lib/python3*/*-packages/nvidia/*/lib")]
    env = dict(os.environ, LD_LIBRARY_PATH=":".join(libs + [os.environ.get("LD_LIBRARY_PATH", "")]))
    rc, o, e = sh([sys.executable, "-c", "import onnxruntime as o; print(o.get_available_providers())"])
    res["steps"]["providers"] = (o or e).strip()[-200:]
    print("step providers", res["steps"]["providers"], flush=True)
    json.dump(res, open(out + "/result.json", "w"))   # early result: a stopped kernel still tells how far it got
    q = spec.get("quality", {})
    cmd = [sys.executable, "facefusion.py", "headless-run",
           "-s", os.path.join(src, "face.png"), "-t", os.path.join(src, "in.mp4"), "-o", out + "/video.mp4",
           "--processors", *q.get("processors", ["face_swapper", "face_enhancer"]),
           "--face-swapper-model", q.get("swapper", "hyperswap_1b_256"),
           "--face-swapper-pixel-boost", q.get("pixel_boost", "1024x1024"),
           "--face-enhancer-model", q.get("enhancer", "gpen_bfr_1024"),
           "--face-enhancer-blend", str(q.get("enhancer_blend", 70)),
           "--face-selector-mode", "reference",
           "--reference-frame-number", str(spec.get("reference_frame", 0)),
           "--reference-face-position", str(spec.get("reference_position", 0)),
           "--reference-face-distance", str(spec.get("reference_distance", 0.5)),
           "--face-mask-types", "box", "occlusion",
           "--output-video-encoder", "libx264", "--output-video-preset", q.get("preset", "slow"),
           "--output-video-quality", str(q.get("crf_quality", 69)),
           "--execution-providers", "cuda", "--execution-thread-count", str(q.get("threads", 8))]
    print("step swap start", round(time.time() - t0), flush=True)
    p = subprocess.run(cmd, cwd="/kaggle/ff", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                       timeout=int(spec.get("swap_budget_s", 9000)), env=env)
    print((p.stdout or "")[-3000:], flush=True)
    res["steps"]["swap"] = {"rc": p.returncode, "log": (p.stdout or "")[-1500:]}
    res["ok"] = p.returncode == 0 and os.path.exists(out + "/video.mp4")
except Exception:
    res["error_hint"] = traceback.format_exc()[-1200:]
res["total_s"] = round(time.time() - t0, 1)
json.dump(res, open(out + "/result.json", "w"))
'''


def run_chunks(spec, src, face, cache_dir, out_path, run_one, chunk_s=9.0, fps=24, log=print):
    """Resumable face swap: the reel is cut into ~chunk_s pieces; each finished piece is kept in cache_dir
    (GitHub Actions cache keeps it between runs). A stopped run starts again at the first missing piece, never from 0.
    The reference frame (only the person to swap is on screen) is put in front of every piece as frame 0, so
    FaceFusion always picks the same person; that frame is cut off again after the swap.
    run_one(spec, wd) -> result dict and wd/video.mp4. Returns {"ok", "chunks", "done", "skipped", ...}."""
    import json, subprocess, tempfile
    from pathlib import Path

    def ff(*args):
        subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True, timeout=1800)

    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(src)],
                       capture_output=True, text=True, timeout=60)
    dur = float(json.loads(p.stdout or "{}").get("format", {}).get("duration") or 0)
    n = max(1, int(-(-dur // chunk_s)))
    ref_t = int(spec.get("reference_frame", 0)) / fps
    ref_png = cache / "ref.png"
    if not ref_png.exists():
        ff("-ss", f"{ref_t:.3f}", "-i", str(src), "-frames:v", "1", str(ref_png))
    done, skipped, res = [], [], {}
    for i in range(n):
        out_i = cache / f"out_{i:02d}.mp4"
        if out_i.exists() and out_i.stat().st_size > 0:
            skipped.append(i)
            continue
        with tempfile.TemporaryDirectory(prefix=f"itcod-fs{i}-") as wd:
            wd = Path(wd)
            piece = wd / "in.mp4"
            ff("-loop", "1", "-framerate", str(fps), "-t", f"{1 / fps:.5f}", "-i", str(ref_png),
               "-ss", f"{i * chunk_s:.3f}", "-t", f"{chunk_s:.3f}", "-i", str(src),
               "-filter_complex", f"[0:v]scale=1080:1920,fps={fps},format=yuv420p[a];[1:v]fps={fps},format=yuv420p[b];[a][b]concat=n=2:v=1[v]",
               "-map", "[v]", "-an", "-c:v", "libx264", "-crf", "12", "-preset", "fast", str(piece))
            s = dict(spec, _video=str(piece), _face=str(face), reference_frame=0)
            log(f"faceswap piece {i + 1}/{n} start")
            res = run_one(s, wd / "o")
            vid = wd / "o" / "video.mp4"
            if not (res.get("ok") and vid.exists()):
                return {"ok": False, "chunks": n, "done": done, "skipped": skipped, "failed_at": i, "piece_result": res}
            ff("-i", str(vid), "-vf", "select=gte(n\\,1),setpts=PTS-STARTPTS", "-an", "-c:v", "libx264",
               "-crf", "16", "-preset", "slow", str(out_i))
            done.append(i)
            log(f"faceswap piece {i + 1}/{n} done")
    lst = cache / "list.txt"
    lst.write_text("".join(f"file '{cache / f'out_{i:02d}.mp4'}'\n" for i in range(n)), encoding="utf-8")
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(src), "-map", "0:v", "-map", "1:a?",
       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out_path))
    return {"ok": True, "chunks": n, "done": done, "skipped": skipped, "last_piece": res}
