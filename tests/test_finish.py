import shutil

from scripts import audio, finish


def test_loudness_normalized_to_target_and_video_untouched(test_video, tmp_path):
    v = tmp_path / "x.mp4"
    shutil.copyfile(test_video, v)
    before = audio.loudness_ebu(audio.extract_wav(v, tmp_path / "b.wav"))["integrated_lufs"]
    target = round(before - 3.0, 1)
    r = finish.normalize_loudness(v, target, tmp_path)
    assert r["changed"] is True
    after = audio.loudness_ebu(audio.extract_wav(v, tmp_path / "a.wav"))
    assert abs(after["integrated_lufs"] - target) <= 1.0, (after, target)
    assert r["reached_target"] is True and after["true_peak_dbtp"] <= -0.5
    again = finish.normalize_loudness(v, after["integrated_lufs"], tmp_path)
    assert again["changed"] is False


def test_target_lufs_priority():
    assert finish.target_lufs({"audio_target_lufs": -14}, {"sound": {"loudness": {"integrated_lufs": -20}}}) == -14.0
    assert finish.target_lufs({}, {"sound": {"loudness": {"integrated_lufs": -20}}}) == -20.0
    assert finish.target_lufs({}, {}) is None


def test_clone_check_runs_on_a_real_video_and_reports_per_type(test_video, tmp_path):
    dna = {"type": "editing", "format": {"width": 540, "height": 960}, "cut_rhythm": {"cuts_per_min": 1000.0}}
    r = finish.clone_check(test_video, {}, {"editing": dna}, tmp_path)
    assert r["editing"]["pass"] is False and any("cuts_per_min" in d for d in r["editing"]["differences"])
    assert not any("format.width" in d for d in r["editing"]["differences"])   # size matched


def test_boost_is_limited_by_true_peak_ceiling_and_says_so(test_video, tmp_path):
    v = tmp_path / "y.mp4"
    shutil.copyfile(test_video, v)
    before = audio.loudness_ebu(audio.extract_wav(v, tmp_path / "b.wav"))["integrated_lufs"]
    r = finish.normalize_loudness(v, before + 12.0, tmp_path)
    assert r["changed"] is True and r["reached_target"] is False and "ceiling" in r["note"]
    assert audio.loudness_ebu(audio.extract_wav(v, tmp_path / "c.wav"))["true_peak_dbtp"] <= -0.5
