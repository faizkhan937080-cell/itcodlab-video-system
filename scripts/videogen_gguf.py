"""Kaggle kernel for the FREE GGUF route (LTX-2.5 Q4 + MiniMax H3 survey) on 2x T4. Every step is timed and logged to result.json
so one run shows exactly where it breaks. mode "gguf" in the spec selects this kernel (videogen.prepare)."""

KERNEL_SRC_GGUF = '''import glob, json, os, shutil, subprocess, sys, time, traceback
os.environ["HF_HOME"] = "/tmp/hf"
src = os.path.dirname(glob.glob("/kaggle/input/**/spec.json", recursive=True)[0])
spec = json.load(open(os.path.join(src, "spec.json")))
if os.path.exists(os.path.join(src, "hf.txt")):
    os.environ["HF_TOKEN"] = open(os.path.join(src, "hf.txt")).read().strip()
res = {"ok": False, "probe": bool(spec.get("probe")), "mode": "gguf", "steps": {}}
T0 = time.time()
def dump():
    res["total_s"] = round(time.time() - T0, 1)
    json.dump(res, open("/kaggle/working/result.json", "w"), default=str)
def step(name, fn):
    t = time.time()
    try:
        r = fn()
        res["steps"][name] = {"ok": True, "s": round(time.time() - t, 1), "info": r}
        dump()
        return r
    except Exception:
        res["steps"][name] = {"ok": False, "s": round(time.time() - t, 1), "err": traceback.format_exc()[-900:]}
        dump()
        return None
def sh(*cmd):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *cmd], check=False)
def env():
    import torch, psutil
    d = {}
    for p in ("/tmp", "/kaggle/working"):
        u = shutil.disk_usage(p)
        d["disk_free_gb" + p.replace("/", "_")] = round(u.free / 2**30, 1)
    return {"gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
            "vram_gb": [round(torch.cuda.get_device_properties(i).total_memory / 2**30, 1) for i in range(torch.cuda.device_count())],
            "ram_gb": round(psutil.virtual_memory().total / 2**30, 1), **d}
step("pip", lambda: sh("-U", "git+https://github.com/huggingface/diffusers", "transformers", "accelerate", "gguf",
                       "huggingface_hub", "bitsandbytes", "sentencepiece", "protobuf", "imageio", "imageio-ffmpeg", "psutil"))
step("env", env)
import torch
import diffusers
from huggingface_hub import HfApi, hf_hub_download
api = HfApi()
def survey():
    out = {"diffusers": diffusers.__version__,
           "classes": sorted(n for n in dir(diffusers) if any(k in n for k in ("LTX", "MiniMax", "H3")))[:30]}
    ms = []
    for q in ("MiniMax-H3", "minimax h3"):
        ms += [m.id for m in api.list_models(search=q, limit=15)]
    out["h3_repos"] = sorted(set(ms))[:25]
    return out
step("survey", survey)
LTX_REPO = spec.get("model", "Lightricks/LTX-2.5-Diffusers")
GGUF_REPO = spec.get("gguf_repo", "unsloth/LTX-2.5-GGUF")
GGUF_FILE = spec.get("gguf_file", "distilled/ltx-2.5-22b-distilled-UD-Q4_K_XL.gguf")
def sizes():
    tot = {}
    for e in api.list_repo_tree(LTX_REPO, recursive=True):
        sz = getattr(e, "size", None)
        if sz:
            top = e.path.split("/")[0]
            tot[top] = round(tot.get(top, 0) + sz / 2**30, 2)
    return tot
step("repo_sizes", sizes)
def h3_survey():
    out = {"h3_classes": sorted(n for n in dir(diffusers) if "H3" in n or "MiniMax" in n)}
    for repo in ("Abiray/MiniMax-H3-Pruned-GGUF", "Comfy-Org/MiniMax-H3", "MiniMaxAI/MiniMax-H3"):
        try:
            out[repo] = {e.path: round(getattr(e, "size", 0) / 2**30, 1) for e in api.list_repo_tree(repo, recursive=True)
                         if getattr(e, "size", 0) and getattr(e, "size", 0) > 2**27}
        except Exception as ex:
            out[repo] = "ERR " + str(ex)[-120:]
    return out
step("h3_survey", h3_survey)
gg = step("download_gguf", lambda: hf_hub_download(GGUF_REPO, GGUF_FILE))
dit = None
if gg:
    def _l():
        global dit
        import json as j
        cfg = j.load(open(hf_hub_download(LTX_REPO, "transformer/config.json")))
        from diffusers import GGUFQuantizationConfig
        cls = getattr(diffusers, cfg["_class_name"])
        qc = GGUFQuantizationConfig(compute_dtype=torch.bfloat16)
        try:
            dit = cls.from_single_file(gg, quantization_config=qc, config=LTX_REPO, subfolder="transformer",
                                       torch_dtype=torch.bfloat16)
            return {"class": cfg["_class_name"], "how": "default"}
        except Exception as e1:
            res["steps"]["load_dit_gguf_first_error"] = str(e1)[-200:]
            import gguf
            from accelerate import init_empty_weights
            names = {t.name for t in gguf.GGUFReader(gg).tensors}
            with init_empty_weights():
                m = cls.from_config(cls.load_config(LTX_REPO, subfolder="transformer"))
            keys = set(m.state_dict().keys())
            import re as _re
            pat = lambda xs: sorted({_re.sub(r"\\.\\d+\\.", ".N.", n) for n in xs})
            res["steps"]["key_diag"] = {"gguf_n": len(names), "model_n": len(keys),
                                        "gguf_only": pat(names - keys)[:40], "model_only": pat(keys - names)[:40]}
            try:
                import inspect
                import diffusers.loaders.single_file_utils as _u
                fns = [n for n in dir(_u) if "ltx" in n.lower()]
                res["steps"]["converter_fns"] = fns
                tf = [n for n in fns if "transformer" in n.lower()]
                if tf:
                    res["steps"]["converter_src"] = inspect.getsource(getattr(_u, tf[0]))[:2600]
            except Exception as _e:
                res["steps"]["converter_src"] = "ERR " + str(_e)[-100:]
            dump()
            raise RuntimeError("keys differ, see key_diag")
    step("load_dit_gguf", _l)
pipe = None
if dit is not None:
    def _p():
        global pipe
        import json as j
        from diffusers import DiffusionPipeline
        from diffusers.quantizers import PipelineQuantizationConfig
        q = PipelineQuantizationConfig(quant_backend="bitsandbytes_4bit",
                                       quant_kwargs={"load_in_4bit": True, "bnb_4bit_compute_dtype": torch.bfloat16, "bnb_4bit_quant_type": "nf4"},
                                       components_to_quantize=["text_encoder"])
        pipe = DiffusionPipeline.from_pretrained(LTX_REPO, transformer=dit, torch_dtype=torch.bfloat16, quantization_config=q)
        pipe.enable_model_cpu_offload()
        if hasattr(pipe, "enable_vae_tiling"):
            pipe.enable_vae_tiling()
        return {"pipeline": type(pipe).__name__}
    step("build_pipeline", _p)
if pipe is not None and not spec.get("probe"):
    def _g():
        import inspect
        from diffusers.utils import export_to_video
        params = list(inspect.signature(pipe.__call__).parameters)
        kw = {"prompt": spec["prompt"], "width": spec["width"], "height": spec["height"],
              "generator": torch.Generator("cpu").manual_seed(int(spec.get("seed", 1)))}
        if "num_frames" in params:
            kw["num_frames"] = int(spec["num_frames"])
        if "num_inference_steps" in params:
            kw["num_inference_steps"] = 8
        if "guidance_scale" in params:
            kw["guidance_scale"] = 1.0
        out = pipe(**kw)
        export_to_video(out.frames[0], "/kaggle/working/video.mp4", fps=int(spec.get("fps", 24)))
        return {"peak_vram_gb": [round(torch.cuda.max_memory_allocated(i) / 2**30, 1) for i in range(torch.cuda.device_count())]}
    step("generate", _g)
elif pipe is not None:
    def _m():
        return {"peak_vram_gb": [round(torch.cuda.max_memory_allocated(i) / 2**30, 1) for i in range(torch.cuda.device_count())]}
    step("mem_after_build", _m)
res["ok"] = all(s.get("ok") for s in res["steps"].values())
dump()
print("done", res["ok"])
'''
