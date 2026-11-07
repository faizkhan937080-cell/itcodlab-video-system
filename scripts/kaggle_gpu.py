"""Free Kaggle T4 for the ears (faster-whisper). Opt-in, never raises, None = caller uses the CPU path.

Identical on purpose: the kernel runs the SAME scripts/audio.py transcribe() (shipped as a copy) with the SAME settings.
Switch: env ITCOD_KAGGLE_GPU=1 and limits analysis.kaggle_gpu true. Proof of equality: `./run kaggle-compare <wav>`.
Secrets stay in env (KAGGLE_USERNAME, KAGGLE_KEY); nothing secret is logged or written to disk by this module.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .common import ROOT, limits, log, tail

DATASET = "itcod-ears-in"
KERNEL = "itcod-ears"
SHIP = ["scripts/__init__.py", "scripts/common.py", "scripts/audio.py", "scripts/script_metrics.py"]
SHIP_CFG = "config/limits.json"

KERNEL_SRC = '''import glob, hashlib, json, os, shutil, subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "faster-whisper"], check=False)
src = os.path.dirname(glob.glob("/kaggle/input/**/ears.wav", recursive=True)[0])
root = "/kaggle/working/root"
os.makedirs(root + "/scripts", exist_ok=True)
os.makedirs(root + "/config", exist_ok=True)
for f in os.listdir(src):
    if f.startswith("py__"):
        shutil.copy(os.path.join(src, f), os.path.join(root, "scripts", f[4:]))
shutil.copy(os.path.join(src, "limits.json"), os.path.join(root, "config", "limits.json"))
sys.path.insert(0, root)
from scripts import audio
wav = os.path.join(src, "ears.wav")
res = audio.transcribe(wav)
res_out = {"input_sha1": hashlib.sha1(open(wav, "rb").read()).hexdigest(), "transcript": res}
json.dump(res_out, open("/kaggle/working/transcript.json", "w"), ensure_ascii=False)
print("done", res.get("available"))
'''


def enabled():
    return os.environ.get("ITCOD_KAGGLE_GPU") == "1" and bool(limits()["analysis"].get("kaggle_gpu"))


def _env():
    """New API tokens (KGAT_...) go in KAGGLE_API_TOKEN; old keys stay KAGGLE_USERNAME + KAGGLE_KEY."""
    e = dict(os.environ)
    key = e.get("KAGGLE_KEY", "")
    if key.startswith("KGAT_"):
        e["KAGGLE_API_TOKEN"] = key
        e.pop("KAGGLE_KEY", None)
    return e


def _clean(text):
    """Never let a key reach a log line."""
    key = os.environ.get("KAGGLE_KEY", "")
    return text.replace(key, "***") if key else text


def _cli(args, timeout=300):
    try:
        p = subprocess.run(["kaggle", *args], capture_output=True, text=True, timeout=timeout, env=_env())
    except Exception as e:  # noqa: BLE001
        return 1, "", f"{type(e).__name__}"
    return p.returncode, _clean(p.stdout or ""), _clean(p.stderr or "")


def _sha1(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def prepare(wav, work, owner):
    """Write the dataset dir and the kernel dir. Returns (dataset_dir, kernel_dir)."""
    ds, kn = Path(work) / "ds", Path(work) / "kn"
    ds.mkdir(parents=True), kn.mkdir(parents=True)
    shutil.copy(wav, ds / "ears.wav")
    for rel in SHIP:
        shutil.copy(ROOT / rel, ds / ("py__" + Path(rel).name))
    shutil.copy(ROOT / SHIP_CFG, ds / "limits.json")
    (ds / "dataset-metadata.json").write_text(json.dumps(
        {"title": "itcod ears input", "id": f"{owner}/{DATASET}", "licenses": [{"name": "CC0-1.0"}]}), encoding="utf-8")
    (kn / "ears_kernel.py").write_text(KERNEL_SRC, encoding="utf-8")
    (kn / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{owner}/{KERNEL}", "title": "itcod ears", "code_file": "ears_kernel.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "dataset_sources": [f"{owner}/{DATASET}"], "competition_sources": [], "kernel_sources": []}), encoding="utf-8")
    return ds, kn


def _status_word(text):
    t = text.upper()
    for w in ("COMPLETE", "ERROR", "CANCEL", "RUNNING", "QUEUED"):
        if w in t:
            return w
    return "UNKNOWN"


def transcribe(wav, timeout_s=None, poll_s=15):
    """Run audio.transcribe on a Kaggle T4. Returns the result dict, or None (caller falls back to CPU)."""
    lim = limits()["analysis"]
    timeout_s = timeout_s or int(lim.get("kaggle_timeout_s", 900))
    owner = os.environ.get("KAGGLE_USERNAME", "")
    if not owner or not os.environ.get("KAGGLE_KEY") or not shutil.which("kaggle"):
        log("kaggle gpu skipped: credentials or kaggle CLI missing")
        return None
    t0 = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="itcod-kaggle-") as work:
            ds, kn = prepare(wav, work, owner)
            rc, out, err = _cli(["datasets", "status", f"{owner}/{DATASET}"], 120)
            verb = ["datasets", "version", "-p", str(ds), "-m", "ears " + _sha1(wav)[:10], "-r", "skip"] \
                if rc == 0 and "ready" in (out + err).lower() else ["datasets", "create", "-p", str(ds), "-r", "skip"]
            rc, out, err = _cli(verb, 600)
            if rc != 0:
                log("kaggle gpu: dataset upload failed: " + tail(err or out, 2))
                return None
            for _ in range(40):  # dataset must be 'ready' before a kernel can mount it
                rc, out, err = _cli(["datasets", "status", f"{owner}/{DATASET}"], 120)
                if rc == 0 and "ready" in (out + err).lower():
                    break
                time.sleep(5)
            else:
                log("kaggle gpu: dataset never became ready")
                return None
            rc, out, err = _cli(["kernels", "push", "-p", str(kn)], 300)
            if rc != 0:
                log("kaggle gpu: kernel push failed: " + tail(err or out, 2))
                return None
            while time.time() - t0 < timeout_s:
                time.sleep(poll_s)
                rc, out, err = _cli(["kernels", "status", f"{owner}/{KERNEL}"], 120)
                w = _status_word(out + err)
                if w == "COMPLETE":
                    break
                if w in ("ERROR", "CANCEL"):
                    log(f"kaggle gpu: kernel {w.lower()}")
                    return None
            else:
                log("kaggle gpu: timeout")
                return None
            outdir = Path(work) / "out"
            rc, out, err = _cli(["kernels", "output", f"{owner}/{KERNEL}", "-p", str(outdir)], 300)
            f = outdir / "transcript.json"
            if rc != 0 or not f.exists():
                log("kaggle gpu: no output: " + tail(err or out, 2))
                return None
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("input_sha1") != _sha1(wav):  # stale dataset version mounted: never trust it
                log("kaggle gpu: input hash mismatch, ignored")
                return None
            res = data.get("transcript") or {}
            if not res.get("available"):
                log("kaggle gpu: transcript not available on the GPU side: " + tail(str(res.get("error") or res)[:400], 2))
                return None
            log(f"kaggle gpu transcript ok in {round(time.time() - t0)} s")
            return res
    except Exception as e:  # noqa: BLE001
        log(f"kaggle gpu skipped: {type(e).__name__}")
        return None


def compare(a, b):
    """Equality report between the CPU result and the GPU result (segment text/times, words, language)."""
    def segs(r):
        return [(s["start"], s["end"], s["text"], [w["w"] for w in s.get("words", [])]) for s in r.get("segments", [])]
    same_text = (a.get("text") == b.get("text"))
    sa, sb = segs(a), segs(b)
    n = max(len(sa), len(sb)) or 1
    same_seg = sum(1 for x, y in zip(sa, sb) if x == y)
    return {"language_same": a.get("language") == b.get("language"), "text_identical": same_text,
            "segments_cpu": len(sa), "segments_gpu": len(sb), "segments_identical_share": round(same_seg / n, 3),
            "identical": same_text and sa == sb and a.get("alt_english") == b.get("alt_english")}
