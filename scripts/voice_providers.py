"""Voice engines behind one switch: kokoro (free, CPU), google (Cloud TTS Chirp 3 HD), elevenlabs, chatterbox (open, MIT, clone).
Every engine returns (float32 mono samples, sample_rate). Keys come from the environment (GitHub secrets), never from files.
Cloned voices are consent-gated: config/voices.json entry with a verified consent record, else ConsentError (rulebook 20-voice.md)."""
import base64
import io
import json
import os
import urllib.request
from datetime import date

import numpy as np

from .common import ROOT, log

VOICES = ROOT / "config" / "voices.json"
USAGE = ROOT / "costs" / "local" / "voice_usage.json"   # monthly char counter (local, not committed)


class VoiceUnavailable(RuntimeError):
    """Engine cannot run here (missing key / package / GPU). Message says exactly what is missing."""


class ConsentError(RuntimeError):
    """A cloned voice was asked for without a verified, in-scope, unexpired consent record."""


# ------------------------------------------------------------------ registry + consent gate
def registry():
    try:
        return json.loads(VOICES.read_text(encoding="utf-8")).get("voices", {})
    except (OSError, ValueError):
        return {}


def check_consent(entry, today=None, need=("ai_synthesis", "commercial")):
    """Clone voices need: consent.verified (Faiz saw the signed release), scope covering every `need`, and not expired."""
    if entry.get("kind") != "clone":
        return True
    c = entry.get("consent") or {}
    if not c.get("verified"):
        raise ConsentError(f"voice '{entry.get('person', '?')}': no verified consent record (signed release, Drive path in consent.doc)")
    missing = [n for n in need if n not in (c.get("scope") or [])]
    if missing:
        raise ConsentError(f"voice '{entry.get('person', '?')}': consent scope lacks {', '.join(missing)}")
    exp = c.get("expires")
    if exp and str(exp) < (today or date.today().isoformat()):
        raise ConsentError(f"voice '{entry.get('person', '?')}': consent expired {exp}")
    return True


def resolve(script):
    """-> (provider, voice settings dict). `voice_id` in the script points at the registry; else provider/voice come from the script."""
    vid = script.get("voice_id")
    if vid:
        e = registry().get(vid)
        if not e:
            raise ConsentError(f"voice_id '{vid}' is not in config/voices.json")
        check_consent(e)
        return e["provider"], {**e, "voice": e.get("voice") or e.get("voice_id_remote")}
    return script.get("provider", "kokoro"), {"voice": script.get("voice"), "kind": "stock"}


def _save(reg):
    VOICES.write_text(json.dumps({"_note": "Voice registry. Clones need consent.verified=true (Faiz saw the signed release). No keys here.",
                                  "voices": reg}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def register(vid, provider, person, kind="stock", voice=None, voice_id_remote=None, ref_audio=None, consent_doc=None,
             scope=("ai_synthesis", "commercial"), expires=None):
    """Add a voice. A clone starts UNVERIFIED: it cannot be used until verify(vid) after Faiz confirms the signed release in chat."""
    reg = registry()
    e = {"provider": provider, "kind": kind, "person": person}
    for k, v in (("voice", voice), ("voice_id_remote", voice_id_remote), ("ref_audio", ref_audio)):
        if v:
            e[k] = v
    if kind == "clone":
        if not consent_doc:
            raise ConsentError("a clone needs --consent-doc (Drive path of the signed release)")
        e["consent"] = {"verified": False, "doc": consent_doc, "scope": list(scope), "expires": expires}
    reg[vid] = e
    _save(reg)
    return e


def verify(vid):
    reg = registry()
    if vid not in reg or reg[vid].get("kind") != "clone":
        raise ConsentError(f"'{vid}' is not a registered clone")
    reg[vid]["consent"]["verified"] = True
    reg[vid]["consent"]["verified_on"] = date.today().isoformat()
    _save(reg)
    return reg[vid]


# ------------------------------------------------------------------ free-quota counter
def note_usage(provider, chars, caps=None):
    """Adds to this month's counter; returns remaining free chars (None = no free cap known)."""
    caps = caps or {"google": 1_000_000, "elevenlabs": 10_000}
    month = date.today().strftime("%Y-%m")
    try:
        d = json.loads(USAGE.read_text())
    except (OSError, ValueError):
        d = {}
    d.setdefault(month, {})
    d[month][provider] = d[month].get(provider, 0) + int(chars)
    try:
        USAGE.parent.mkdir(parents=True, exist_ok=True)
        USAGE.write_text(json.dumps(d))
    except OSError:
        pass
    cap = caps.get(provider)
    return None if cap is None else cap - d[month][provider]


# ------------------------------------------------------------------ http helper (polite: netguard)
def _post(host_key, url, headers, body, timeout=120):
    from . import netguard
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})

    def go():
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    return netguard.guard().call(host_key, go)


def _key(name, why):
    v = os.environ.get(name, "").strip()
    if not v:
        raise VoiceUnavailable(f"secret {name} is not set ({why})")
    return v


# ------------------------------------------------------------------ engines
class Kokoro:
    name = "kokoro"

    def __init__(self, script):
        from kokoro_onnx import Kokoro as K
        from .tts import ensure_model
        m, v = ensure_model()
        self.k = K(str(m), str(v))
        self.lex = script.get("lexicon") or {}

    def speak(self, text, seg, script, vs):
        from .tts import _with_lexicon
        lang = script.get("lang", "en-us")
        ph = _with_lexicon(self.k, text, lang, self.lex)
        y, sr = self.k.create(ph or text, voice=seg.get("voice") or vs.get("voice") or "am_michael",
                              speed=float(seg.get("speed", script.get("speed", 1.0))), lang=lang, is_phonemes=bool(ph))
        return np.asarray(y, dtype=np.float32), sr


class Google:
    """Cloud Text-to-Speech. Voice e.g. 'en-IN-Chirp3-HD-Aoede'. Free 1M chars/month on Chirp 3 HD, then $30 per 1M."""
    name = "google"

    def __init__(self, script):
        self.key = _key("GOOGLE_TTS_KEY", "Google Cloud API key with Text-to-Speech enabled")

    def speak(self, text, seg, script, vs):
        import soundfile as sf
        voice = seg.get("voice") or vs.get("voice") or "en-IN-Chirp3-HD-Aoede"
        lang = "-".join(voice.split("-")[:2])
        audio = {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}
        rate = float(seg.get("speed", script.get("speed", 1.0)))
        if abs(rate - 1.0) > 1e-6:
            audio["speakingRate"] = rate
        out = _post("google_tts", "https://texttospeech.googleapis.com/v1/text:synthesize",
                    {"X-Goog-Api-Key": self.key}, {"input": {"text": text}, "voice": {"languageCode": lang, "name": voice}, "audioConfig": audio})
        y, sr = sf.read(io.BytesIO(base64.b64decode(json.loads(out)["audioContent"])), dtype="float32")
        return (y if y.ndim == 1 else y.mean(axis=1)), sr


class ElevenLabs:
    """Needs a paid plan for commercial use (free = non-commercial). Cloned voice ids come from the consent-gated registry."""
    name = "elevenlabs"

    def __init__(self, script):
        self.key = _key("ELEVENLABS_API_KEY", "ElevenLabs paid plan key")
        self.model = script.get("model_id", "eleven_multilingual_v2")

    def speak(self, text, seg, script, vs):
        vid = vs.get("voice_id_remote") or vs.get("voice")
        if not vid:
            raise VoiceUnavailable("elevenlabs needs a voice id (script 'voice' or registry 'voice_id_remote')")
        body = {"text": text, "model_id": self.model,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": float(seg.get("speed", script.get("speed", 1.0)))}}
        out = _post("elevenlabs", f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=pcm_24000",
                    {"xi-api-key": self.key}, body)
        return np.frombuffer(out, dtype="<i2").astype(np.float32) / 32768.0, 24000


class Chatterbox:
    """Open (MIT) zero-shot clone from a short reference clip. Needs the chatterbox-tts package; a GPU is strongly advised."""
    name = "chatterbox"

    def __init__(self, script):
        try:
            import torch
            from chatterbox.tts import ChatterboxTTS
        except Exception as e:  # noqa: BLE001
            raise VoiceUnavailable(f"chatterbox-tts not installed here ({type(e).__name__}); run it on the worker GPU")
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        log(f"voice: chatterbox on {dev}")
        self.m = ChatterboxTTS.from_pretrained(device=dev)

    def speak(self, text, seg, script, vs):
        ref = vs.get("ref_audio")
        if vs.get("kind") == "clone" and not (ref and os.path.exists(ref)):
            raise VoiceUnavailable("chatterbox clone needs ref_audio (clean 10-30 s clip of the consenting speaker)")
        wav = self.m.generate(text, audio_prompt_path=ref, exaggeration=float(vs.get("exaggeration", 0.5)), cfg_weight=float(vs.get("cfg_weight", 0.5)))
        return wav.squeeze().detach().cpu().numpy().astype(np.float32), int(self.m.sr)


ENGINES = {"kokoro": Kokoro, "google": Google, "elevenlabs": ElevenLabs, "chatterbox": Chatterbox}


def open_engine(script):
    """-> (engine, voice settings). Raises ConsentError / VoiceUnavailable with a plain reason."""
    prov, vs = resolve(script)
    if prov not in ENGINES:
        raise VoiceUnavailable(f"unknown voice provider '{prov}' (have: {', '.join(ENGINES)})")
    return ENGINES[prov](script), vs
