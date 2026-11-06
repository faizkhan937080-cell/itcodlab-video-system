from scripts.tune import tune_hints


def test_editing_hints_name_the_number_to_change():
    target = {"format": {"width": 2160, "height": 3840, "fps": 30}, "cut_rhythm": {"cuts_per_min": 40.0, "beat_synced_share": 0.8}}
    summary = {"video": {"width": 1080, "height": 1920, "fps": 30},
               "cut_rhythm": {"cuts_per_min": 20.0}, "audio": {"bpm": 120, "cut_beat_sync": {"share_within_80ms": 0.3}}}
    hints = {h["param"]: h for h in tune_hints("editing", target, summary)}
    assert hints["plan.output"]["change"] == {"width": 2160, "height": 3840}
    assert hints["scenes[].duration_s"]["change"] == "x0.5"          # half the cuts -> scenes half as long
    assert "0.5" in hints["scenes[].start"]["change"]                 # 120 BPM -> 0.5 s grid


def test_matching_output_has_no_hints_and_corpus_targets_work():
    target = {"type": "corpus", "targets": {"format.width": 1080, "format.height": 1920, "cut_rhythm.cuts_per_min": 30.0}}
    summary = {"video": {"width": 1080, "height": 1920, "fps": 30}, "cut_rhythm": {"cuts_per_min": 31.0}}
    assert tune_hints("editing", target, summary) == []


def test_sound_hints_loudness_and_tempo():
    target = {"loudness": {"integrated_lufs": -14.0}, "tempo": {"bpm": 100}}
    summary = {"audio": {"ebu_r128": {"integrated_lufs": -20.0}, "bpm": 130}}
    params = {h["param"] for h in tune_hints("sound", target, summary)}
    assert params == {"plan.audio_target_lufs", "plan.audio[].track"}
