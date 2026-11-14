"""Free photoreal stills on a Kaggle T4: FLUX.1-schnell (Apache-2.0, commercial use OK), GGUF Q8 transformer, 4 steps.
One still per scene; Remotion then moves them (slow push, parallax, wisps, captions). mode "image" in a videogen spec.
Spec: {"mode": "image", "engine": "flux", "width", "height", "steps", "seed", "prompts": [{"id", "prompt"}], "test"?}
Every image is timed; a black/NaN image (fp16 overflow on T4) retries once in bf16."""

KERNEL_SRC_IMG = '''import glob, json, os, subprocess, sys, time, traceback
os.environ["HF_HOME"] = "/tmp/hf"
os.environ["HF_HUB_DISABLE_SHARED_BLOBS"] = "1"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
src = os.path.dirname(glob.glob("/kaggle/input/**/spec.json", recursive=True)[0])
spec = json.load(open(os.path.join(src, "spec.json")))
if os.path.exists(os.path.join(src, "hf.txt")):
    os.environ["HF_TOKEN"] = open(os.path.join(src, "hf.txt")).read().strip()
res = {"ok": False, "mode": "image", "images": [], "steps": {}}
T0 = time.time()
def dump():
    res["total_s"] = round(time.time() - T0, 1)
    json.dump(res, open("/kaggle/working/result.json", "w"), default=str)
try:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "diffusers", "transformers", "accelerate",
                    "sentencepiece", "gguf", "protobuf"], check=False)
    import numpy as np, torch
    from huggingface_hub import hf_hub_download, list_repo_files
    from diffusers import FluxPipeline, FluxTransformer2DModel, GGUFQuantizationConfig
    res["gpu"] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    repo = spec.get("gguf_repo", "city96/FLUX.1-schnell-gguf")
    files = [f for f in list_repo_files(repo) if f.endswith(".gguf")]
    pick = next((f for q in ("Q8_0", "Q6_K", "Q5_K_S", "Q4_K_S") for f in files if q in f), files[0])
    res["gguf"] = pick
    path = hf_hub_download(repo, pick)
    def load(dtype):
        t = time.time()
        tr = FluxTransformer2DModel.from_single_file(path, quantization_config=GGUFQuantizationConfig(compute_dtype=dtype),
                                                     torch_dtype=dtype, config="black-forest-labs/FLUX.1-schnell", subfolder="transformer", token=tok)
        p = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-schnell", transformer=tr, torch_dtype=dtype, token=tok)
        p.enable_model_cpu_offload()
        p.vae.enable_tiling()
        res["steps"]["load_" + str(dtype).split(".")[-1]] = round(time.time() - t, 1)
        dump()
        return p
    def bad(img):
        a = np.asarray(img).astype("float32")
        return (not np.isfinite(a).all()) or a.std() < 3.0
    tok = os.environ.get("HF_TOKEN")
    dtype = torch.float16
    try:
        pipe = load(dtype)
    except Exception:   # FLUX repo gated for this HF account: fall back to SDXL base (OpenRAIL++-M, commercial use allowed, not gated)
        res["steps"]["flux_load_error"] = traceback.format_exc()[-400:]
        from diffusers import StableDiffusionXLPipeline
        t = time.time()
        pipe = StableDiffusionXLPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", torch_dtype=torch.float16,
                                                         variant="fp16", use_safetensors=True).to("cuda")
        pipe.enable_vae_tiling()
        res["engine_used"] = "sdxl-base-1.0"
        res["steps"]["load_sdxl"] = round(time.time() - t, 1)
        spec["steps"], spec["width"], spec["height"] = 30, 768, 1344
        dump()
    for i, item in enumerate(spec["prompts"]):
        for attempt in range(2):
            t = time.time()
            kw = dict(width=int(spec.get("width", 864)), height=int(spec.get("height", 1536)),
                      num_inference_steps=int(spec.get("steps", 4)), generator=torch.Generator("cpu").manual_seed(int(spec.get("seed", 7)) + i))
            if res.get("engine_used") == "sdxl-base-1.0":
                kw.update(guidance_scale=6.0, negative_prompt="text, watermark, cartoon, illustration, blurry, low quality, deformed")
            else:
                kw.update(guidance_scale=0.0, max_sequence_length=256)
            img = pipe(item["prompt"], **kw).images[0]
            if bad(img) and dtype == torch.float16 and not res.get("engine_used"):
                res["steps"]["fp16_black"] = item["id"]
                del pipe; torch.cuda.empty_cache()
                dtype = torch.bfloat16
                pipe = load(dtype)
                continue
            break
        name = "img_" + item["id"] + ".png"
        img.save("/kaggle/working/" + name)
        res["images"].append({"id": item["id"], "file": name, "s": round(time.time() - t, 1), "dtype": str(dtype)})
        dump()
    try:   # depth maps for the 3D parallax move (Depth Anything V2 Small, Apache-2.0)
        del pipe; torch.cuda.empty_cache()
        from PIL import Image
        from transformers import pipeline as hfpipe
        t = time.time()
        dp = hfpipe("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=0)
        for it in res["images"]:
            im = Image.open("/kaggle/working/" + it["file"]).convert("RGB")
            d = dp(im)["predicted_depth"].squeeze().float().cpu().numpy()
            d = (d - d.min()) / max(1e-6, float(d.max() - d.min()))
            Image.fromarray((d * 65535).astype("uint16")).resize(im.size, Image.BICUBIC).save("/kaggle/working/depth_" + it["id"] + ".png")
        res["steps"]["depth_s"] = round(time.time() - t, 1)
    except Exception:
        res["steps"]["depth_error"] = traceback.format_exc()[-600:]
    dump()
    res["peak_vram_gb"] = round(max(torch.cuda.max_memory_allocated(i) for i in range(torch.cuda.device_count())) / 2**30, 1)
    res["ok"] = len(res["images"]) == len(spec["prompts"])
except Exception:
    res["error"] = traceback.format_exc()[-1500:]
dump()
print("done", res["ok"])
'''


def collage(img_dir, out_name="collage_images.jpg", tile_w=360):
    """Contact sheet of the made stills (what Claude looks at)."""
    from pathlib import Path
    from PIL import Image, ImageDraw
    fs = sorted(Path(img_dir).glob("img_*.png"))
    if not fs:
        return None
    ims = [Image.open(f).convert("RGB") for f in fs]
    th = round(ims[0].height * tile_w / ims[0].width)
    cols = min(4, len(ims))
    rows = -(-len(ims) // cols)
    sheet = Image.new("RGB", (tile_w * cols, th * rows), "black")
    for i, (f, im) in enumerate(zip(fs, ims)):
        x, y = (i % cols) * tile_w, (i // cols) * th
        sheet.paste(im.resize((tile_w, th)), (x, y))
        ImageDraw.Draw(sheet).text((x + 6, y + 6), f.stem, fill="white")
    p = Path(img_dir) / out_name
    sheet.save(p, quality=88)
    return str(p)
