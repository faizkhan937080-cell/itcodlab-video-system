import pytest
from scripts import clients, linkcheck, reelid


def test_reelid_shortcode_and_canonical():
    assert reelid.shortcode("https://www.instagram.com/reel/DeoxIgMPlS-/?mdxt=abc") == "DeoxIgMPlS-"
    assert reelid.canonical("https://instagram.com/sahil/reel/DfWAlgTxEkL/?exln=1") == "https://www.instagram.com/reel/DfWAlgTxEkL/"
    assert reelid.shortcode("https://example.com/x") == ""


def test_new_job_id_blocks_second_job_unless_failed(drive):
    assert reelid.new_job_id(drive, "AAAAAA1") == "reel-AAAAAA1"
    drive.write_state("jobs/state/reel-AAAAAA1.json", {"status": "AWAIT_GATE2"})
    with pytest.raises(ValueError):
        reelid.new_job_id(drive, "AAAAAA1")
    drive.write_state("jobs/state/reel-AAAAAA1.json", {"status": "FAILED"})
    assert reelid.new_job_id(drive, "AAAAAA1") == "reel-AAAAAA1-r2"


def test_find_reel_anywhere(drive):
    drive.put_json("creators/_unassigned/videos/BBBBBB2/reel.json", {})
    assert reelid.find_reel(drive, "BBBBBB2") == "creators/_unassigned/videos/BBBBBB2"
    assert reelid.find_reel(drive, "ZZZZZZ9") == ""


def _reel(drive):
    drive.put_json("creators/rahul/dna/r1__scripting__v1.json", {"a": 1})
    drive.put_json("creators/rahul/videos/CCCCCC3/reel.json",
                   {"layout_version": 2, "reel_id": "CCCCCC3", "job": "reel-CCCCCC3", "creator": "rahul",
                    "link": "https://www.instagram.com/reel/CCCCCC3/", "dna": ["creators/rahul/dna/r1__scripting__v1.json"]})


def test_made_from_pins_dna_and_detects_change(drive):
    _reel(drive)
    base, mf = clients.write_made_from(drive, "XYZ Co", "Promo 1", "CCCCCC3")
    assert base == "clients/xyz-co/videos/promo-1" and mf["reference"]["creator"] == "rahul"
    assert linkcheck.run(drive) == []
    import json
    (drive.root / "creators/rahul/dna/r1__scripting__v1.json").write_text(json.dumps({"a": 2}))
    assert any("pinned DNA changed" in i for i in linkcheck.run(drive))


def test_licence_gate():
    assert clients.licence_blockers([{"name": "m", "licence": "cc0"}, {"name": "x", "licence": "needs-licence"},
                                     {"name": "y"}]) == ["x", "y"]


def test_audit_flags_duplicates_and_unfinished(drive):
    drive.put_json("creators/a/videos/DDDDDD4/reel.json", {"layout_version": 2, "reel_id": "DDDDDD4", "dna": []})
    drive.put_json("creators/b/videos/DDDDDD4/reel.json", {"layout_version": 2, "reel_id": "DDDDDD4", "dna": []})
    drive.put_json("creators/a/videos/EEEEEE5/x.json", {})
    out = "\n".join(linkcheck.run(drive))
    assert "duplicate reel DDDDDD4" in out and "unfinished" in out


def test_snapshot_lists_reels_dna_hashes_clients_library(drive):
    from scripts import library, snapshot
    _reel(drive)
    clients.write_made_from(drive, "XYZ", "v1", "CCCCCC3")
    library.add_entry(drive, "font", "Space Mono", "ofl")
    m = snapshot.build(drive)
    assert m["creators"]["rahul"][0]["dna"]["creators/rahul/dna/r1__scripting__v1.json"]
    assert m["clients"]["xyz"][0]["reference"] == "CCCCCC3" and m["library"][0]["id"] == "font-space-mono"


def test_test_data_is_flagged_and_glossary_hints(drive):
    drive.put_json("creators/test-run1/videos/x/reel.json", {})
    assert any("never save tests" in i for i in linkcheck.run(drive))
    from scripts.script_metrics import transcript_txt
    t = transcript_txt({"available": True, "language": "en", "text": "use Textures Lab and pre-5 brushes",
                        "segments": [{"start": 0, "end": 1, "text": "use Textures Lab and pre-5 brushes"}]})
    assert "pre-5 brushes -> p5.brush" in t and "textures lab -> Texture Labs" in t


def test_recipe_elements_carry_confidence():
    from scripts import recipe
    c = recipe.build({"job": "j"}, {"fonts": [{"name": "A"}, {"name": "B", "confidence": "seen"}]})
    assert [f["confidence"] for f in c["elements"]["fonts"]] == ["judged", "seen"]
