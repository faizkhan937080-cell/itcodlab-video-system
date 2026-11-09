"""Kaggle kernel for MiniMax-H3 (full, unpruned, 33B DiT) on 2x T4. Spec mode "h3". Every step is timed + logged to result.json.
Route: diffusers ModularPipeline, text encoder (Qwen3-VL-32B) and transformer each loaded in 4-bit NF4 ONE AT A TIME so they fit
2x14.6 GB VRAM / 31 GB RAM. Probe (spec.probe=true) loads and reports memory only. spec.workflow: "fl2va" (default) or "ref2va"."""

KERNEL_SRC_H3 = '''import gc, glob, inspect, json, os, shutil, subprocess, sys, time, traceback
def _pick_hf_home():   # run 5: /tmp/hf became read-only mid-download (Errno 30). Use the first dir that takes a write and has room for the 62 GB DiT.
    import shutil as _sh
    for d in ["/kaggle/temp", "/var/tmp", "/root", "/tmp", "/home/kaggle", "/dev/shm"]:
        try:
            os.makedirs(os.path.join(d, "hf"), exist_ok=True)
            tp = os.path.join(d, "hf", ".w")
            open(tp, "wb").write(b"x" * (1 << 20)); os.remove(tp)
            if _sh.disk_usage(d).free / 2**30 >= 80:
                return os.path.join(d, "hf"), d
        except Exception:
            continue
    return "/tmp/hf", "/tmp"
HF_DIR, HF_BASE = _pick_hf_home()
os.environ["HF_HOME"] = HF_DIR
os.environ["HF_HUB_DISABLE_SHARED_BLOBS"] = "1"
os.environ["HF_HUB_DISABLE_FILE_LOCKS"] = "1"   # run 2: lock files in /tmp/hf/.locks failed as read-only
src = os.path.dirname(glob.glob("/kaggle/input/**/spec.json", recursive=True)[0])
spec = json.load(open(os.path.join(src, "spec.json")))
if os.path.exists(os.path.join(src, "hf.txt")):
    os.environ["HF_TOKEN"] = open(os.path.join(src, "hf.txt")).read().strip()
REPO = spec.get("model", "MiniMaxAI/MiniMax-H3")
WF = spec.get("workflow", "fl2va")
res = {"ok": False, "probe": bool(spec.get("probe")), "mode": "h3", "workflow": WF, "steps": {"hf_home": HF_DIR}}
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
def free_cache():   # run 6: the writable disk is ~60-70 GB; the 62 GB text encoder is already in GPU/RAM, so its cached copy goes
    import shutil as _sh
    hub = os.path.join(HF_DIR, "hub")
    before = _sh.disk_usage(HF_BASE).free / 2**30
    _sh.rmtree(hub, ignore_errors=True)
    os.makedirs(hub, exist_ok=True)
    return {"free_gb_before": round(before, 1), "free_gb_after": round(_sh.disk_usage(HF_BASE).free / 2**30, 1)}
if pipe is not None and getattr(pipe, "text_encoder", None) is not None:
    step("free_hf_cache", free_cache)
def sig():
    return {"call_params": list(inspect.signature(pipe.__call__).parameters)[:40]}
if pipe is not None:
    step("call_signature", sig)
IMG = os.path.join(src, "in.png")
COND = {}
TE_BLOCK = None
def _tree(b, depth=0):
    out = {}
    for n, sb in (getattr(b, "sub_blocks", None) or {}).items():
        comps = [c.name for c in (getattr(sb, "expected_components", None) or [])]
        ins = [getattr(i, "name", str(i)) for i in (getattr(sb, "inputs", None) or [])][:25]
        outs = [getattr(o, "name", str(o)) for o in (getattr(sb, "intermediate_outputs", None) or [])][:25]
        out[n] = {"type": type(sb).__name__, "components": comps, "inputs": ins, "outputs": outs}
        if depth < 1 and getattr(sb, "sub_blocks", None):
            out[n]["sub"] = _tree(sb, depth + 1)
    return out
def _gen_kw():
    kw = {"prompt": spec["prompt"], "num_frames": int(spec.get("num_frames", 124)),
          "height": int(spec.get("height", 672)), "width": int(spec.get("width", 384)),
          "generator": torch.Generator().manual_seed(int(spec.get("seed", 42)))}
    if spec.get("steps"):
        kw["num_inference_steps"] = int(spec["steps"])
    if os.path.exists(IMG) and WF == "fl2va":
        from PIL import Image
        kw["image"] = Image.open(IMG).convert("RGB")
    return kw
def encode():   # text (+ first frame) conditioning with the text encoder alone on the GPUs; result kept on CPU
    global TE_BLOCK
    tree = _tree(pipe.blocks)
    info = {"blocks": tree}
    res["steps"]["block_tree"] = tree
    dump()
    name = next((n for n, b in pipe.blocks.sub_blocks.items()
                 if "text_encoder" in [c.name for c in (getattr(b, "expected_components", None) or [])]), None)
    if name is None:
        raise RuntimeError("no top-level block uses text_encoder: " + json.dumps(list(tree))[:300])
    TE_BLOCK = name
    blk = pipe.blocks.sub_blocks[name]
    tp = blk.init_pipeline()
    comps = {c.name: getattr(pipe, c.name) for c in blk.expected_components if getattr(pipe, c.name, None) is not None}
    tp.update_components(**comps)
    want = {getattr(i, "name", None) for i in (getattr(blk, "inputs", None) or [])}
    kw = {k: v for k, v in _gen_kw().items() if k in want}
    outs = [o.name for o in blk.intermediate_outputs]
    with torch.no_grad():
        st = tp(**kw, output=outs)
    if not isinstance(st, dict):
        st = {o: st.get(o) for o in outs}
    for k, v in st.items():
        COND[k] = v.detach().to("cpu") if torch.is_tensor(v) else v
    info.update(te_block=name, used_inputs=sorted(kw), outputs={k: (list(v.shape) if torch.is_tensor(v) else type(v).__name__) for k, v in COND.items()})
    return dict(mem(), **info)
if pipe is not None and getattr(pipe, "text_encoder", None) is not None and not spec.get("probe"):
    step("encode_prompt", encode)
if pipe is not None and getattr(pipe, "text_encoder", None) is not None:
    def free_te():   # drop the 4-bit text encoder for real (lesson LTX run 29/30: .to(cpu) keeps the 4-bit weights on GPU)
        old = pipe.text_encoder
        for m in old.modules():
            for k in list(m._parameters):
                m._parameters[k] = None
            for k in list(m._buffers):
                m._buffers[k] = None
        try:
            pipe.text_encoder = None
        except Exception:
            pass
        del old
        gc.collect(); torch.cuda.empty_cache()
        return mem()
    step("free_text_encoder", free_te)
MAXMEM = {0: str(spec.get("dit_gpu0_gib", 9)) + "GiB", 1: str(spec.get("dit_gpu1_gib", 12)) + "GiB", "cpu": "20GiB"}
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
def generate():
    from diffusers.utils.export_utils import encode_video
    if TE_BLOCK and TE_BLOCK in pipe.blocks.sub_blocks:
        pipe.blocks.sub_blocks.pop(TE_BLOCK)   # conditioning already made; the rest of the blocks get it as inputs
    for n in ("vae", "audio_vae"):
        c = getattr(pipe, n, None)
        if c is not None:
            c.to("cuda:0")
            for f in ("enable_tiling", "enable_slicing"):
                if hasattr(c, f):
                    try:
                        getattr(c, f)()
                    except Exception:
                        pass
    kw = _gen_kw()
    dev = torch.device("cuda:0")
    cond = {k: (v.to(dev) if torch.is_tensor(v) else v) for k, v in COND.items()}
    t = time.time()
    with torch.no_grad():
        r = pipe(**kw, **cond, output=["videos", "audio", "sampling_rate"])
    gen_s = round(time.time() - t, 1)
    encode_video(r["videos"][0], fps=24, output_path="/kaggle/working/video.mp4",
                 audio=r["audio"][0], audio_sample_rate=r["sampling_rate"])
    res["gen_s"] = gen_s
    return dict(mem(), gen_s=gen_s, frames=len(r["videos"][0]), size_mb=round(os.path.getsize("/kaggle/working/video.mp4") / 2**20, 2),
                peak_vram_gb=[round(torch.cuda.max_memory_allocated(i) / 2**30, 1) for i in range(torch.cuda.device_count())])
if pipe is not None and not spec.get("probe") and getattr(pipe, "transformer", None) is not None and COND:
    step("generate", generate)
res["ok"] = all(s.get("ok") for s in res["steps"].values() if isinstance(s, dict) and "ok" in s)
dump()
print("done", res["ok"])
'''
