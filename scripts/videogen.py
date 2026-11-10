"""Footage engines for what Remotion cannot make (realistic shots). Rules: rulebooks/21-evaluator.md.
ltx = LTX-2.5 on a free Kaggle GPU (default, no approval). minimax / veo = gated: need Faiz's Y / allow_paid, runner not built yet.
Same Kaggle plumbing as kaggle_gpu.py. A spec with "probe": true only loads the model and reports class, signature, GPU, memory (no video)
so the first live run teaches us what the 22B model needs on a 16 GB card before any GPU time is spent on frames.
Secrets stay in env (KAGGLE_USERNAME, KAGGLE_KEY); nothing secret is logged."""
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from . import kaggle_gpu as kg
from .common import ROOT, limits, log, tail

DATASET, KERNEL = "itcod-vgen-in2", "itcod-vgen3"
MODEL = {"wan": "Wan-AI/Wan2.2-TI2V-5B-Diffusers", "ltx": "Lightricks/LTX-2.5-Diffusers"}   # wan first: 5B fits a free Kaggle T4; ltx 22B (38 GB) likely too big for Kaggle disk


class EngineBlocked(RuntimeError):
    """The engine may not run now (needs approval, paid flag, or runner missing). Message says what is missing."""


def gate(spec, eval_state=None):
    eng = spec.get("engine", "wan")
    if eng in ("wan", "ltx"):
        return eng
    if eng == "minimax":
        if not (eval_state or {}).get("minimax_approved"):
            raise EngineBlocked("minimax needs Faiz's Y in chat, then `./run approve-engine minimax --state <eval.json>`")
        return eng
    if eng == "veo":
        if not spec.get("allow_paid"):
            raise EngineBlocked("veo is paid: only on Faiz's command, script must carry allow_paid")
        raise EngineBlocked("veo runner (Vertex AI) is not built yet")
    raise EngineBlocked(f"unknown engine {eng!r}")


def frames_for(seconds, fps=24):
    """LTX wants 8k+1 frames."""
    n = max(9, round(seconds * fps))
    return -(-(n - 1) // 8) * 8 + 1


KERNEL_SRC = '''import glob, inspect, json, os, subprocess, sys, time, traceback
os.environ["HF_HOME"] = "/tmp/hf"
src = os.path.dirname(glob.glob("/kaggle/input/**/spec.json", recursive=True)[0])
spec = json.load(open(os.path.join(src, "spec.json")))
res = {"ok": False, "probe": bool(spec.get("probe"))}
t0 = time.time()
try:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "diffusers", "transformers", "accelerate",
                    "sentencepiece", "imageio", "imageio-ffmpeg", "-U", "protobuf"], check=False)
    import torch
    res["gpu"] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    res["vram_gb"] = [round(torch.cuda.get_device_properties(i).total_memory / 2**30, 1) for i in range(torch.cuda.device_count())]
    from diffusers import DiffusionPipeline
    pipe = DiffusionPipeline.from_pretrained(spec["model"], torch_dtype=torch.bfloat16)
    res["pipeline_class"] = type(pipe).__name__
    res["load_s"] = round(time.time() - t0, 1)
    for fn in ("enable_model_cpu_offload", "enable_vae_tiling"):
        if hasattr(pipe, fn):
            getattr(pipe, fn)()
    params = list(inspect.signature(pipe.__call__).parameters)
    res["call_params"] = params
    if not spec.get("probe"):
        kw = {"prompt": spec["prompt"], "width": spec["width"], "height": spec["height"],
              "generator": torch.Generator("cpu").manual_seed(int(spec.get("seed", 1)))}
        if "num_frames" in params:
            kw["num_frames"] = int(spec["num_frames"])
        img = os.path.join(src, "in.png")
        if os.path.exists(img) and "image" in params:
            from PIL import Image
            kw["image"] = Image.open(img).convert("RGB")
        t1 = time.time()
        out = pipe(**kw)
        res["gen_s"] = round(time.time() - t1, 1)
        res["output_fields"] = [k for k in dir(out) if not k.startswith("_")][:20]
        from diffusers.utils import export_to_video
        export_to_video(out.frames[0], "/kaggle/working/video.mp4", fps=int(spec.get("fps", 24)))
    res["peak_vram_gb"] = round(max(torch.cuda.max_memory_allocated(i) for i in range(torch.cuda.device_count())) / 2**30, 1)
    res["ok"] = True
except Exception:
    res["error"] = traceback.format_exc()[-1500:]
res["total_s"] = round(time.time() - t0, 1)
json.dump(res, open("/kaggle/working/result.json", "w"))
print("done", res["ok"])
'''


def build_spec(raw, image=None):
    seconds = float(raw.get("seconds", 4))
    eng = raw.get("engine", "wan")
    spec = {"engine": eng, "model": MODEL.get(eng, MODEL["wan"]), "probe": bool(raw.get("probe")), "prompt": raw.get("prompt", ""),
            "width": int(raw.get("width", 768)), "height": int(raw.get("height", 512)), "fps": int(raw.get("fps", 24)),
            "seed": int(raw.get("seed", 1)), "seconds": seconds, "num_frames": frames_for(seconds, int(raw.get("fps", 24)))}
    spec["has_image"] = bool(image)
    if raw.get("mode") == "gguf":
        spec["mode"] = "gguf"
        for k in ("gguf_repo", "gguf_file", "gen_budget_s", "offload", "watchdog_s"):
            if raw.get(k):
                spec[k] = raw[k]
    if raw.get("mode") == "faceswap":   # face swap test (scripts/faceswap_kaggle.py)
        spec.update(mode="faceswap", test=True)
        for k in ("quality", "reference_frame", "reference_position", "reference_distance", "swap_budget_s", "timeout_s"):
            if raw.get(k) is not None:
                spec[k] = raw[k]
    if raw.get("mode") == "h3":   # MiniMax-H3 full model, 4-bit, one component at a time (scripts/videogen_h3.py)
        spec.update(mode="h3", model="MiniMaxAI/MiniMax-H3", workflow=raw.get("workflow", "fl2va"))
        for k in ("watchdog_s", "gen_budget_s", "timeout_s", "num_frames", "height", "width", "seed", "steps", "dit_gpu0_gib", "dit_gpu1_gib"):
            if raw.get(k):
                spec[k] = raw[k]
    return spec


def prepare(spec, image, work, owner):
    ds, kn = Path(work) / "ds", Path(work) / "kn"
    ds.mkdir(parents=True), kn.mkdir(parents=True)
    (ds / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    if spec.get("mode") == "faceswap":
        shutil.copy(spec.pop("_video"), ds / "in.mp4")
        shutil.copy(spec.pop("_face"), ds / "face.png")
        (ds / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    elif image:
        shutil.copy(image, ds / "in.png")
    if os.environ.get("HF_TOKEN"):  # private Kaggle dataset only; lets the kernel read gated Hugging Face repos
        (ds / "hf.txt").write_text(os.environ["HF_TOKEN"], encoding="utf-8")
    (ds / "dataset-metadata.json").write_text(json.dumps(
        {"title": "itcod vgen input", "id": f"{owner}/{DATASET}", "licenses": [{"name": "CC0-1.0"}]}), encoding="utf-8")
    if spec.get("mode") == "gguf":
        from .videogen_gguf import KERNEL_SRC_GGUF
        (kn / "vgen_kernel.py").write_text(KERNEL_SRC_GGUF, encoding="utf-8")
    elif spec.get("mode") == "faceswap":
        from .faceswap_kaggle import KERNEL_SRC_FACESWAP
        (kn / "vgen_kernel.py").write_text(KERNEL_SRC_FACESWAP, encoding="utf-8")
    elif spec.get("mode") == "h3":
        from .videogen_h3 import KERNEL_SRC_H3
        (kn / "vgen_kernel.py").write_text(KERNEL_SRC_H3, encoding="utf-8")
    else:
        (kn / "vgen_kernel.py").write_text(KERNEL_SRC, encoding="utf-8")
    (kn / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{owner}/{KERNEL}", "title": KERNEL.replace("-", " "), "code_file": "vgen_kernel.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "dataset_sources": [f"{owner}/{DATASET}"], "competition_sources": [], "kernel_sources": []}), encoding="utf-8")
    return ds, kn


def run(spec, image, out_dir, poll_s=20, timeout_s=None):
    """Run the spec on a Kaggle GPU. Returns result dict (always has ok + error_hint) and writes video.mp4 into out_dir when made."""
    timeout_s = timeout_s or spec.get("timeout_s") or int(limits().get("videogen", {}).get("timeout_s", 2400))
    owner = os.environ.get("KAGGLE_USERNAME", "")
    if not owner or not os.environ.get("KAGGLE_KEY") or not shutil.which("kaggle"):
        return {"ok": False, "error_hint": "Kaggle credentials or CLI missing (secrets KAGGLE_USERNAME, KAGGLE_KEY)"}
    t0 = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="itcod-vgen-") as work:
            ds, kn = prepare(spec, image, work, owner)
            rc, out, err = kg._cli(["datasets", "status", f"{owner}/{DATASET}"], 120)
            verb = ["datasets", "version", "-p", str(ds), "-m", "vgen " + str(int(t0)), "-r", "skip"] \
                if rc == 0 and "ready" in (out + err).lower() else ["datasets", "create", "-p", str(ds), "-r", "skip"]
            rc, out, err = kg._cli(verb, 600)
            if rc != 0:
                return {"ok": False, "error_hint": "dataset upload failed: " + tail(err or out, 2)}
            for _ in range(40):
                rc, out, err = kg._cli(["datasets", "status", f"{owner}/{DATASET}"], 120)
                if rc == 0 and "ready" in (out + err).lower():
                    break
                time.sleep(5)
            else:
                return {"ok": False, "error_hint": "dataset never became ready"}
            rc, out, err = kg._cli(["kernels", "push", "-p", str(kn)], 300)
            if rc != 0:
                return {"ok": False, "error_hint": "kernel push failed: " + tail(err or out, 2)}
            w = ""
            while time.time() - t0 < timeout_s:
                time.sleep(poll_s)
                rc, out, err = kg._cli(["kernels", "status", f"{owner}/{KERNEL}"], 120)
                w = kg._status_word(out + err) or w
                if w == "COMPLETE":
                    break
                if w in ("ERROR", "CANCEL"):
                    log(f"videogen: kernel {w.lower()}")
                    break
            else:   # say WHERE it was stuck (QUEUED = no free GPU / GPU not enabled on account; RUNNING = too slow)
                return {"ok": False, "error_hint": f"timeout (last kaggle status: {w or 'unknown'})"}
            outdir = Path(work) / "out"
            rc, out, err = kg._cli(["kernels", "output", f"{owner}/{KERNEL}", "-p", str(outdir)], 900)
            rf = outdir / "result.json"
            if not rf.exists():
                return {"ok": False, "error_hint": "no result.json from the kernel: " + tail(err or out, 2)}
            res = json.loads(rf.read_text(encoding="utf-8"))
            res["kaggle_wall_s"] = round(time.time() - t0)
            vid = outdir / "video.mp4"
            if res.get("ok") and vid.exists() and not res.get("probe"):
                Path(out_dir).mkdir(parents=True, exist_ok=True)
                shutil.copy(vid, Path(out_dir) / "video.mp4")
            return res
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error_hint": f"{type(e).__name__}"}


def run_modal(spec, image, out_dir, timeout_s=3300):
    """ltx / minimax on Modal (free Starter credit). Returns the result dict; the clip lands in out_dir/video.mp4 when made."""
    import subprocess
    if not (os.environ.get("MODAL_TOKEN_ID") and os.environ.get("MODAL_TOKEN_SECRET")) or not shutil.which("modal"):
        return {"ok": False, "error_hint": "Modal tokens or CLI missing (secrets MODAL_TOKEN_ID, MODAL_TOKEN_SECRET)"}
    t0 = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="itcod-modal-") as work:
            sp = Path(work) / "spec.json"
            sp.write_text(json.dumps(spec), encoding="utf-8")
            cmd = ["modal", "run", str(ROOT / "scripts" / "modal_app.py"), "--spec-path", str(sp), "--out-dir", str(out_dir)]
            if image:
                cmd += ["--image", str(image)]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
            rf = Path(out_dir) / "result.json"
            if not rf.exists():
                return {"ok": False, "error_hint": "modal gave no result: " + tail((p.stderr or p.stdout or ""), 3)}
            res = json.loads(rf.read_text(encoding="utf-8"))
            res["modal_wall_s"] = round(time.time() - t0)
            return res
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error_hint": type(e).__name__}


def reel_frames(link, wd, frame_s=0.3):
    """Test input from a reel link (nothing saved to Drive): download it (polite, guarded), take the first-frame
    png for the model and a 3x2 collage for Claude to look at. Returns dict with paths + basic metadata."""
    from .common import run_cmd
    from .jobs import merge_streams, pick_source
    from .netguard import config as net_config, guard, host_key
    from .security import require_safe
    wd = Path(wd)
    wd.mkdir(parents=True, exist_ok=True)
    cfg = net_config()
    cmd = ["yt-dlp", "-f", "bv*+ba/b", "--merge-output-format", "mp4", "--no-playlist", "--write-info-json",
           "-o", str(wd / "source.%(ext)s"), *cfg["yt_dlp_polite"]]
    ck = os.environ.get("ITCOD_COOKIES")
    if ck and Path(ck).exists():
        cmd += ["--cookies", ck]
    key = host_key(link, cfg)
    g = guard()
    g.before(key)
    rc, out, err = run_cmd(cmd + [link], timeout=900)
    if rc != 0:
        g.after(key, None, err or out)
        raise RuntimeError("reel download failed: " + tail(err or out, 3))
    merge_streams(wd)
    src = pick_source(list(wd.glob("source.*")))
    require_safe(src, "video")
    rc, out, err = run_cmd(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height:format=duration", "-of", "json", str(src)], timeout=60)
    info = json.loads(out or "{}")
    st = (info.get("streams") or [{}])[0]
    dur = float((info.get("format") or {}).get("duration") or 1.0)
    first = wd / "first.png"
    run_cmd(["ffmpeg", "-y", "-v", "error", "-ss", str(frame_s), "-i", str(src), "-frames:v", "1", str(first)], timeout=120)
    pack = wd / "pack"
    pack.mkdir(exist_ok=True)
    run_cmd(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", f"fps=6/{max(dur, 0.5):.3f},scale=360:-2,tile=3x2",
             "-frames:v", "1", "-q:v", "4", str(pack / "collage_01.jpg")], timeout=180)
    if not first.exists():
        raise RuntimeError("could not take the first frame")
    return {"first": str(first), "pack": str(pack), "src": str(src), "duration_s": round(dur, 2),
            "width": st.get("width"), "height": st.get("height")}
