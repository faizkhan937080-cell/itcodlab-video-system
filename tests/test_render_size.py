from scripts import analyze, render
from scripts.common import limits
from scripts.dna import validate


def plan(src=None, output=None, orientation="landscape"):
    p = {"title": "t", "fps": 30, "orientation": orientation,
         "scenes": [{"id": "s1", "duration_s": 2, "template": "video" if src else "title",
                     "props": {"src": src} if src else {"text": "x"}}]}
    if output:
        p["output"] = output
    return p


def test_4k_raw_gives_4k_output_and_half_preview():
    lim = limits()
    pl = plan("input/raw/a.mp4")
    assert render.source_clips(pl) == ["input/raw/a.mp4"]
    assert render.master_size(pl, lim, [(3840, 2160)]) == (3840, 2160)
    assert validate("scene", pl) == []


def test_biggest_clip_wins_and_portrait_4k_kept():
    lim = limits()
    assert render.master_size(plan("a.mp4"), lim, [(1920, 1080), (2160, 3840)]) == (2160, 3840)


def test_1080_raw_stays_1080_not_upscaled_to_4k():
    assert render.master_size(plan("input/a.mp4"), limits(), [(1920, 1080)]) == (1920, 1080)


def test_no_clips_uses_4k_master_default():
    assert render.master_size(plan(), limits(), []) == (3840, 2160)
    assert render.master_size(plan(orientation="portrait"), limits(), None) == (2160, 3840)


def test_explicit_output_wins_and_odd_sizes_made_even():
    assert render.master_size(plan("a.mp4", output={"width": 2560, "height": 1440}), limits(), [(3840, 2160)]) == (2560, 1440)
    assert render.master_size(plan("a.mp4"), limits(), [(1919, 1079)]) == (1918, 1078)


def test_8k_capped_at_max_long_edge():
    w, h = render.master_size(plan("a.mp4"), limits(), [(15360, 8640)])
    assert max(w, h) <= 7680 and w % 2 == 0 and h % 2 == 0


def test_phone_rotation_swaps_to_display_size():
    j = {"streams": [{"codec_type": "video", "width": 3840, "height": 2160, "r_frame_rate": "30/1",
                      "side_data_list": [{"rotation": -90}]}], "format": {"duration": "5"}}
    p = analyze.parse_probe(j)
    assert (p["width"], p["height"], p["rotation"]) == (2160, 3840, 270)
    j["streams"][0]["side_data_list"] = []
    assert analyze.parse_probe(j)["width"] == 3840


def test_plan_with_audio_tracks_and_raw_audio_assets_are_staged():
    pl = plan("input/raw/a.mp4")
    pl["audio"] = [{"src": "assets/music/bed.mp3", "volume": 0.3, "fade_in_s": 1, "fade_out_s": 2},
                   {"src": "assets/vo/line1.wav", "at_s": 1.5}]
    assert validate("scene", pl) == []
    found = set()
    render._asset_paths(pl, found)
    assert found == {"input/raw/a.mp4", "assets/music/bed.mp3", "assets/vo/line1.wav"}
    pl["audio"][0]["volume"] = 3
    assert validate("scene", pl) != []
