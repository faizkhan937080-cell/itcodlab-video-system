import cv2
import numpy as np
import pytest

from scripts import cover, fx, plan_edit, qa
from scripts.analyze import probe


def plan_of(*durs, **kw):
    p = {"title": "t", "fps": 30, "orientation": "portrait",
         "scenes": [{"id": f"s{i}", "duration_s": d, "template": "title", "props": {"text": "x"}} for i, d in enumerate(durs)]}
    p.update(kw)
    return p


# ------------------------------------------------------------------ QA, plan side
def test_cadence_flags_a_long_still_stretch_and_zoom_keys_fix_it():
    f, st = qa.cadence(plan_of(2, 9, 2))
    assert f and f[0]["code"] == "cadence" and st["longest_still_s"] == 9.0 and st["starts_at_s"] == 2.0
    p = plan_of(2, 9, 2)
    p["scenes"][1]["zoom"] = fx.punch_keys([2.0, 5.0])
    assert qa.cadence(p)[0] == []
    assert qa.cadence(plan_of(3, 3, 3))[0] == []


def test_hook_checks():
    assert any(x["code"] == "hook" and x["level"] == "warn" for x in qa.hook(plan_of(6, 2)))
    assert qa.hook(plan_of(2, 2)) == []
    vid = plan_of(2)
    vid["scenes"][0]["template"] = "video"
    assert [x["level"] for x in qa.hook(vid)] == ["info"]
    vid["captions"] = [{"text": "hi", "start_s": 0.4, "end_s": 1.0}]
    assert qa.hook(vid) == []


# ------------------------------------------------------------------ QA, file side
def test_detect_logs_are_parsed():
    log = "[blackdetect @ 0x1] black_start:0 black_end:0.5 black_duration:0.5\n[blackdetect] black_start:4.0 black_end:4.5\n" \
          "[silencedetect @ 0x2] silence_start: 2.5\n[silencedetect @ 0x2] silence_end: 3.9 | silence_duration: 1.4"
    assert qa.parse_intervals(log, "black") == [(0.0, 0.5), (4.0, 4.5)]
    assert qa.parse_intervals(log, "silence") == [(2.5, 3.9)]
    assert qa.complement([(2.5, 3.9)], 10) == [(0.0, 2.5), (3.9, 10)]


def test_file_checks_find_black_dead_air_loudness_and_missing_captions():
    probe_ = {"duration_s": 10.0, "has_audio": True}
    plan = plan_of(5, 5, audio=[{"src": "a.wav", "role": "voice"}])
    det = {"black": [(0.0, 0.6), (4.0, 4.6)], "silence": [(2.0, 3.2)]}
    codes = {x["code"] for x in qa.file_checks("v", plan, probe_, {"integrated_lufs": -20.0, "true_peak_dbtp": -0.1}, det, None)}
    assert {"black_start", "black", "dead_air", "loudness", "true_peak", "captions"} <= codes
    good = qa.file_checks("v", plan_of(5, 5), {"duration_s": 10.0, "has_audio": True}, {"integrated_lufs": -14.2, "true_peak_dbtp": -1.5},
                          {"black": [], "silence": []}, None)
    assert good == []


def test_caption_coverage():
    plan = {"captions": [{"text": "a", "start_s": 0, "end_s": 4}]}
    assert qa.caption_coverage(plan, [(0.0, 4.0)]) == 1.0
    assert qa.caption_coverage(plan, [(0.0, 8.0)]) == 0.5
    assert qa.caption_coverage(plan, []) is None


def test_qa_runs_on_a_real_video(test_video, tmp_path):
    r = qa.run(test_video, plan_of(8, 8, 8), tmp_path, None)
    assert "error" not in r and "cadence" in r["stats"] and isinstance(r["findings"], list)
    assert qa.vfr(test_video) in (True, False)


# ------------------------------------------------------------------ beats + J/L
def test_snap_to_beats_moves_cuts_but_keeps_total_length():
    plan = plan_of(2.05, 2.0, 2.0)
    beats = [i * 0.5 for i in range(20)]                       # 120 bpm
    new, moves = plan_edit.snap_to_beats(plan, beats, max_shift_s=0.12)
    assert [m["to_s"] for m in moves] == [2.0, 4.0]
    assert [s["duration_s"] for s in new["scenes"]] == [2.0, 2.0, 2.05]
    assert round(sum(s["duration_s"] for s in new["scenes"]), 3) == 6.05
    assert plan["scenes"][0]["duration_s"] == 2.05                  # original untouched
    far, none = plan_edit.snap_to_beats(plan_of(2.3, 2.0), beats, max_shift_s=0.1)
    assert none == [] and far["scenes"][0]["duration_s"] == 2.3
    tight, none2 = plan_edit.snap_to_beats(plan_of(0.45, 0.5), [0.38], max_shift_s=0.12)     # would leave <0.4 s: refused
    assert none2 == []


def test_detect_beats_on_a_click_track(test_video, tmp_path):
    from scripts.audio import extract_wav
    wav = extract_wav(test_video, tmp_path / "x.wav")
    bpm, beats = plan_edit.detect_beats(wav)
    assert 100 <= bpm <= 140 or 50 <= bpm <= 70 and len(beats) > 10


def test_jl_cut_moves_clip_sound_into_its_own_entry():
    plan = plan_of(3)
    plan["scenes"] += [{"id": "v", "duration_s": 4, "template": "video",
                        "props": {"src": "input/a.mp4", "trim_start_s": 2.0, "audio_lead_s": 0.5, "audio_tail_s": 0.3, "voice": True}}]
    new, notes = plan_edit.apply_jl_cuts(plan)
    a = new["audio"][0]
    assert a["at_s"] == 2.5 and a["trim_start_s"] == 1.5 and a["duration_s"] == 4.8 and a["role"] == "voice"
    assert new["scenes"][1]["props"]["muted"] is True and "audio" not in plan
    capped = plan_edit.apply_jl_cuts({**plan, "scenes": [dict(plan["scenes"][0]), {**plan["scenes"][1], "props": {**plan["scenes"][1]["props"], "trim_start_s": 0.2}}]})[0]
    assert capped["audio"][0]["trim_start_s"] == 0.0 and capped["audio"][0]["at_s"] == 2.8     # lead limited by the file start
    sp = plan_edit.apply_jl_cuts({**plan, "scenes": [plan["scenes"][0], {**plan["scenes"][1], "props": {**plan["scenes"][1]["props"], "speed": 2}}]})
    assert "audio" in sp[0] and sp[0]["audio"] == [] and "skipped" in sp[1][0]


# ------------------------------------------------------------------ cover
def test_cover_prefers_a_sharp_well_exposed_frame(tmp_path):
    rng = np.random.default_rng(0)
    sharp = (rng.uniform(0.2, 0.7, (120, 90, 3))).astype(np.float32)
    blurry = cv2.GaussianBlur(sharp, (0, 0), 6)
    dark = sharp * 0.2
    t, s, scores = cover.pick([(1.0, dark), (2.0, blurry), (3.0, sharp)])
    assert t == 3.0 and s == max(x for _, x in scores)


def test_make_cover_on_a_real_video(test_video, tmp_path):
    r = cover.make_cover(test_video, tmp_path / "c.jpg")
    assert (tmp_path / "c.jpg").stat().st_size > 1000 and 0 < r["t"] < probe(test_video)["duration_s"]


# ------------------------------------------------------------------ cfr
def test_variable_frame_rate_clip_gets_a_constant_rate(tmp_path):
    import subprocess
    pub = tmp_path / "public"
    (pub / "input").mkdir(parents=True)
    src = pub / "input" / "v.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=3", "-vf",
                    "select='not(mod(n,3))+not(mod(n,7))',setpts=N/(30*TB)*1.0+random(0)*0.01/TB", "-fps_mode", "vfr", "-c:v", "libx264", str(src)], check=False)
    plan = {"fps": 30, "scenes": [{"id": "a", "duration_s": 2, "template": "video", "props": {"src": "input/v.mp4", "denoise": "light"}}]}
    new, rep = fx.expand_plan(plan, public_dir=pub, work=tmp_path / "w", hooks={"vfr": lambda p: True})
    assert not rep["errors"], rep
    out = pub / new["scenes"][0]["props"]["src"]
    assert rep["clips"]["a"]["cfr"] and out.exists() and qa.vfr(out) is False
