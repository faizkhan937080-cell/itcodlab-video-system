"""Optional: turn each collage into plain-text facts with a free Gemini API key, so Claude can 'read' the
frames as text (Drive images reach Claude as base64). Best effort: no key = skipped, job never fails."""
import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .common import limits, log, now_iso, tail

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
PROMPT = (
    "The image is a grid of video frames. Each tile has a label like 'c3 s5 00:04.2' "
    "(cluster, scene, time). For EVERY tile return a JSON list of objects with keys: "
    "tile (the label text), shot (close-up/medium/wide/screen-recording/graphic), subject, "
    "on_screen_text (exact words, or ''), graphics (captions style, shapes, stickers, lower thirds, "
    "icons, 3D or tilted elements), colors (3 hex-like names), layout (where text/subject sits), "
    "motion_hint (what looks animated or blurred). Facts only. No opinions. No extra text."
)


def get_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        from google.colab import userdata
        return userdata.get("GEMINI_API_KEY")
    except Exception:  # noqa: BLE001
        return None


def _post(model, key, body, timeout=180):
    req = urllib.request.Request(URL.format(model=model), data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    from .netguard import guard

    def go():
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    return guard().call("gemini", go)


def _ask(models, key, jpg_bytes, retries=2):
    body = {"contents": [{"parts": [{"text": PROMPT}, {"inline_data": {
        "mime_type": "image/jpeg", "data": base64.b64encode(jpg_bytes).decode()}}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
    last = ""
    for model in models:
        for attempt in range(retries + 1):
            try:
                res = _post(model, key, body)
                txt = res["candidates"][0]["content"]["parts"][0]["text"]
                return model, json.loads(txt)
            except urllib.error.HTTPError as e:
                last = f"{model} HTTP {e.code}"
                if e.code == 429:
                    time.sleep(20 * (attempt + 1))
                elif e.code in (400, 403, 404):
                    break  # wrong model or key: try next model
            except Exception as e:  # noqa: BLE001
                last = f"{model} {type(e).__name__}"
                time.sleep(3)
    raise RuntimeError(tail(last))


def describe_pack(pack_dir, idx):
    """Write pack/descriptions.json. Returns a small status dict. Never raises."""
    lim = limits().get("describe", {})
    key = get_key()
    if not lim.get("enabled", True) or not key:
        return {"status": "skipped", "reason": "no GEMINI_API_KEY" if not key else "disabled"}
    pack = Path(pack_dir)
    out, used, errors = [], None, []
    for c in idx["collages"][: lim.get("max_calls", 10)]:
        try:
            used, items = _ask(lim.get("models", ["gemini-flash-latest", "gemini-2.5-flash"]), key,
                               (pack / c["file"]).read_bytes())
            out.append({"collage": c["file"], "tiles": items})
        except Exception as e:  # noqa: BLE001
            errors.append(f"{c['file']}: {e}")
    if not out:
        return {"status": "failed", "errors": errors[-3:]}
    doc = {"note": "Written by a vision model from the collages. Facts only; may miss detail.",
           "model": used, "made": now_iso(), "collages": out, "errors": errors}
    (pack / "descriptions.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    log(f"descriptions.json: {len(out)} collage(s) described")
    return {"status": "ok", "collages": len(out), "errors": len(errors)}
