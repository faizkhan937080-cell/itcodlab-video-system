import base64
import io
import json

import numpy as np
import pytest
import soundfile as sf

from scripts import voice_providers as vp


@pytest.fixture
def reg(tmp_path, monkeypatch):
    monkeypatch.setattr(vp, "VOICES", tmp_path / "voices.json")
    monkeypatch.setattr(vp, "USAGE", tmp_path / "usage.json")
    return tmp_path


def test_clone_locked_until_verified(reg):
    vp.register("c1", "elevenlabs", "Dr X", kind="clone", voice_id_remote="abc", consent_doc="Drive/consent.pdf")
    with pytest.raises(vp.ConsentError):
        vp.resolve({"voice_id": "c1"})
    vp.verify("c1")
    prov, vs = vp.resolve({"voice_id": "c1"})
    assert prov == "elevenlabs" and vs["voice_id_remote"] == "abc"


def test_clone_without_consent_doc_refused(reg):
    with pytest.raises(vp.ConsentError):
        vp.register("c2", "chatterbox", "Y", kind="clone", ref_audio="a.wav")


def test_scope_and_expiry_enforced(reg):
    e = vp.register("c3", "elevenlabs", "Z", kind="clone", consent_doc="d", scope=("ai_synthesis",), voice_id_remote="v")
    vp.verify("c3")
    with pytest.raises(vp.ConsentError):   # no commercial scope
        vp.check_consent(vp.registry()["c3"])
    vp.register("c4", "elevenlabs", "Z", kind="clone", consent_doc="d", voice_id_remote="v", expires="2020-01-01")
    vp.verify("c4")
    with pytest.raises(vp.ConsentError):
        vp.check_consent(vp.registry()["c4"], today="2026-11-07")


def test_unknown_registry_id_and_stock_voice(reg):
    with pytest.raises(vp.ConsentError):
        vp.resolve({"voice_id": "nope"})
    assert vp.resolve({"provider": "google", "voice": "en-IN-Chirp3-HD-Aoede"})[0] == "google"


def test_google_decodes_wav(monkeypatch):
    buf = io.BytesIO()
    sf.write(buf, np.zeros(2400, dtype="float32") + 0.1, 24000, format="WAV", subtype="PCM_16")
    out = json.dumps({"audioContent": base64.b64encode(buf.getvalue()).decode()}).encode()
    monkeypatch.setenv("GOOGLE_TTS_KEY", "k")
    monkeypatch.setattr(vp, "_post", lambda *a, **k: out)
    y, sr = vp.Google({}).speak("hi", {}, {}, {})
    assert sr == 24000 and len(y) == 2400


def test_elevenlabs_pcm_and_missing_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(vp.VoiceUnavailable):
        vp.ElevenLabs({})
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    pcm = (np.ones(480, dtype="<i2") * 1000).tobytes()
    monkeypatch.setattr(vp, "_post", lambda *a, **k: pcm)
    y, sr = vp.ElevenLabs({}).speak("hi", {}, {}, {"voice_id_remote": "v"})
    assert sr == 24000 and len(y) == 480


def test_quota_counter(reg):
    assert vp.note_usage("elevenlabs", 4000) == 6000
    assert vp.note_usage("elevenlabs", 1000) == 5000
    assert vp.note_usage("kokoro", 10) is None


def test_default_is_free_engines_and_hindi_voice(reg):
    prov, vs = vp.resolve({"lang": "hi-IN", "gender": "female"})
    assert prov == "auto" and vs["voice"] == "hi-IN-Chirp3-HD-Aoede"
    assert vp.resolve({"lang": "en-us"})[1]["voice"] == "en-IN-Chirp3-HD-Charon"


def test_paid_engine_only_on_command(reg):
    with pytest.raises(vp.PaidOnCommand):
        vp.open_engine({"provider": "elevenlabs"})


def test_auto_falls_back_then_explains(reg, monkeypatch):
    class Boom:
        def __init__(self, s):
            raise vp.VoiceUnavailable("no key")
    monkeypatch.setitem(vp.ENGINES, "google", Boom)
    monkeypatch.setitem(vp.ENGINES, "chatterbox", Boom)
    with pytest.raises(vp.VoiceUnavailable) as e:
        vp.open_engine({})
    assert "google: no key" in str(e.value) and "chatterbox: no key" in str(e.value)

    class Ok:
        name = "chatterbox"
        def __init__(self, s):
            pass
    monkeypatch.setitem(vp.ENGINES, "chatterbox", Ok)
    assert vp.open_engine({})[0].name == "chatterbox"


def test_free_quota_blocks_unless_allowed(reg, monkeypatch):
    vp.note_usage("google", 999_990, caps={"google": 1_000_000})
    class Ok:
        name = "google"
        def __init__(self, s):
            pass
    monkeypatch.setitem(vp.ENGINES, "google", Ok)
    monkeypatch.setitem(vp.ENGINES, "chatterbox", lambda s: (_ for _ in ()).throw(vp.VoiceUnavailable("gpu")))
    with pytest.raises(vp.VoiceUnavailable) as e:
        vp.open_engine({}, chars=100)
    assert "quota" in str(e.value)
    assert vp.open_engine({"allow_paid": True}, chars=100)[0].name == "google"
