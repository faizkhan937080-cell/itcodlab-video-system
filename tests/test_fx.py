import json
import re
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts import fx, matte, safezone, track, voice
from scripts.analyze import probe
from scripts.common import limits
from scripts.dna import validate

ROOT = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------ speed
def test_ramp_segments_cover_the_window_and_follow_the_keys():
    segs = fx.ramp_segments([{"at_s": 0, "speed": 1}, {"at_s": 2, "speed": 0.25}, {"at_s": 4, "speed": 1}], 0.0, 6.0)
    assert segs[0][0] == 0.0 and segs[-1][1] == 6.0
    assert all(a2 == b1 for (_, b1, _), (a2, _, _) in zip(segs, segs[1:]))          # no gaps
    slow = min(s for _, _, s in segs)
    assert 0.2 <= slow <= 0.45 and segs[-1][2] == 1.0                                 # slows down in the middle, back to 1
    assert len(segs) <= fx.MAX_SEGMENTS
    assert fx.out_duration([(0, 4, 2.0)]) == 2.0


def test_atempo_chain_stays_in_ffmpeg_range():
    for s in (0.1, 0.3, 0.5, 1.0, 1.7, 4.0, 8.0):
        parts = [float(x.split("=")[1]) for x in fx.atempo_chain(s).split(",")]
        assert all(0.5 - 1e-6 <= p <= 2.0 + 1e-6 for p in parts)
        assert abs(np.prod(parts) - s) / s < 1e-3


def test_punch_keys_snap_in_and_return_to_normal():
    k = fx.punch_keys([1.0, 2.0])
    assert [x["at_s"] for x in k] == sorted(x["at_s"] for x in k)
    assert max(x["scale"] for x in k) == 1.12 and k[-1]["scale"] == 1.0
    assert validate("scene", {"title": "t", "fps": 30, "orientation": "portrait", "scenes": [
        {"id": "a", "duration_s": 3, "template": "title", "props": {"text": "x"}, "zoom": k}]}) == []


def _ffmpeg_clip(path, secs=4):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=size=320x240:rate=15:duration={secs}",
                    "-f", "lavfi", "-i", f"sine=frequency=300:duration={secs}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(path)], check=True)


def test_retime_real_clip_halves_duration_at_2x_and_consumes_trim(tmp_path):
    pub = tmp_path / "public"
    (pub / "input").mkdir(parents=True)
    _ffmpeg_clip(pub / "input" / "a.mp4")
    plan = {"scenes": [{"id": "s1", "duration_s": 2, "template": "video", "props": {"src": "input/a.mp4", "speed": 2.0, "trim_start_s": 0}}]}
    new, rep = fx.expand_plan(plan, public_dir=pub, work=tmp_path / "w")
    assert not rep["errors"], rep
    p = new["scenes"][0]["props"]
    assert p["src"].startswith("fx/") and "speed" not in p and "trim_start_s" not in p
    assert plan["scenes"][0]["props"]["speed"] == 2.0                             # stored plan untouched
    info = probe(pub / p["src"])
    assert abs(info["duration_s"] - 2.0) < 0.3 and info["has_audio"]
    assert abs(rep["clips"]["s1"]["out_duration_s"] - 2.0) < 0.05


def test_speed_ramp_and_smooth_run_on_a_real_clip(tmp_path):
    pub = tmp_path / "public"
    (pub / "input").mkdir(parents=True)
    _ffmpeg_clip(pub / "input" / "a.mp4")
    plan = {"scenes": [{"id": "s1", "duration_s": 5, "template": "video",
                        "props": {"src": "input/a.mp4", "speed_ramp": [{"at_s": 0, "speed": 1}, {"at_s": 2, "speed": 0.5}, {"at_s": 4, "speed": 1}]}}]}
    new, rep = fx.expand_plan(plan, public_dir=pub, work=tmp_path / "w")
    assert not rep["errors"], rep
    assert probe(pub / new["scenes"][0]["props"]["src"])["duration_s"] > 4.0       # slowed down: longer than the source


def test_stabilize_runs_and_a_failing_effect_keeps_the_clip(tmp_path):
    pub = tmp_path / "public"
    (pub / "input").mkdir(parents=True)
    _ffmpeg_clip(pub / "input" / "a.mp4", 2)
    plan = {"scenes": [{"id": "s1", "duration_s": 2, "template": "video", "props": {"src": "input/a.mp4", "stabilize": "normal"}},
                       {"id": "s2", "duration_s": 2, "template": "video", "props": {"src": "input/a.mp4", "speed": 2, "trim_start_s": 0.5}}]}
    new, rep = fx.expand_plan(plan, public_dir=pub, work=tmp_path / "w")
    assert not rep["errors"] and rep["clips"]["s1"]["stabilize"] in ("vidstab", "deshake")
    def boom(*a, **k):
        raise RuntimeError("nope")
    pub2 = tmp_path / "pub2"
    (pub2 / "input").mkdir(parents=True)
    shutil.copy(pub / "input" / "a.mp4", pub2 / "input" / "a.mp4")
    new2, rep2 = fx.expand_plan(plan, public_dir=pub2, work=tmp_path / "w2", hooks={"stabilize": boom})
    assert "s1" in rep2["errors"] and new2["scenes"][0]["props"]["src"] == "input/a.mp4"      # kept as shot
    assert "stabilize" not in new2["scenes"][0]["props"] and new2["scenes"][1]["props"]["src"].startswith("fx/")


# ------------------------------------------------------------------ tracking / reframe
def _moving_square_video(path, n=45, w=320, h=240):
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 15, (w, h))
    rng = np.random.default_rng(0)
    bg = rng.integers(60, 100, (h, w, 3)).astype(np.uint8)
    for i in range(n):
        fr = bg.copy()
        x = 40 + i * 4
        cv2.rectangle(fr, (x, 90), (x + 50, 150), (30, 200, 240), -1)
        cv2.circle(fr, (x + 25, 120), 12, (255, 255, 255), -1)
        vw.write(fr)
    vw.release()
    return n


def test_follow_path_tracks_a_moving_box(tmp_path):
    v = tmp_path / "m.mp4"
    _moving_square_video(v)
    path = track.follow_path(v, (40 / 320, 90 / 240, 50 / 320, 60 / 240))
    assert len(path) >= 20 and path[0]["t"] == 0.0
    assert path[-1]["x"] - path[0]["x"] > 0.3                    # moved right across the frame
    assert all(0 <= p["x"] <= 1 and 0 < p["w"] < 0.6 for p in path)
    json.dumps(path)


def test_follow_face_uses_the_detector_and_asks_for_a_box_without_one(tmp_path):
    v = tmp_path / "m.mp4"
    _moving_square_video(v)
    seen = []
    def fake_face(im):
        seen.append(1)
        h, w = im.shape[:2]
        return [(int(40 / 320 * w), int(90 / 240 * h), int(50 / 320 * w), int(60 / 240 * h))]
    assert track.follow_path(v, "face", face=fake_face)
    with pytest.raises(RuntimeError, match="no face"):
        track.follow_path(v, "face", face=lambda im: [])


def test_camera_follow_deadzone_speed_and_bounds():
    win = 0.32
    still = track.camera_follow([0.5] * 10, 0.5, win)
    assert max(still) - min(still) < 1e-9                                     # subject in the middle: camera does not move
    jump = track.camera_follow([0.5] * 2 + [0.9] * 10, 0.5, win)
    assert all(b - a <= 0.30 * 0.5 + 1e-9 for a, b in zip(jump, jump[1:]))   # glides, no snap
    assert all(win / 2 - 1e-9 <= c <= 1 - win / 2 + 1e-9 for c in jump + track.camera_follow([0.0, 1.0], 0.5, win))


def test_reframe_path_follows_a_moving_face(tmp_path):
    v = tmp_path / "m.mp4"
    _moving_square_video(v, n=60)
    def fake_face(im):
        h, w = im.shape[:2]
        # find the bright circle: its x is the subject
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        ys, xs = np.where(g > 240)
        if len(xs) < 5:
            return []
        return [(int(xs.mean()) - 10, int(ys.mean()) - 10, 20, 20)]
    info = probe(v)
    path = track.reframe_path(v, info, face=fake_face)
    assert path[-1]["x"] > path[0]["x"] + 0.1 and all(0 < p["x"] < 1 for p in path)
    assert track.reframe_path(v, {"width": 1080, "height": 1920}, face=fake_face) == [{"t": 0.0, "x": 0.5}]   # already 9:16
    assert track.output_size(3840, 2160) == (1214, 2160)


def test_track_and_reframe_through_expand_plan(tmp_path):
    pub = tmp_path / "public"
    (pub / "input").mkdir(parents=True)
    _moving_square_video(pub / "input" / "m.mp4", n=60)
    plan = {"scenes": [{"id": "s", "duration_s": 4, "template": "video",
                        "props": {"src": "input/m.mp4", "reframe": "auto", "track_from": {"box": [40 / 320, 90 / 240, 50 / 320, 60 / 240]}}}]}
    new, rep = fx.expand_plan(plan, public_dir=pub, work=tmp_path / "w", hooks={"face": lambda im: []})
    p = new["scenes"][0]["props"]
    assert not rep["errors"], rep
    assert p["reframe_path"] and p["follow"] and abs(p["src_aspect"] - 320 / 240) < 1e-3


# ------------------------------------------------------------------ voice
def test_silence_log_to_speech_windows_and_ducking():
    log = "silence_start: 2.0\nsilence_end: 4.0 | silence_duration: 2.0\nsilence_start: 4.2\nsilence_end: 5.0\nsilence_start: 8.0"
    w = voice.windows_from_silence(log, 10.0)
    assert w == [(0.0, 2.0), (4.0, 4.2), (5.0, 8.0)]
    assert voice.windows_from_silence("", 5.0) == [(0.0, 5.0)]
    d = voice.duck_for(1.0, [(0.0, 2.0), (5.0, 8.0)])
    assert d[0] == {"from_s": -1.0, "to_s": 1.0, "gain": voice.DUCK_GAIN} and d[1]["from_s"] == 4.0


def test_prepare_audio_cleans_voice_and_ducks_music(tmp_path):
    pub = tmp_path / "public"
    (pub / "assets").mkdir(parents=True)
    (pub / "fx").mkdir()
    (pub / "assets" / "v.wav").write_bytes(b"x")
    (pub / "assets" / "m.mp3").write_bytes(b"x")
    plan = {"scenes": [{"id": "a", "duration_s": 10, "template": "title"}],
            "audio": [{"src": "assets/v.wav", "role": "voice", "at_s": 1.0}, {"src": "assets/m.mp3", "role": "music", "at_s": 0.0},
                      {"src": "assets/m.mp3", "role": "sfx"}]}
    def fake_clean(src, dst, level):
        Path(dst).write_bytes(b"clean")
    out, rep = voice.prepare_audio(plan, pub, tmp_path, hooks={"clean_audio": fake_clean, "windows": lambda f: [(0.0, 2.0), (6.0, 7.0)]})
    assert out["audio"][0]["src"].startswith("fx/") and rep["cleaned"]
    music = out["audio"][1]
    assert [(d["from_s"], d["to_s"]) for d in music["duck"]] == [(1.0, 3.0), (7.0, 8.0)]
    assert "duck" not in out["audio"][2]                                       # sfx is never ducked


def test_voice_chain_runs_on_real_audio(tmp_path):
    wav = tmp_path / "in.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=2", str(wav)], check=True)
    out = voice.clean_audio_file(wav, tmp_path / "out.wav")
    assert out.exists() and abs(probe_audio(out) - 2.0) < 0.2
    assert voice.windows_from_silence("", 2.0)


def probe_audio(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


# ------------------------------------------------------------------ matte
def test_matte_image_and_short_video_with_alpha(tmp_path):
    im = np.full((60, 80, 3), 120, np.uint8)
    cv2.imwrite(str(tmp_path / "p.png"), im)
    def fake(rgb):
        a = np.zeros(rgb.shape[:2] + (1,), np.uint8)
        a[10:50, 10:70] = 255
        return np.concatenate([rgb, a], -1)
    out = matte.process(tmp_path / "p.png", tmp_path / "o", remover=fake)
    got = cv2.imread(str(out), cv2.IMREAD_UNCHANGED)
    assert got.shape[2] == 4 and got[0, 0, 3] == 0 and got[30, 40, 3] == 255
    assert matte.process(tmp_path / "p.png", tmp_path / "o", remover=lambda x: 1 / 0) == out     # cached: remover not called again
    _moving_square_video(tmp_path / "v.mp4", n=6)
    outv = matte.process(tmp_path / "v.mp4", tmp_path / "o", remover=fake)
    assert outv.suffix == ".webm" and outv.stat().st_size > 0
    lim = dict(limits(), matte={"max_frames": 3})
    with pytest.raises(RuntimeError, match="limit"):
        matte.process(tmp_path / "v.mp4", tmp_path / "o2", remover=fake, lim=lim)


# ------------------------------------------------------------------ safe zones / grain / Remotion
def test_safe_zone_numbers_match_the_remotion_file():
    ts = (ROOT / "remotion/src/lib/safe.ts").read_text()
    z = limits()["safezone"]["strict"]
    got = dict(re.findall(r"(top|bottom|side):\s*([\d.]+)", ts.split("SAFE =")[1].split("}")[0]))
    assert {k: float(v) for k, v in got.items()} == z
    ins = safezone.insets(1080, 1920)
    assert round(ins["top"]) == 269 and round(ins["bottom"]) == 672 and round(ins["left"]) == 65
    assert safezone.insets(1920, 1080)["left"] == pytest.approx(96.0)


def test_safe_zone_lint_flags_boxes_over_ui_and_long_captions():
    plan = {"scenes": [{"id": "a", "overlays": [{"template": "stroke", "box": {"x": 0.1, "y": 0.9, "w": 0.3, "h": 0.08}},
                                                 {"template": "stroke", "box": {"x": 0.3, "y": 0.4, "w": 0.3, "h": 0.1}},
                                                 {"template": "stroke", "box": {"x": 0.3, "y": 0.95, "w": 0.2, "h": 0.04}, "follow": [{"t": 0}]}]}]}
    f = safezone.lint(plan, (1080, 1920))
    assert [x["where"] for x in f] == ["a.overlays[0]"] and f[0]["level"] == "hard"
    caps = {"scenes": [], "captions": [{"text": " ".join(["extraordinarily"] * 4), "start_s": 0, "end_s": 2}], "caption_style": {"size": 2.5}}
    assert safezone.lint(caps, (1080, 1920))


def test_grain_tile_is_deterministic(tmp_path):
    a = fx.grain_tile(tmp_path / "g.png")
    img = cv2.imread(a, cv2.IMREAD_GRAYSCALE)
    assert img.shape == (1024, 1024) and 100 < img.mean() < 156 and img.std() > 20


def test_plan_with_new_fields_validates():
    plan = {"title": "t", "fps": 30, "orientation": "portrait", "vignette": 0.4, "grain": True,
            "scenes": [{"id": "a", "duration_s": 3, "template": "video", "props": {"src": "input/a.mp4", "speed": 0.5},
                        "zoom": [{"at_s": 0, "scale": 1}, {"at_s": 1, "scale": 1.2, "ease": "out"}],
                        "overlays": [{"template": "stroke", "props": {"shape": "circle"}, "box": {"x": 0.5, "y": 0.4, "w": 0.2, "h": 0.1}}]}],
            "audio": [{"src": "assets/v.wav", "role": "voice"}, {"src": "assets/m.mp3", "role": "music", "duck_gain": 0.3}]}
    assert validate("scene", plan) == []
    bad = json.loads(json.dumps(plan))
    bad["scenes"][0]["zoom"][1]["scale"] = 3
    assert validate("scene", bad)


@pytest.mark.skipif(not (ROOT / "remotion/node_modules/.bin/tsc").exists(), reason="Remotion deps not installed")
def test_remotion_code_typechecks():
    r = subprocess.run(["npx", "tsc", "--noEmit", "-p", "."], cwd=ROOT / "remotion", capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-800:]
