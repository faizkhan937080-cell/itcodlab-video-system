"""Kaggle kernel for the FREE GGUF route (LTX-2.5 Q4 + MiniMax H3 survey) on 2x T4. Every step is timed and logged to result.json
so one run shows exactly where it breaks. mode "gguf" in the spec selects this kernel (videogen.prepare)."""

KERNEL_SRC_GGUF = '''import gc, glob, json, os, shutil, subprocess, sys, time, traceback
os.environ["HF_HOME"] = "/tmp/hf"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["HF_HUB_DISABLE_SHARED_BLOBS"] = "1"   # shared blob store hits a read-only path on Kaggle
src = os.path.dirname(glob.glob("/kaggle/input/**/spec.json", recursive=True)[0])
spec = json.load(open(os.path.join(src, "spec.json")))
if os.path.exists(os.path.join(src, "hf.txt")):
    os.environ["HF_TOKEN"] = open(os.path.join(src, "hf.txt")).read().strip()
res = {"ok": False, "probe": bool(spec.get("probe")), "mode": "gguf", "steps": {}}
T0 = time.time()
def dump():
    res["total_s"] = round(time.time() - T0, 1)
    json.dump(res, open("/kaggle/working/result.json", "w"), default=str)
def _watchdog():   # a kernel killed by our timeout returns nothing: dump where every thread is, then end cleanly so the result comes back
    time.sleep(float(spec.get("watchdog_s", 1800)))
    import threading as _t
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
                       "huggingface_hub", "hf_transfer", "bitsandbytes", "sentencepiece", "protobuf", "imageio", "imageio-ffmpeg", "psutil", "av"))
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"   # free speed-up: parallel chunk download of the big model files
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
        import diffusers.loaders.single_file_utils as _u
        _orig = _u.convert_ltx2_transformer_to_diffusers
        def _patched(checkpoint, **kw):   # LTX-2.5 keys the 2.0 converter does not know
            for k in list(checkpoint.keys()):
                for a, b in (("audio_prompt_adaln_single.", "audio_prompt_adaln."), ("prompt_adaln_single.", "prompt_adaln.")):
                    if k.startswith(a):
                        checkpoint[b + k[len(a):]] = checkpoint.pop(k)
                        break
            return _orig(checkpoint, **kw)
        _u.convert_ltx2_transformer_to_diffusers = _patched
        import diffusers.loaders.single_file_model as _sm
        for _mod in (_u, _sm):
            for _v in getattr(_mod, "SINGLE_FILE_LOADABLE_CLASSES", {}).values():
                if _v.get("checkpoint_mapping_fn") is _orig:
                    _v["checkpoint_mapping_fn"] = _patched
        try:
            dit = cls.from_single_file(gg, quantization_config=qc, config=LTX_REPO, subfolder="transformer",
                                       torch_dtype=torch.bfloat16)
            meta = [n for n, q in dit.named_parameters() if q.device.type == "meta"][:8]
            return {"class": cfg["_class_name"], "how": "patched", "meta_params": meta}
        except Exception as e1:
            res["steps"]["load_dit_gguf_first_error"] = str(e1)[-200:]
            import gguf
            from accelerate import init_empty_weights
            names = {t.name for t in gguf.GGUFReader(gg).tensors}
            with init_empty_weights():
                m = cls.from_config(cls.load_config(LTX_REPO, subfolder="transformer"))
            keys = set(m.state_dict().keys())
            try:
                names = set(_patched({n: 0 for n in names}).keys())
            except Exception as _e:
                res["steps"]["conv_sim_err"] = str(_e)[-150:]
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
def h3_try():
    out = {}
    for sub in ("FL2VA", "FL2VA/transformer", "FL2VA/vae"):
        try:
            out[sub] = {e.path.split("/")[-1]: round(getattr(e, "size", 0) / 2**30, 1) for e in api.list_repo_tree("MiniMaxAI/MiniMax-H3", path_in_repo=sub)}
        except Exception as ex:
            out[sub] = "ERR " + str(ex)[-100:]
    out["root"] = [e.path for e in api.list_repo_tree("MiniMaxAI/MiniMax-H3")][:30]
    return out
step("h3_listing", h3_try)
pipe = None
if dit is not None:
    def _p():
        global pipe
        import json as j
        from diffusers import DiffusionPipeline
        from diffusers.quantizers import PipelineQuantizationConfig
        from huggingface_hub import snapshot_download
        du = lambda: round(shutil.disk_usage("/tmp").used / 2**30, 1)
        info = {"disk_used_gb_start": du()}
        try:   # the quantised DiT now lives in RAM: free its 13 GB file, Kaggle scratch disk is ~57 GB
            os.remove(os.path.realpath(gg)); os.remove(gg)
        except OSError:
            pass
        local = snapshot_download(LTX_REPO, local_dir="/tmp/ltx_local", ignore_patterns=[
            "transformer/*", "transformer_full/*", "prompt_enhancer/*", "temporal_latent_upsampler/*", "*lora*", ".cache/*"])
        info["disk_used_gb_after_dl"] = du()
        idx = j.load(open(os.path.join(local, "model_index.json")))
        missing = {k: None for k, v in idx.items() if isinstance(v, list) and k != "transformer"
                   and not os.path.isdir(os.path.join(local, k))}
        info["skipped"] = sorted(missing)
        # diffusers loads every model_index entry that has no folder from the ROOT (-> "no model.safetensors in /tmp/ltx_local").
        # prompt_enhancer=None as kwarg does NOT stop it (optional init args are not in passed_class_obj). Null it in the index.
        for k in missing:
            idx[k] = [None, None]
        j.dump(idx, open(os.path.join(local, "model_index.json"), "w"))
        q = PipelineQuantizationConfig(quant_backend="bitsandbytes_4bit",
                                       quant_kwargs={"load_in_4bit": True, "bnb_4bit_compute_dtype": torch.bfloat16, "bnb_4bit_quant_type": "nf4"},
                                       components_to_quantize=["text_encoder"])
        res["steps"]["pipe_diag"] = {
            "model_index": {k: v for k, v in idx.items() if isinstance(v, list)},
            "tree": sorted(x for x in (os.path.relpath(os.path.join(r, f), local) for r, _, fs in os.walk(local) for f in fs)
                           if not x.startswith(".cache"))[:120],
            "skipped": sorted(missing)}
        dump()
        import transformers
        from transformers import AutoModel, BitsAndBytesConfig as BNB
        bnb = BNB(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
        te_cls = getattr(transformers, idx["text_encoder"][1], None) or AutoModel   # class the pipeline expects (hidden_states)
        try:
            te = te_cls.from_pretrained(os.path.join(local, "text_encoder"), torch_dtype=torch.bfloat16, quantization_config=bnb)
        except Exception as e_te:
            res["steps"]["text_encoder_first_error"] = str(e_te)[-200:]
            te = AutoModel.from_pretrained(os.path.join(local, "text_encoder"), torch_dtype=torch.bfloat16, quantization_config=bnb)
        res["steps"]["text_encoder_loaded"] = type(te).__name__
        dump()
        pipe = DiffusionPipeline.from_pretrained(local, transformer=dit, text_encoder=te, torch_dtype=torch.bfloat16)
        # The 13 GB GGUF DiT cannot sit on one 14.5 GB T4 (run 24: CUDA OOM in model_cpu_offload). Keep everything else on cuda:0
        # and stream the DiT block by block (group offload); fall back to sequential offload if that fails.
        dev = torch.device("cuda:0")
        strat = spec.get("offload", "split")   # split = DiT halves on cuda:0/cuda:1 (see _g); group + sequential failed on GGUF (run 26)
        info["offload"] = strat
        if strat == "group":
            try:
                for _n, _c in pipe.components.items():
                    if isinstance(_c, torch.nn.Module) and _c is not pipe.transformer and next(_c.parameters(), None) is not None \
                            and next(_c.parameters()).device.type != "cuda":
                        _c.to(dev)
                pipe.transformer.enable_group_offload(onload_device=dev, offload_device=torch.device("cpu"),
                                                      offload_type="block_level", num_blocks_per_group=1)
            except Exception as _eg:
                info["group_offload_error"] = str(_eg)[-300:]
                strat = "sequential"
        if strat == "split":
            pass   # no offload hooks: _g encodes the prompt, frees the text encoder, then spreads the DiT over both GPUs
        elif strat == "sequential":
            pipe.enable_sequential_cpu_offload()
        elif strat == "model":
            pipe.enable_model_cpu_offload()
        if hasattr(pipe, "enable_vae_tiling"):
            pipe.enable_vae_tiling()
        info["pipeline"] = type(pipe).__name__
        return info
    step("build_pipeline", _p)
if pipe is not None and not spec.get("probe"):
    def _g():
        global pipe
        import inspect
        from diffusers.utils import export_to_video
        _img_path = os.path.join(src, "in.png")
        _img = None
        if spec.get("has_image") and os.path.exists(_img_path):   # image-to-video: same components, start frame = our picture (a face we own)
            from diffusers import LTX2ImageToVideoPipeline
            from PIL import Image
            pipe = LTX2ImageToVideoPipeline(**pipe.components)
            _img = Image.open(_img_path).convert("RGB").resize((int(spec["width"]), int(spec["height"])))
        params = list(inspect.signature(pipe.__call__).parameters)
        for _fn in ("enable_tiling", "enable_slicing"):   # run 2026-11-10: 288x512x97 OOM in VAE decode (5.8 GB conv3d); tiles fix it
            if hasattr(pipe.vae, _fn):
                getattr(pipe.vae, _fn)()
        if spec.get("offload", "split") == "split":
            d0, d1 = torch.device("cuda:0"), torch.device("cuda:1")
            def _devs():
                out = {}
                for _n, _c in pipe.components.items():
                    if isinstance(_c, torch.nn.Module):
                        _p = next(_c.parameters(), None)
                        out[_n] = str(_p.device) if _p is not None else "none"
                return out
            res["steps"]["split_phase"] = {"before_encode_vram_gb": [round(torch.cuda.memory_allocated(i) / 2**30, 1) for i in range(2)],
                                          "devices": _devs()}
            dump()
            with torch.no_grad():   # run 31: without this the result keeps the whole graph (all 4-bit weights + activations) on cuda:0
                pe, pm, _n1, _n2 = pipe.encode_prompt(prompt=spec["prompt"], do_classifier_free_guidance=False, device=d0,
                                                      max_sequence_length=int(spec.get("max_seq", 256)))
            pe, pm = pe.detach().to("cpu"), pm.detach().to("cpu")
            del _n1, _n2
            _old = pipe.text_encoder
            pipe.text_encoder = None   # frees the 7.7 GB of the text encoder before the DiT arrives
            # run 29: .to("cpu") did nothing on the 4-bit weights (9.1 GB stayed). Empty the module itself, whoever else holds it.
            for _m in _old.modules():
                for _k in list(_m._parameters):
                    _m._parameters[_k] = None
                for _k in list(_m._buffers):
                    _m._buffers[_k] = None
            del _old
            gc.collect(); torch.cuda.empty_cache()
            res["steps"]["after_free_vram_gb"] = [round(torch.cuda.memory_allocated(i) / 2**30, 1) for i in range(2)]
            try:   # who still holds GPU memory? (grouped by shape/dtype, biggest first)
                _g_ = {}
                for _o in gc.get_objects():
                    try:
                        if torch.is_tensor(_o) and _o.is_cuda:
                            _key = (tuple(_o.shape), str(_o.dtype), str(_o.device))
                            _a = _g_.setdefault(_key, [0, 0])
                            _a[0] += 1
                            _a[1] += _o.element_size() * _o.nelement()
                    except Exception:
                        pass
                res["steps"]["gpu_holders"] = [[str(k), v[0], round(v[1] / 2**30, 2)] for k, v in sorted(_g_.items(), key=lambda kv: -kv[1][1])[:8]]
            except Exception as _e:
                res["steps"]["gpu_holders"] = "ERR " + str(_e)[-120:]
            dump()
            def _mv(x, d):
                if torch.is_tensor(x):
                    return x.to(d)
                if isinstance(x, (list, tuple)):
                    return type(x)(_mv(i, d) for i in x)
                if isinstance(x, dict):
                    return {k: _mv(v, d) for k, v in x.items()}
                return x
            dit_m = pipe.transformer
            blocks = dit_m.transformer_blocks
            def _bytes(m):
                return sum(q.nelement() * q.element_size() for q in list(m.parameters()) + list(m.buffers()))
            others = {n: _bytes(c) for n, c in pipe.components.items() if isinstance(c, torch.nn.Module) and c is not dit_m}
            nonblock = {n: _bytes(c) for n, c in dit_m.named_children() if n != "transformer_blocks"}
            bb = [_bytes(x) for x in blocks]
            fixed = sum(others.values()) + sum(nonblock.values())
            target = (fixed + sum(bb)) / 2   # run 32: cuda:0 held 14.2 GB, cuda:1 5.4 GB; balance by real bytes instead of block count
            acc, half = fixed, 0
            while half < len(blocks) and acc + bb[half] <= target:
                acc += bb[half]
                half += 1
            res["steps"]["split_sizes_gb"] = {"others": {k: round(v / 2**30, 2) for k, v in others.items()},
                                              "nonblock": {k: round(v / 2**30, 2) for k, v in nonblock.items()},
                                              "blocks_total": round(sum(bb) / 2**30, 2), "blocks_on_d0": half}
            dump()
            for n, c in dit_m.named_children():
                if n != "transformer_blocks":
                    c.to(d0)
            for _k, _pp in list(dit_m._parameters.items()):   # run 33: the DiT's own tables (scale_shift_table...) were left on the CPU
                if _pp is not None:
                    _pp.data = _pp.data.to(d0)
            for _k, _bf in list(dit_m._buffers.items()):
                if _bf is not None:
                    dit_m._buffers[_k] = _bf.to(d0)
            for i, bl in enumerate(blocks):
                dv = d0 if i < half else d1
                bl.to(dv)
                bl.register_forward_pre_hook(lambda m, a, k, dv=dv: (_mv(a, dv), _mv(k, dv)), with_kwargs=True)
            blocks[-1].register_forward_hook(lambda m, a, o: _mv(o, d0))
            for n, c in pipe.components.items():
                if isinstance(c, torch.nn.Module) and c is not dit_m:
                    c.to(d0)
            res["steps"]["split_done"] = {"blocks": len(blocks), "half": half,
                                          "vram_gb": [round(torch.cuda.memory_allocated(i) / 2**30, 1) for i in range(2)]}
            dump()
            kw0 = {"prompt_embeds": pe.to(d0), "prompt_attention_mask": pm.to(d0)}
        else:
            kw0 = {"prompt": spec["prompt"]}
        kw = {**kw0, "width": spec["width"], "height": spec["height"],
              "generator": torch.Generator("cpu").manual_seed(int(spec.get("seed", 1)))}
        if "num_frames" in params:
            kw["num_frames"] = int(spec["num_frames"])
        if _img is not None and "image" in params:
            kw["image"] = _img
        if "num_inference_steps" in params:
            kw["num_inference_steps"] = 8
        if "guidance_scale" in params:
            kw["guidance_scale"] = 1.0
        for _k, _v in (("audio_guidance_scale", 1.0), ("stg_scale", 0.0), ("audio_stg_scale", 0.0)):   # distilled model: one pass per step
            if _k in params:
                kw[_k] = _v
        tg = time.time()
        tm = res["steps"].setdefault("gen_timing", {"first_step_after_s": None, "step_s": []})
        budget = float(spec.get("gen_budget_s", 1500))
        def _cb(p, i, t, ck):   # per-step timing + hard time budget so a slow run still reports where the time went
            now = round(time.time() - tg, 1)
            if tm["first_step_after_s"] is None:
                tm["first_step_after_s"] = now
            tm["step_s"].append(now)
            dump()
            if now > budget:
                raise TimeoutError("gen budget %ss used, stopped at step %s" % (budget, i))
            return ck
        if "callback_on_step_end" in params:
            kw["callback_on_step_end"] = _cb
        out = pipe(**kw)
        export_to_video(out.frames[0], "/kaggle/working/video.mp4", fps=int(spec.get("fps", 24)))
        return {"peak_vram_gb": [round(torch.cuda.max_memory_allocated(i) / 2**30, 1) for i in range(torch.cuda.device_count())]}
    step("generate", _g)
elif pipe is not None:
    def _m():
        return {"peak_vram_gb": [round(torch.cuda.max_memory_allocated(i) / 2**30, 1) for i in range(torch.cuda.device_count())]}
    step("mem_after_build", _m)
if spec.get("upscale") and os.path.exists("/kaggle/working/video.mp4"):   # Real-ESRGAN x4 on the same GPU, frame by frame
    def _u():
        global pipe
        import gc, urllib.request
        pipe = None
        gc.collect(); torch.cuda.empty_cache()
        sh("spandrel")
        import imageio.v3 as iio, numpy as np
        from spandrel import ModelLoader
        w = "/kaggle/working/RealESRGAN_x4plus.pth"
        urllib.request.urlretrieve("https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth", w)
        m = ModelLoader().load_from_file(w).model.eval().half().to("cuda:0")
        frames = iio.imread("/kaggle/working/video.mp4", plugin="pyav")
        outs = []
        with torch.no_grad():
            for f in frames:
                x = torch.from_numpy(f).permute(2, 0, 1)[None].half().div(255).to("cuda:0")
                y = m(x).clamp(0, 1)[0].permute(1, 2, 0).float().cpu().numpy()
                outs.append((y * 255).round().astype(np.uint8))
        os.rename("/kaggle/working/video.mp4", "/kaggle/working/video_small.mp4")
        tw, th = int(spec.get("out_width", 1080)), int(spec.get("out_height", 1920))
        tmp = "/kaggle/working/up_raw.mp4"
        iio.imwrite(tmp, np.stack(outs), plugin="pyav", fps=int(spec.get("fps", 24)), codec="libx264")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-vf", f"scale={tw}:{th}:flags=lanczos", "-c:v", "libx264",
                        "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "/kaggle/working/video.mp4"], check=True)
        return {"frames": len(outs), "out": [tw, th]}
    step("upscale", _u)
res["ok"] = all(s.get("ok") for s in res["steps"].values() if isinstance(s, dict) and "ok" in s)
dump()
print("done", res["ok"])
'''
