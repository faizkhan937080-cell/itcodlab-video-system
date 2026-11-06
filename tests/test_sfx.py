from scripts import sfx


def plan():
    return {"fps": 30, "scenes": [
        {"id": "a", "duration_s": 2, "template": "title"},
        {"id": "b", "duration_s": 3, "template": "checklist", "props": {"items": ["x", "y", "z"]}, "transition_in": {"type": "slide"}},
        {"id": "c", "duration_s": 2, "template": "counter", "transition_in": {"type": "cut"}},
    ]}


def test_cues_are_exact_and_sorted():
    cues = sfx.plan_cues(plan())
    kinds = [(round(c["t"], 2), c["kind"]) for c in cues]
    assert kinds[0] == (0.0, "hit")
    assert (1.88, "whoosh") in kinds                  # 2.0 s cut minus 0.12 s lead
    assert sum(1 for _, k in kinds if k == "tick") == 3
    assert (5.1, "pop") in kinds                      # scene c starts at 5.0 s, +3 frames
    assert [c["t"] for c in cues] == sorted(c["t"] for c in cues)


def test_pick_keeps_only_commercial_short_and_prefers_cc0():
    res = [{"license": "by-nc", "duration": 1000, "url": "u1"},
           {"license": "by", "duration": 900, "url": "u2", "title": "T", "creator": "C"},
           {"license": "cc0", "duration": 3000, "url": "u3"},
           {"license": "cc0", "duration": 9000, "url": "u4"},
           {"license": "by-sa", "duration": 500, "url": "u5"}]
    item, credit = sfx.pick(res)
    assert item["url"] == "u3" and credit is None
    item, credit = sfx.pick([res[1]])
    assert item["url"] == "u2" and "C" in credit       # CC BY keeps a credit line
    assert sfx.pick([res[0], res[4]]) == (None, None)


def test_audio_defs_skip_missing_kinds():
    cues = sfx.plan_cues(plan())
    out = sfx.audio_defs(cues, {"hit": "assets/sfx/hit.mp3"})
    assert len(out) == 1 and out[0]["at_s"] == 0.0 and out[0]["volume"] == sfx.SFX_VOLUME


def test_judge_uses_numbers():
    assert sfx.judge(1.0, -6.0) is None
    assert "clipped" in sfx.judge(1.0, -0.1)
    assert "quiet" in sfx.judge(1.0, -50)
    assert "duration" in sfx.judge(9.0, -6)
    assert "peak" in sfx.judge(1.0, None)


def test_fetch_all_takes_first_passing_candidate_and_never_fakes(tmp_path):
    cands = {"hit": [{"license": "cc0", "duration": 500, "url": "http://x/clip.mp3"},
                     {"license": "by", "duration": 800, "url": "http://x/b.mp3", "title": "T", "creator": "C"}]}
    peaks = iter([-0.1, -8.0])  # first candidate clipped, second ok

    def search_fn(kind, **kw):
        return cands.get(kind, [])

    def dl(url, dest):
        dest.write_bytes(b"x")

    out = sfx.fetch_all(plan(), tmp_path, search_fn=search_fn, download_fn=dl, measure_fn=lambda p: (0.8, next(peaks)))
    assert out["files"] == {"hit": "assets/sfx/hit.mp3"}
    assert len(out["credits"]) == 1                      # the CC BY one needs a credit
    assert set(out["skipped"]) == {"whoosh", "pop", "tick"}  # nothing found -> skipped, not invented
