import json
import time
from scripts import guards as G


def test_voice_pace_blocks_rushed_voice():
    words = " ".join(["word"] * 146)
    assert not G.voice_pace(words, 40.0)[0]          # ~219 wpm, rushed even for the fast reference
    assert G.voice_pace(words, 62.0)[0]               # ~141 wpm


def test_long_prompt_blocked_short_ok():
    assert not G.prompts_fit([{"id": "a", "prompt": " ".join(["x"] * 120)}])[0]
    assert G.prompts_fit([{"id": "b", "prompt": "a lit cigarette and a cup of tea, dark macro render"}])[0]


def test_motion_claim_needs_honesty():
    spec = {"claim": "3d_motion_graphics", "mode": "parallax", "scenes": [{"id": "v1"}]}
    assert not G.motion_honest(spec)[0]
    assert G.motion_honest(spec, faiz_ok_substitute=True)[0]
    assert G.motion_honest({"scenes": [{"id": "x"}]})[0]


def test_ready_needs_a_look_and_a_good_score(tmp_path):
    assert not G.looked("j1", tmp_path)[0]
    G.record_look("j1", 4, "pink cup", tmp_path)
    assert not G.looked("j1", tmp_path)[0]
    G.record_look("j1", 8, "ok", tmp_path)
    assert G.looked("j1", tmp_path)[0]


def test_waiting_stalls_and_approved_is_remembered(tmp_path):
    G.pending_add("dna-gate2", "thebrainmaze DNA needs Y", tmp_path)
    old = time.time() + 3 * 3600
    assert "STALLED" in G.brief_lines(tmp_path, now=old)[0]
    G.approved_add("dna-gate2", "Faiz Y", tmp_path)
    lines = G.brief_lines(tmp_path)
    assert G.is_approved("dna-gate2", tmp_path) and all("WAITING" not in l for l in lines) and "dna-gate2" in lines[0]


def test_style_card_prompt_fits_and_keeps_subject_first():
    from scripts import style_card as S
    card = json.load(open("config/style-cards/thebrainmaze.json"))
    r = S.shot_prompt(card, "cigarette smoke entering the throat", "drifting down the airway")
    assert r["prompt"].startswith("cigarette smoke") and r["tokens"] <= 75 and r["negative"]
    long = S.shot_prompt(card, " ".join(["detail"] * 60), "")
    assert long["tokens"] <= 75
