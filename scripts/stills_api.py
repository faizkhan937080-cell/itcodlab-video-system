"""Stills on the GitHub runner, no GPU, no Kaggle: free image APIs (HF router FLUX.1-schnell, then Pollinations flux).
Depth maps by Depth Anything V2 Small on CPU. Writes img_<id>.png, depth_<id>.png, engine.json (engine_used per picture)."""
import io
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
    tok = os.environ.get("HF_TOKEN", "").strip()
    if tok:
        try:
            raw = _get(HF, {"Authorization": f"Bearer {tok}", "Accept": "image/png"},
                       {"inputs": prompt, "parameters": {"width": w, "height": h, "num_inference_steps": 4, "seed": seed}})
            return raw, "hf-flux-schnell"
        except Exception as e:  # noqa: BLE001
            why.append(f"hf {type(e).__name__} {str(e)[:80]}")
    try:
        q = urllib.parse.quote(prompt)
        raw = _get(f"https://image.pollinations.ai/prompt/{q}?model=flux&width={w}&height={h}&seed={seed}&nologo=true&private=true")
        return raw, "pollinations-flux"
    except Exception as e:  # noqa: BLE001
        why.append(f"pollinations {type(e).__name__} {str(e)[:80]}")
    raise RuntimeError("; ".join(why))


def make(spec, out_dir, log=print):
    import subprocess
    import sys
    try:
        import transformers  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--index-url", "https://download.pytorch.org/whl/cpu", "torch"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers", "pillow", "numpy"], check=True)
    from PIL import Image
    from . import parallax3d
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    w, h, seed = int(spec.get("width", 864)), int(spec.get("height", 1536)), int(spec.get("seed", 7))
    rep = {}
    for i, p in enumerate(spec["prompts"]):
        img = out / f"img_{p['id']}.png"
        if not img.exists():
            raw, eng = one(p["prompt"], w, h, seed + i)
            Image.open(io.BytesIO(raw)).convert("RGB").save(img)
            rep[p["id"]] = eng
            log(f"STILL {p['id']} {eng}")
        dep = out / f"depth_{p['id']}.png"
        if not dep.exists():
            parallax3d.depth_map(img, dep)
    (out / "engine.json").write_text(json.dumps(rep, indent=1))
    return rep
