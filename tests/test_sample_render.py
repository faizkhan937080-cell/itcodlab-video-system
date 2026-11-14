import json
from scripts.sample_render import trim_plan


def test_trim_cuts_scenes_captions_audio():
    plan = {"scenes": [{"id": "a", "duration_s": 6.46}, {"id": "b", "duration_s": 5.0}],
            "captions": [{"start_s": 0.2, "end_s": 6.1, "words": [{"text": "x", "start_s": 0.2}, {"text": "y", "start_s": 6.0}]},
                         {"start_s": 6.4, "end_s": 9, "words": [{"text": "z", "start_s": 6.4}]}],
            "audio": [{"src": "v", "at_s": 0, "role": "voice"}, {"src": "m", "at_s": 0, "duration_s": 48, "duck": [{"from_s": 1, "to_s": 2}, {"from_s": 7, "to_s": 8}]}]}
    p = trim_plan(plan, 6.5)
    assert [s["id"] for s in p["scenes"]] == ["a", "b"] and abs(sum(s["duration_s"] for s in p["scenes"]) - 6.5) < 1e-6
    assert len(p["captions"]) == 2 and p["captions"][1]["end_s"] == 6.5
    assert p["audio"][0]["duration_s"] == 6.5 and p["audio"][1]["duck"] == [{"from_s": 1, "to_s": 2}]


def test_missing_music_is_made_not_fatal(tmp_path):
    from scripts import sample_render as S
    put = []

    class St:
        def exists(self, rel): return False
        def put_file(self, f, rel, versioned=True): put.append((rel, __import__("os").path.getsize(f)))

    S.ensure_music({"audio": [{"role": "music", "src": "assets/library/music/x.mp3"}]}, St(), log=lambda m: None)
    assert put and put[0][0] == "assets/library/music/x.mp3" and put[0][1] > 10000
