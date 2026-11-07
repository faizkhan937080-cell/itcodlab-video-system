import numpy as np

from scripts import tts


class _Tok:
    def phonemize(self, text, lang):
        return text.strip().upper()


class _K:
    tokenizer = _Tok()


def test_trim_keeps_speech_and_cuts_silence():
    sr = 1000
    y = np.concatenate([np.zeros(500), np.ones(200) * 0.5, np.zeros(500)]).astype(np.float32)
    out = tts._trim(y, sr, keep_s=0.01)
    assert 200 <= len(out) <= 230


def test_lexicon_replaces_only_listed_words():
    ph = tts._with_lexicon(_K(), "Doctor Sodhi explains", "en-us", {"Sodhi": "sˈoʊdiː"})
    assert "sˈoʊdiː" in ph and "DOCTOR" in ph and "EXPLAINS" in ph


def test_lexicon_absent_returns_none():
    assert tts._with_lexicon(_K(), "plain text", "en-us", {"Sodhi": "x"}) is None
    assert tts._with_lexicon(_K(), "plain text", "en-us", {}) is None
