"""Stills on the GitHub runner, no GPU, no Kaggle: SDXL base + SDXL-Lightning 4-step on CPU (one engine for every picture = one look; free APIs 410/402 on 14 Nov).
Depth maps by Depth Anything V2 Small on CPU. Writes img_<id>.png, depth_<id>.png, engine.json (engine_used per picture)."""
import io
import re
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

from . import netguard

HF = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"


def _get(url, headers=None, body=None, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", "User-Agent": "itcodlab/1.0", **(headers or {})})

    def go():
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    return netguard.guard().call("stills_api", go)


def one(prompt, w, h, seed):
    """Returns (png_bytes, engine_name). Tries each free route; raises RuntimeError with the reasons."""
    why = []
    try:
        return _lightning(prompt, w, h, seed), "sdxl-lightning-cpu"
    except Exception as e:  # noqa: BLE001
        why.append(f"lightning {type(e).__name__} {str(e)[:120]}")
    raise RuntimeError("; ".join(why))


_PIPE = []


def _lightning(prompt, w, h, seed):
    """SDXL base + ByteDance SDXL-Lightning 4-step UNet (OpenRAIL++, commercial OK), on the runner's CPU."""
    import torch
    from diffusers import EulerDiscreteScheduler, StableDiffusionXLPipeline, UNet2DConditionModel
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    if not _PIPE:
        base = "stabilityai/stable-diffusion-xl-base-1.0"
        unet = UNet2DConditionModel.from_config(base, subfolder="unet")
        unet.load_state_dict(load_file(hf_hub_download("ByteDance/SDXL-Lightning", "sdxl_lightning_4step_unet.safetensors")))
        pipe = StableDiffusionXLPipeline.from_pretrained(base, unet=unet, torch_dtype=torch.float32)
        pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")
        _PIPE.append(pipe)
    w, h = (w // 8) * 8, (h // 8) * 8
    img = _PIPE[0](prompt, num_inference_steps=4, guidance_scale=0.0, width=min(w, 768), height=min(h, 1344),
                   generator=torch.Generator("cpu").manual_seed(seed)).images[0]
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


CLIP_MAX = 75   # CLIP text encoder keeps 77 tokens (2 are start/end); the rest of a prompt is silently dropped


def cut_report(prompt):
    """-> (tokens, dropped_text). Rough token count (word pieces) so a too-long prompt is SEEN, not silently cut."""
    toks = re.findall(r"\w+|[^\w\s]", prompt)
    if len(toks) <= CLIP_MAX:
        return len(toks), ""
    words = prompt.split()
    keep, n = [], 0
    for w in words:
        n += len(re.findall(r"\w+|[^\w\s]", w))
        if n > CLIP_MAX:
            break
        keep.append(w)
    return len(toks), " ".join(words[len(keep):])


def make(spec, out_dir, log=print, fetch=None, put=None):
    """fetch(name, dest)->bool pulls a finished file from Drive (resume); put(path) saves each file the moment it exists (never lose work)."""
    import subprocess
    import sys
    try:
        import transformers  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--index-url", "https://download.pytorch.org/whl/cpu", "torch"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers", "diffusers", "accelerate", "safetensors", "huggingface_hub", "pillow", "numpy"], check=True)
    from PIL import Image
    from . import parallax3d
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    w, h, seed = int(spec.get("width", 864)), int(spec.get("height", 1536)), int(spec.get("seed", 7))
    rep = {}
    for i, p in enumerate(spec["prompts"]):
        img = out / f"img_{p['id']}.png"
        for nm in (img.name, f"depth_{p['id']}.png"):
            if fetch and not (out / nm).exists() and fetch(nm, out / nm):
                log(f"RESUME {nm} from Drive")
        n_tok, lost = cut_report(p["prompt"])
        if lost:
            log(f"PROMPT_CUT {p['id']}: {n_tok} tokens, CLIP drops: ...{lost[:80]}")
            if not img.exists() and not spec.get("allow_cut"):
                raise ValueError(f"prompt {p['id']} is {n_tok} tokens: the model would drop the end ({lost[:60]}...). Shorten it (guards.prompts_fit)")
        if not img.exists():
            raw, eng = one(p["prompt"], w, h, seed + i)
            Image.open(io.BytesIO(raw)).convert("RGB").save(img)
            rep[p["id"]] = eng
            log(f"STILL {p['id']} {eng}")
            if put:
                put(img)
        dep = out / f"depth_{p['id']}.png"
        if not dep.exists():
            parallax3d.depth_map(img, dep)
            if put:
                put(dep)
    (out / "engine.json").write_text(json.dumps(rep, indent=1))
    return rep
