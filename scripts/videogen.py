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

DATASET, KERNEL = "itcod-vgen-in", "itcod-vgen"
MODEL = "unsloth/LTX-2.5-FP8"   # FP8 transformer + stock diffusers parts (model card 2026-11-07)


class EngineBlocked(RuntimeError):
    """The engine may not run now (needs approval, paid flag, or runner missing). Message says what is missing."""


def gate(spec, eval_state=None):
    eng = spec.get("engine", "ltx")
    if eng == "ltx":
        return eng
    if eng == "minimax":
        if not (eval_state or {}).get("minimax_approved"):
            raise EngineBlocked("minimax needs Faiz's Y in chat, then `./run approve-engine minimax --state <eval.json>`")
        raise EngineBlocked("minimax approved, but its runner (big paid GPU) is not built yet")
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
                    "sentencepiece", "imageio", "imageio-ffmpeg"], check=False)
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
    spec = {"engine": "ltx", "model": MODEL, "probe": bool(raw.get("probe")), "prompt": raw.get("prompt", ""),
            "width": int(raw.get("width", 768)), "height": int(raw.get("height", 512)), "fps": int(raw.get("fps", 24)),
            "seed": int(raw.get("seed", 1)), "seconds": seconds, "num_frames": frames_for(seconds, int(raw.get("fps", 24)))}
    spec["has_image"] = bool(image)
    return spec


def prepare(spec, image, work, owner):
    ds, kn = Path(work) / "ds", Path(work) / "kn"
    ds.mkdir(parents=True), kn.mkdir(parents=True)
    (ds / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    if image:
        shutil.copy(image, ds / "in.png")
    (ds / "dataset-metadata.json").write_text(json.dumps(
        {"title": "itcod vgen input", "id": f"{owner}/{DATASET}", "licenses": [{"name": "CC0-1.0"}]}), encoding="utf-8")
    (kn / "vgen_kernel.py").write_text(KERNEL_SRC, encoding="utf-8")
    (kn / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{owner}/{KERNEL}", "title": "itcod vgen", "code_file": "vgen_kernel.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "dataset_sources": [f"{owner}/{DATASET}"], "competition_sources": [], "kernel_sources": []}), encoding="utf-8")
    return ds, kn


def run(spec, image, out_dir, poll_s=20, timeout_s=None):
    """Run the spec on a Kaggle GPU. Returns result dict (always has ok + error_hint) and writes video.mp4 into out_dir when made."""
    timeout_s = timeout_s or int(limits().get("videogen", {}).get("timeout_s", 2400))
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
            while time.time() - t0 < timeout_s:
                time.sleep(poll_s)
                rc, out, err = kg._cli(["kernels", "status", f"{owner}/{KERNEL}"], 120)
                w = kg._status_word(out + err)
                if w == "COMPLETE":
                    break
                if w in ("ERROR", "CANCEL"):
                    log(f"videogen: kernel {w.lower()}")
                    break
            else:
                return {"ok": False, "error_hint": "timeout"}
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
