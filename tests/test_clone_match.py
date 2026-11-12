import json

import cv2
import numpy as np

from scripts import clone_match


def _plan(template="ext", component="caption-weight", caps=True, shots=None, ref="creators/x/style_record.json"):
    p = {"scenes": [{"id": "s1", "duration_s": 4, "template": "video", "props": {"src": "a.mp4"},
                     "underlays": [{"template": template, "start_s": 0, "end_s": 4, "props": {"component": component}}]}],
         "protocol": {"reference": ref, "clone": {"reel": "R1", "ref_video": "r.mp4",
                                                  "shots": shots if shots is not None else [{"out": [0, 4], "ref": [1, 5]}]}}}
    if caps:
        p["captions"] = [{"text": "a", "start_s": 0, "end_s": 1}]
        p["caption_style"] = {"look": "ext", "component": "caption-weight", "font": "Inter"}
    return p


def _reg(monkeypatch, extra=None):
    reg = {"caption-weight": {"source": "remocn"}, "rep": {"source": "clone:R1"}, "other": {"source": "clone:R2"}}
    reg.update(extra or {})
    monkeypatch.setattr(clone_match, "_registry", lambda: reg)
    monkeypatch.setattr(clone_match, "_google_fonts", lambda: {"Inter", "JetBrainsMono"})


def test_outside_components_pass(monkeypatch):
    _reg(monkeypatch)
    assert clone_match.check_plan(_plan(), 4.0) == []
    assert clone_match.check_plan(_plan("clone", "rep"), 4.0) == []


def test_in_house_templates_and_fonts_are_refused(monkeypatch):
    _reg(monkeypatch)
    errs = clone_match.check_plan(_plan("nt_card", None), 4.0)
    assert any("in-house template 'nt_card'" in e for e in errs)
    errs = clone_match.check_plan(_plan("clone", "other"), 4.0)
    assert any("belongs to clone:R2" in e for e in errs)
    p = _plan()
    p["caption_style"]["look"] = "nt"
    assert any("outside caption component" in e for e in clone_match.check_plan(p, 4.0))
    p = _plan()
    p["caption_style"]["font"] = "MyFont"
    assert any("not a Google font" in e for e in clone_match.check_plan(p, 4.0))


def test_shot_map_and_reference_are_required(monkeypatch):
    _reg(monkeypatch)
    assert any("has no reference shot" in e for e in clone_match.check_plan(_plan(shots=[{"out": [0, 2], "ref": [0, 2]}]), 4.0))
    assert any("never 'none'" in e for e in clone_match.check_plan(_plan(ref="none"), 4.0))


def _video(path, colour_fn, n=40):
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (108, 192))
    for i in range(n):
        f = np.zeros((192, 108, 3), np.uint8)
        colour_fn(f, i)
        w.write(f)
    w.release()


def test_score_same_high_different_low():
    a = np.zeros((192, 108, 3), np.uint8)
    a[:96] = (224, 232, 233)
    a[96:] = (30, 30, 30)
    b = np.zeros_like(a)
    b[:] = (200, 60, 20)
    assert clone_match.score(a, a)["total"] > 0.99
    assert clone_match.score(a, b)["total"] < 0.6


def test_match_writes_side_by_side_and_fails_low(tmp_path):
    def split(f, i):
        f[:96] = (224, 232, 233)
        f[96:] = (25, 25, 25)

    def blue(f, i):
        f[:] = (200, 60, 20)
    _video(tmp_path / "ref.mp4", split)
    _video(tmp_path / "good.mp4", split)
    _video(tmp_path / "bad.mp4", blue)
    clone = {"shots": [{"out": [0, 3.5], "ref": [0, 3.5], "what": "split"}]}
    ok = clone_match.match(tmp_path / "good.mp4", tmp_path / "ref.mp4", clone, tmp_path / "o1", {"clone": {"min_score": 0.85}})
    bad = clone_match.match(tmp_path / "bad.mp4", tmp_path / "ref.mp4", clone, tmp_path / "o2", {"clone": {"min_score": 0.85}})
    assert ok["pass"] and ok["min"] > 0.95 and (tmp_path / "o1" / "collage_match.jpg").exists()
    assert not bad["pass"] and bad["low"]
    json.dumps(ok)


def test_assets_job_keeps_only_commercial_licences(tmp_path, monkeypatch):
    from PIL import Image
    from scripts import assets_job, library

    class S:
        def __init__(self):
            self.files, self.idx = {}, []

        def put_file(self, src, rel):
            self.files[rel] = src

        def read_json(self, rel):
            return self.idx

        def put_json(self, rel, d, versioned=True):
            self.idx = d

        def put_text(self, rel, t, versioned=True):
            pass

    res = [{"url": "https://x/a.jpg", "license": "by-nc", "filetype": "jpg"},
           {"url": "https://x/b.jpg", "license": "cc0", "filetype": "jpg", "creator": "c", "title": "t"},
           {"url": "https://x/c.jpg", "license": "by", "filetype": "jpg"}]

    def dl(url, dest, kind):
        Image.new("RGB", (40, 60), (20, 20, 20)).save(dest)
    st = S()
    rep = assets_job.run(st, {"queries": [{"query": "dark room", "name": "dark-room", "count": 5}]}, tmp_path,
                         search_fn=lambda *a, **k: res, download_fn=dl)
    assert [k["licence"] for k in rep[0]["kept"]] == ["cc0", "by"]
    assert rep[0]["sheet"] and (tmp_path / rep[0]["sheet"]).exists()
    assert len(st.idx) == 2 and all(e["file"].startswith(library.BASE + "/image/dark-room/") for e in st.idx)
