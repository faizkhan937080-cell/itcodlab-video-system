"""Rule engine_fallback: when the main voice engine fails mid-run the next free engine speaks (no manual re-run)."""
import numpy as np
from scripts import voice_providers as vp


class Dead:
    name = "dead"

    def speak(self, *a):
        raise RuntimeError("HTTP 400 model deprecated")


class Ok:
    name = "ok"

    def speak(self, text, seg, script, vs):
        return np.zeros(100, dtype=np.float32), 24000


def test_chain_falls_back_and_records_who_spoke():
    c = vp.Chain([Dead(), Ok()], {})
    y, sr = c.speak("hi", {"voice": "x"}, {}, {"voice": "x"})
    assert sr == 24000 and c.used == ["ok"]


def test_chain_all_failed_is_one_clear_error():
    import pytest
    with pytest.raises(vp.VoiceUnavailable):
        vp.Chain([Dead(), Dead()], {}).speak("hi", {}, {}, {})
