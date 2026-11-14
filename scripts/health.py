"""Service health (Checker): which free routes are alive TODAY. Runs on the runner (open network). Cheap calls only.
A route not tested today is not trusted (rule check_service_alive_first). Output: one line per service + work/health.json."""
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path


def _call(url, headers=None, body=None, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "User-Agent": "itcodlab/1.0", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]
    except Exception as e:  # noqa: BLE001
        return 0, str(e).encode()[:120]


def checks(env=os.environ):
    out = []

    def add(name, ok, note):
        out.append({"service": name, "ok": bool(ok), "note": str(note)[:160]})
    k = env.get("SARVAM_API_KEY")
    if k:
        c, b = _call("https://api.sarvam.ai/text-to-speech", {"api-subscription-key": k},
                     {"text": "Hi", "target_language_code": "en-IN", "speaker": "shubh", "model": "bulbul:v3"})
        add("sarvam_tts", c == 200, f"HTTP {c} {'' if c == 200 else b.decode('utf-8', 'replace')}")
    else:
        add("sarvam_tts", False, "SARVAM_API_KEY not set")
    k = env.get("GOOGLE_TTS_KEY")
    if k:
        c, b = _call("https://texttospeech.googleapis.com/v1/text:synthesize", {"X-Goog-Api-Key": k},
                     {"input": {"text": "Hi"}, "voice": {"languageCode": "en-IN", "name": "en-IN-Chirp3-HD-Charon"},
                      "audioConfig": {"audioEncoding": "LINEAR16"}})
        add("google_tts", c == 200, f"HTTP {c}")
    else:
        add("google_tts", False, "GOOGLE_TTS_KEY not set")
    k = env.get("GEMINI_API_KEY")
    if k:
        c, b = _call("https://generativelanguage.googleapis.com/v1beta/models?pageSize=1", {"x-goog-api-key": k})
        add("gemini_key", c == 200, f"HTTP {c} (key valid; TTS free quota is separate)")
    else:
        add("gemini_key", False, "GEMINI_API_KEY not set")
    k = env.get("HF_TOKEN")
    if k:
        c, b = _call("https://huggingface.co/api/whoami-v2", {"Authorization": f"Bearer {k}"})
        add("huggingface_token", c == 200, f"HTTP {c}")
    else:
        add("huggingface_token", False, "HF_TOKEN not set")
    a, t = env.get("CF_ACCOUNT_ID"), env.get("CF_API_TOKEN")
    if a and t:
        c, b = _call(f"https://api.cloudflare.com/client/v4/accounts/{a}/ai/run/@cf/black-forest-labs/flux-1-schnell",
                     {"Authorization": f"Bearer {t}"}, {"prompt": "a red apple", "steps": 1})
        add("cloudflare_flux", c == 200, f"HTTP {c} (free: 10,000 neurons/day, square picture only)")
    else:
        add("cloudflare_flux", False, "CF_ACCOUNT_ID / CF_API_TOKEN not set (optional)")
    if shutil.which("kaggle") and env.get("KAGGLE_USERNAME") and env.get("KAGGLE_KEY"):
        p = subprocess.run(["kaggle", "kernels", "list", "--mine", "-p", "1"], capture_output=True, text=True, timeout=60)
        add("kaggle_api", p.returncode == 0, "api ok (GPU queue length is not visible: slow queue = timeout)" if p.returncode == 0 else (p.stderr or p.stdout)[-120:])
    else:
        add("kaggle_api", False, "kaggle cli or keys missing")
    add("modal", bool(env.get("MODAL_TOKEN_ID") and env.get("MODAL_TOKEN_SECRET")), "tokens present (not live-tested)")
    return out


def main():
    res = checks()
    for r in res:
        print(("OK   " if r["ok"] else "DOWN ") + r["service"] + " | " + r["note"])
    p = Path("work")
    p.mkdir(exist_ok=True)
    (p / "health.json").write_text(json.dumps(res, indent=1))
    return 0
