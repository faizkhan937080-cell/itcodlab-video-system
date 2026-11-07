"""Modal app for the heavy footage engines (LTX-2.5 and MiniMax H3). Runs on Modal's free Starter credit ($30/month, billed per second).
Started by the worker: `modal run scripts/modal_app.py --spec-path S --out-dir D [--image I]` (tokens MODAL_TOKEN_ID / MODAL_TOKEN_SECRET in env).
Model files are cached in a Modal Volume, so each model downloads once. A spec with "probe": true loads and reports, no frames.
MiniMax H3: the first run is a CPU-only repo listing (no GPU, no credit); generation code is added after we know its checkpoint layout."""
import json
import time

import modal

app = modal.App("itcod-footage")
vol = modal.Volume.from_name("itcod-hf-cache", create_if_missing=True)
IMG = (modal.Image.debian_slim(python_version="3.11")
       .pip_install("torch", "diffusers", "transformers", "accelerate", "sentencepiece", "imageio", "imageio-ffmpeg", "pillow",
                    "huggingface_hub", "safetensors"))
ENV = {"HF_HOME": "/cache/hf"}


def _generate(spec, image_bytes):
    import io
    import os
    import torch
    t0 = time.time()
    res = {"ok": False, "probe": bool(spec.get("probe")), "engine": spec["engine"]}
    try:
        res["gpu"] = torch.cuda.get_device_name(0)
        from diffusers import DiffusionPipeline
        pipe = DiffusionPipeline.from_pretrained(spec["model"], torch_dtype=torch.bfloat16)
        res["pipeline_class"] = type(pipe).__name__
        res["load_s"] = round(time.time() - t0, 1)
        for fn in ("enable_model_cpu_offload", "enable_vae_tiling"):
            if hasattr(pipe, fn):
                getattr(pipe, fn)()
        import inspect
        params = list(inspect.signature(pipe.__call__).parameters)
        res["call_params"] = params
        if not spec.get("probe"):
            kw = {"prompt": spec["prompt"], "width": spec["width"], "height": spec["height"],
                  "generator": torch.Generator("cpu").manual_seed(int(spec.get("seed", 1)))}
            if "num_frames" in params:
                kw["num_frames"] = int(spec["num_frames"])
            if image_bytes and "image" in params:
                from PIL import Image
                kw["image"] = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            t1 = time.time()
            out = pipe(**kw)
            res["gen_s"] = round(time.time() - t1, 1)
            from diffusers.utils import export_to_video
            export_to_video(out.frames[0], "/tmp/video.mp4", fps=int(spec.get("fps", 24)))
            res["video"] = open("/tmp/video.mp4", "rb").read()
        res["peak_vram_gb"] = round(torch.cuda.max_memory_allocated() / 2**30, 1)
        res["ok"] = True
    except Exception:
        import traceback
        res["error"] = traceback.format_exc()[-1500:]
    res["total_s"] = round(time.time() - t0, 1)
    vol.commit()
    return res


@app.function(image=IMG, gpu="L40S", timeout=3000, memory=65536, volumes={"/cache": vol}, env=ENV)
def gen_ltx(spec, image_bytes=None):
    return _generate(spec, image_bytes)


@app.function(image=IMG, timeout=300, volumes={"/cache": vol}, env=ENV)
def list_minimax(repo="MiniMaxAI/MiniMax-H3"):
    """CPU only: what is in the MiniMax H3 repo (file names + sizes) and the first 3000 chars of its README. No GPU credit used."""
    from huggingface_hub import HfApi, hf_hub_download
    out = {"ok": True, "files": [], "readme": ""}
    try:
        info = HfApi().model_info(repo, files_metadata=True)
        out["files"] = [{"name": s.rfilename, "gb": round((s.size or 0) / 2**30, 2)} for s in info.siblings][:80]
        out["license"] = (info.card_data or {}).get("license") if info.card_data else None
        out["readme"] = open(hf_hub_download(repo, "README.md"), encoding="utf-8", errors="ignore").read()[:3000]
    except Exception as e:  # noqa: BLE001
        out = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"}
    return out


@app.local_entrypoint()
def main(spec_path: str, out_dir: str, image: str = ""):
    import os
    spec = json.load(open(spec_path))
    os.makedirs(out_dir, exist_ok=True)
    if spec["engine"] == "minimax":
        res = list_minimax.remote()
    else:
        res = gen_ltx.remote(spec, open(image, "rb").read() if image else None)
    video = res.pop("video", None)
    if video:
        open(os.path.join(out_dir, "video.mp4"), "wb").write(video)
    json.dump(res, open(os.path.join(out_dir, "result.json"), "w"), ensure_ascii=False)
    print("done", res.get("ok"))
