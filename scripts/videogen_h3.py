"""Kaggle kernel for MiniMax-H3 (full, unpruned, 33B DiT) on 2x T4. Spec mode "h3". Every step is timed + logged to result.json.
Route: diffusers ModularPipeline, text encoder (Qwen3-VL-32B) and transformer each loaded in 4-bit NF4 ONE AT A TIME so they fit
2x14.6 GB VRAM / 31 GB RAM. Probe (spec.probe=true) loads and reports memory only. spec.workflow: "fl2va" (default) or "ref2va"."""

KERNEL_SRC_H3 = '''import gc, glob, inspect, json, os, shutil, subprocess, sys, time, traceback
os.environ["HF_HOME"] = "/tmp/hf"   # /tmp has ~966 GB free (run 3 filled the 19 GB /kaggle/working and died: no space left)
os.environ["HF_HUB_DISABLE_SHARED_BLOBS"] = "1"
os.environ["HF_HUB_DISABLE_FILE_LOCKS"] = "1"   # run 2: lock files in /tmp/hf/.locks failed as read-only
src = os.path.dirname(glob.glob("/kaggle/input/**/spec.json", recursive=True)[0])
spec = json.load(open(os.path.join(src, "spec.json")))
if os.path.exists(os.path.join(src, "hf.txt")):
    os.environ["HF_TOKEN"] = open(os.path.join(src, "hf.txt")).read().strip()
REPO = spec.get("model", "MiniMaxAI/MiniMax-H3")
WF = spec.get("workflow", "fl2va")
res = {"ok": False, "probe": bool(spec.get("probe")), "mode": "h3", "workflow": WF, "steps": {}}
T0 = time.time()
def dump():
    res["total_s"] = round(time.time() - T0, 1)
    json.dump(res, open("/kaggle/working/result.json", "w"), default=str)
def _watchdog():   # a kernel killed by our timeout returns nothing: dump where every thread is, then end cleanly so the result comes back
    time.sleep(float(spec.get("watchdog_s", 3000)))
    st = {}
    for tid, fr in sys._current_frames().items():
        st[str(tid)] = "".join(traceback.format_stack(fr)[-7:])[-1400:]
    res["steps"]["watchdog_stack"] = st
    res["steps"]["watchdog_fired"] = {"ok": False, "s": round(time.time() - T0, 1), "err": "watchdog"}
    dump()
    os._exit(0)
import threading
threading.Thread(target=_watchdog, daemon=True).start()
def step(name, fn):
    t = time.time()
    try:
        r = fn()
        res["steps"][name] = {"ok": True, "s": round(time.time() - t, 1), "info": r}
    except Exception:
        res["steps"][name] = {"ok": False, "s": round(time.time() - t, 1), "err": traceback.format_exc()[-1100:]}
        r = None
    dump()
    return r
def pipi(*a):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *a], check=False)
def mem():
    import torch, psutil
    return {"vram_used_gb": [round(torch.cuda.memory_allocated(i) / 2**30, 1) for i in range(torch.cuda.device_count())],
            "ram_used_gb": round(psutil.virtual_memory().used / 2**30, 1),
            "disk_free_gb_tmp": round(shutil.disk_usage("/tmp").free / 2**30, 1)}
step("pip", lambda: pipi("-U", "git+https://github.com/huggingface/diffusers", "transformers", "accelerate", "bitsandbytes",
                         "huggingface_hub", "hf_transfer", "sentencepiece", "protobuf", "imageio", "imageio-ffmpeg", "psutil", "qwen-vl-utils"))
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"   # free speed-up: parallel chunk download
import filelock as _fl   # run 4: lock files still failed in diffusers/hub; Kaggle runs one job at a time, so no-op locks are safe
class _NoLock:
    def __init__(self, *a, **k): self.is_locked = False
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def acquire(self, *a, **k): return self
    def release(self, *a, **k): pass
_fl.FileLock = _NoLock; _fl.WeakFileLock = _NoLock
import torch
import diffusers, transformers
from huggingface_hub import HfApi
api = HfApi()
step("env", lambda: dict(mem(), gpus=[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
                         diffusers=diffusers.__version__, transformers=transformers.__version__))
def sizes():
    tot = {}
    for e in api.list_repo_tree(REPO, recursive=True):
        sz = getattr(e, "size", None)
        if sz:
            top = e.path.split("/")[0]
            tot[top] = round(tot.get(top, 0) + sz / 2**30, 1)
    return tot
step("h3_sizes_gb", sizes)
def dl(patterns):
    from huggingface_hub import snapshot_download
    return snapshot_download(REPO, allow_patterns=patterns)
MAXMEM = {0: "13GiB", 1: "13GiB", "cpu": "26GiB"}
pipe = None
def make_pipe():
    global pipe
    from diffusers import ModularPipeline
    pipe = ModularPipeline.from_pretrained(REPO, workflow=WF) if WF != "fl2va" else ModularPipeline.from_pretrained(REPO)
    return {"class": type(pipe).__name__, "components": sorted(getattr(pipe, "_component_specs", {}).keys())}
step("modular_pipeline", make_pipe)
def load_te():
    from transformers import BitsAndBytesConfig as BNB
    pipe.load_components(names="text_encoder", dtype=torch.bfloat16, device_map="auto", max_memory=MAXMEM,
                         quantization_config=BNB(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16))
    return dict(mem(), te=type(pipe.text_encoder).__name__)
if pipe is not None:
    step("load_text_encoder_nf4", load_te)
def load_small():
    names = [n for n in pipe._component_specs if n not in ("transformer", "transformer_ref", "text_encoder", "guider")
             and pipe._component_specs[n].default_creation_method == "from_pretrained"
             and pipe._component_specs[n].pretrained_model_name_or_path is not None]
    pipe.load_components(names=names, dtype=torch.bfloat16)
    return dict(mem(), loaded=names)
if pipe is not None:
    step("load_vae_scheduler_etc", load_small)
def sig():
    return {"call_params": list(inspect.signature(pipe.__call__).parameters)[:40]}
if pipe is not None:
    step("call_signature", sig)
if pipe is not None and getattr(pipe, "text_encoder", None) is not None and spec.get("probe"):
    def free_te():   # probe: show the text encoder can be dropped before the 33B DiT is loaded
        pipe.text_encoder = None
        gc.collect(); torch.cuda.empty_cache()
        return mem()
    step("free_text_encoder", free_te)
def load_dit():
    from diffusers import BitsAndBytesConfig as DBNB, MiniMaxH3Transformer3DModel
    q = DBNB(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
    sp = pipe._component_specs.get("transformer")
    info = {"spec": str(sp)[:400]}
    try:
        pipe.load_components(names="transformer", dtype=torch.bfloat16, device_map="auto", max_memory=MAXMEM, quantization_config=q)
    except Exception as e:
        info["load_components_error"] = str(e)[-300:]
    if getattr(pipe, "transformer", None) is None:   # run 35 probe: load_components returned in 0.3 s and left it None -> load directly, then plug in
        info["direct_load"] = True
        sub = "transformer_ref" if WF == "ref2va" else "transformer"
        dit = MiniMaxH3Transformer3DModel.from_pretrained(REPO, subfolder=sub, torch_dtype=torch.bfloat16, device_map="auto",
                                                          max_memory=MAXMEM, quantization_config=q)
        pipe.update_components(**{"transformer": dit})
    return dict(mem(), dit=type(pipe.transformer).__name__, info=info,
                params_b=round(sum(p.numel() for p in pipe.transformer.parameters()) / 1e9, 1))
if pipe is not None:
    step("load_transformer_nf4", load_dit)
res["ok"] = all(s.get("ok") for s in res["steps"].values() if isinstance(s, dict) and "ok" in s)
dump()
print("done", res["ok"])
'''
