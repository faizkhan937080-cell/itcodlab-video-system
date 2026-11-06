import json

import numpy as np
import soundfile as sf

from scripts import listen


def test_music_from_meta():
    assert listen.music_from_meta({"track": "Tum Hi Ho", "artists": ["Arijit Singh"]})["title"] == "Tum Hi Ho"
    assert listen.music_from_meta({"track": "Original audio"})["confidence"].startswith("original-audio")
    assert listen.music_from_meta({}) == {}


def test_fingerprint_lookup_picks_best_and_never_guesses():
    class R:
        stdout = json.dumps({"duration": 30, "fingerprint": "AQAA"})
    res = json.dumps({"results": [{"score": 0.4, "recordings": [{"title": "Weak", "artists": [{"name": "A"}]}]},
                                  {"score": 0.93, "recordings": [{"title": "Strong", "id": "m1", "artists": [{"name": "B"}]}]}]})
    got = listen.fingerprint_lookup("x.wav", "KEY", run=lambda *a, **k: R(), get=lambda q: res)
    assert got["title"] == "Strong" and got["artists"] == ["B"]
    assert listen.fingerprint_lookup("x.wav", None) == {}
    assert listen.fingerprint_lookup("x.wav", "KEY", run=lambda *a, **k: R(), get=lambda q: '{"results": []}') == {}


def test_sound_events_merge_neighbours(tmp_path):
    sr = 16000
    p = tmp_path / "a.wav"
    sf.write(str(p), np.zeros(sr * 4, dtype="float32"), sr)
    calls = []

    def score(w, s, labels):
        calls.append(1)
        i = len(calls) - 1  # windows at 0, .5, 1, 1.5, 2 ...: 1..3 are 'pop'
        return {"pop": 0.9 if 1 <= i <= 3 else 0.0, "whoosh": 0.1}
    ev = listen.sound_events(p, score)
    assert len(ev) == 1 and ev[0]["label"] == "pop" and ev[0]["t"] == 0.5 and ev[0]["end"] == 2.5


def test_resolve_names_by_name_alias_tag():
    items = [{"id": "sfx-w1", "type": "sfx", "name": "Whoosh 1", "tags": ["swish"], "aliases": ["Big Whoosh"]},
             {"id": "music-calm", "type": "music", "name": "Calm", "tags": [], "aliases": []}]
    found, missing = listen.resolve_names(items, [{"name": "big whoosh", "kind": "sfx"}, {"name": "swish", "kind": "sfx"},
                                                  {"name": "pop", "kind": "sfx"}, {"name": "calm", "kind": "sfx"}])
    assert found == {"big whoosh": "sfx-w1", "swish": "sfx-w1"} and missing == ["pop", "calm"]


def test_listen_degrades_without_model(tmp_path):
    out = listen.listen(tmp_path / "x.wav", {}, None, None)
    assert out["music"]["title"] is None and out["sound_events"] == []
