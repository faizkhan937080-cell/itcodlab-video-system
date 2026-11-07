"""Free open Hindi TTS on a free Kaggle GPU: AI4Bharat Indic Parler-TTS (Apache-2.0, voice set by text description).
A/B only: `./run indic-tts-ab <script.json>` makes one wav per voice description and uploads them to Drive output/voice-ab/<name>/.
Same Kaggle plumbing as videogen.py (secrets KAGGLE_USERNAME, KAGGLE_KEY stay in env)."""
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from . import kaggle_gpu as kg
from .common import limits, log, tail

REPO = "ai4bharat/indic-parler-tts"
DATASET, KERNEL = "itcod-hindi-ab-in", "itcod-hindi-ab"
DESCRIPTIONS = {
    "male": "Rohit speaks in Hindi with a clear, natural, warm voice, at a moderate pace, with natural short pauses between sentences. Very high quality recording, no background noise.",
    "female": "Divya speaks in Hindi with a clear, natural, warm voice, at a moderate pace, with natural short pauses between sentences. Very high quality recording, no background noise.",
}

KERNEL_SRC = '''import glob, json, os, subprocess, sys, time, traceback
import numpy as np
src = os.path.dirname(glob.glob("/kaggle/input/**/script.json", recursive=True)[0])
script = json.load(open(os.path.join(src, "script.json")))
out = {"ok": False, "voices": {}}
t0 = time.time()
try:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "git+https://github.com/huggingface/parler-tts.git", "soundfile"], check=False)
    import torch, soundfile as sf
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = ParlerTTSForConditionalGeneration.from_pretrained("%REPO%").to(dev)
    tok = AutoTokenizer.from_pretrained("%REPO%")
    dtok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    sr = model.config.sampling_rate
    for voice, desc in script["descriptions"].items():
        parts = []
        ids = dtok(desc, return_tensors="pt").input_ids.to(dev)
        for seg in script["segments"]:
            pids = tok(seg["text"], return_tensors="pt").input_ids.to(dev)
            with torch.no_grad():
                a = model.generate(input_ids=ids, prompt_input_ids=pids).cpu().numpy().squeeze()
            parts.append(a)
            parts.append(np.zeros(int(sr * seg.get("pause_after_s", 0.3))))
        wav = np.concatenate(parts)
        sf.write("/kaggle/working/%s.wav" % voice, wav, sr)
        out["voices"][voice] = {"seconds": round(len(wav) / sr, 1), "sr": sr}
    out["ok"] = True
except Exception:
    out["error"] = traceback.format_exc()[-1500:]
out["total_s"] = round(time.time() - t0, 1)
json.dump(out, open("/kaggle/working/result.json", "w"))
print("done", out["ok"])
'''.replace("%REPO%", REPO)


def run(script, out_dir, poll_s=20, timeout_s=None):
    timeout_s = timeout_s or int(limits().get("videogen", {}).get("timeout_s", 2400))
    owner = os.environ.get("KAGGLE_USERNAME", "")
    if not owner or not os.environ.get("KAGGLE_KEY") or not shutil.which("kaggle"):
        return {"ok": False, "error_hint": "Kaggle credentials or CLI missing"}
    payload = dict(script, descriptions=DESCRIPTIONS)
    t0 = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="itcod-hindi-ab-") as work:
            ds, kn = Path(work) / "ds", Path(work) / "kn"
            ds.mkdir(), kn.mkdir()
            (ds / "script.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            (ds / "dataset-metadata.json").write_text(json.dumps(
                {"title": "itcod hindi ab input", "id": f"{owner}/{DATASET}", "licenses": [{"name": "CC0-1.0"}]}), encoding="utf-8")
            (kn / "hindi_kernel.py").write_text(KERNEL_SRC, encoding="utf-8")
            (kn / "kernel-metadata.json").write_text(json.dumps({
                "id": f"{owner}/{KERNEL}", "title": "itcod hindi ab", "code_file": "hindi_kernel.py", "language": "python",
                "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
                "dataset_sources": [f"{owner}/{DATASET}"], "competition_sources": [], "kernel_sources": []}), encoding="utf-8")
            rc, o, e = kg._cli(["datasets", "status", f"{owner}/{DATASET}"], 120)
            verb = ["datasets", "version", "-p", str(ds), "-m", "ab " + str(int(t0)), "-r", "skip"] \
                if rc == 0 and "ready" in (o + e).lower() else ["datasets", "create", "-p", str(ds), "-r", "skip"]
            rc, o, e = kg._cli(verb, 600)
            if rc != 0:
                return {"ok": False, "error_hint": "dataset upload failed: " + tail(e or o, 2)}
            for _ in range(40):
                rc, o, e = kg._cli(["datasets", "status", f"{owner}/{DATASET}"], 120)
                if rc == 0 and "ready" in (o + e).lower():
                    break
                time.sleep(5)
            rc, o, e = kg._cli(["kernels", "push", "-p", str(kn)], 300)
            if rc != 0:
                return {"ok": False, "error_hint": "kernel push failed: " + tail(e or o, 2)}
            while time.time() - t0 < timeout_s:
                time.sleep(poll_s)
                rc, o, e = kg._cli(["kernels", "status", f"{owner}/{KERNEL}"], 120)
                w = kg._status_word(o + e)
                if w == "COMPLETE":
                    break
                if w in ("ERROR", "CANCEL"):
                    log(f"hindi-ab: kernel {w.lower()}")
                    break
            else:
                return {"ok": False, "error_hint": "timeout"}
            outdir = Path(work) / "out"
            kg._cli(["kernels", "output", f"{owner}/{KERNEL}", "-p", str(outdir)], 900)
            rf = outdir / "result.json"
            if not rf.exists():
                return {"ok": False, "error_hint": "no result from kernel"}
            res = json.loads(rf.read_text(encoding="utf-8"))
            res["kaggle_wall_s"] = round(time.time() - t0)
            if res.get("ok"):
                Path(out_dir).mkdir(parents=True, exist_ok=True)
                for wv in outdir.glob("*.wav"):
                    shutil.copy(wv, Path(out_dir) / wv.name)
            return res
    except Exception as ex:  # noqa: BLE001
        return {"ok": False, "error_hint": type(ex).__name__}
