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
    rc, o, e = sh("git clone -q --depth 1 --branch 3.3.2 https://github.com/facefusion/facefusion.git /kaggle/ff")
    res["steps"]["clone"] = rc
    reqs = [l.strip() for l in open("/kaggle/ff/requirements.txt") if l.strip() and not l.startswith("onnxruntime")]
    rc, o, e = sh([sys.executable, "-m", "pip", "install", "-q", *reqs, "onnxruntime-gpu==1.22.0"], 1800)
    res["steps"]["pip"] = {"rc": rc, "err": e[-400:]}
    # onnxruntime-gpu needs the CUDA/cuDNN libs that pip's nvidia-* wheels ship
    libs = [d for d in glob.glob(sys.prefix + "/lib/python3*/*-packages/nvidia/*/lib")]
    env = dict(os.environ, LD_LIBRARY_PATH=":".join(libs + [os.environ.get("LD_LIBRARY_PATH", "")]))
    rc, o, e = sh([sys.executable, "-c", "import onnxruntime as o; print(o.get_available_providers())"])
    res["steps"]["providers"] = (o or e).strip()[-200:]
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
    p = subprocess.run(cmd, cwd="/kaggle/ff", capture_output=True, text=True, timeout=int(spec.get("swap_budget_s", 9000)), env=env)
    res["steps"]["swap"] = {"rc": p.returncode, "log": ((p.stdout or "") + (p.stderr or ""))[-1500:]}
    res["ok"] = p.returncode == 0 and os.path.exists(out + "/video.mp4")
except Exception:
    res["error_hint"] = traceback.format_exc()[-1200:]
res["total_s"] = round(time.time() - t0, 1)
json.dump(res, open(out + "/result.json", "w"))
'''
