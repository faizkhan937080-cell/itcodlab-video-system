import pytest
from scripts import library as lib


def test_add_find_scan(drive):
    e = lib.add_entry(drive, "sfx", "Whoosh 1", "cc0", "openverse", tags=["whoosh", "swipe"])
    assert e["id"] == "sfx-whoosh-1"
    assert lib.add_entry(drive, "sfx", "Whoosh 1", "cc0")["added"] == e["added"]  # no duplicate
    assert len(lib.load(drive)) == 1
    with pytest.raises(ValueError):
        lib.add_entry(drive, "music", "Song", "by-nc")  # non-commercial refused
    drive.put_text("assets/library/font/Courier Prime Bold.ttf", "x")
    new = lib.scan(drive)
    assert [n["id"] for n in new] == ["font-courier-prime-bold"] and "courier" in new[0]["tags"]
    assert lib.scan(drive) == []  # second scan finds nothing new
    assert [i["id"] for i in lib.find(drive, "swipe")] == ["sfx-whoosh-1"]
    assert "Whoosh 1" in drive.read_text("assets/library/INDEX.md")


def _wav(path, y):
    import soundfile as sf
    sf.write(str(path), y.astype("float32"), 22050)
    return path


def _base():
    import numpy as np
    t = np.arange(22050 * 2) / 22050
    rng = np.random.default_rng(1)
    return t, 0.4 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 880 * t) * np.sin(2 * np.pi * 2 * t) + 0.05 * rng.standard_normal(len(t))


def test_dedupe_four_tiers(drive, tmp_path):
    import numpy as np
    t, base = _base()
    a = _wav(tmp_path / "a.wav", base)
    e1, tier = lib.add_file(drive, a, "sfx", "Whoosh A", "cc0", tags=["whoosh"])
    assert tier == "different" and e1["fingerprint"]["sha256"]
    # same bytes, other name -> only an alias
    e2, tier = lib.add_file(drive, a, "sfx", "Whoosh Copy", "cc0")
    assert tier == "exact" and e2["id"] == e1["id"] and "Whoosh Copy" in e2["aliases"] and len(lib.load(drive)) == 1
    # quieter re-encode (gain only) -> near = same item
    e3, tier = lib.add_file(drive, _wav(tmp_path / "b.wav", base * 0.5), "sfx", "Whoosh Quiet", "cc0")
    assert tier == "near" and e3["id"] == e1["id"] and len(lib.load(drive)) == 1
    # micro change (extra tone) -> variant: kept, linked, NOT merged
    e4, tier = lib.add_file(drive, _wav(tmp_path / "c.wav", base + 0.15 * np.sin(2 * np.pi * 3000 * t)), "sfx", "Whoosh Bright", "cc0")
    assert tier == "variant" and e4["variant_of"] == e1["id"] and len(lib.load(drive)) == 2
    # unrelated sound with the SAME name -> own item, not swallowed
    e5, tier = lib.add_file(drive, _wav(tmp_path / "d.wav", 0.4 * np.sin(2 * np.pi * 200 * t) * np.exp(-t)), "sfx", "Whoosh A", "cc0")
    assert tier == "different" and e5["id"] != e1["id"]
    lib.mark_used(drive, e1["id"], "reel-X", "rahul")
    assert lib.load(drive)[0]["used_by"][-1]["creator"] == "rahul"


def test_scan_flags_duplicates_without_deleting(drive, tmp_path):
    _, base = _base()
    (drive.root / "assets/library/sfx").mkdir(parents=True, exist_ok=True)
    for n in ("one.wav", "two.wav"):
        _wav(drive.root / "assets/library/sfx" / n, base)
    new = lib.scan(drive)
    assert len(new) == 2 and new[1]["duplicate_of"] == new[0]["id"] and new[1]["tier"] == "exact"
    assert (drive.root / "assets/library/sfx/two.wav").exists()  # nothing was removed


def test_fetch_from_openverse_adds_licensed_item_by_name(drive, tmp_path):
    import numpy as np
    _, base = _base()
    src = _wav(tmp_path / "x.wav", base)

    def dl(url, dest):
        open(dest, "wb").write(open(src, "rb").read())
    res = [{"license": "cc0", "url": "http://x/pop.wav", "duration": 1500, "filetype": "wav", "title": "pop"},
           {"license": "by-nc", "url": "http://x/bad.wav", "duration": 800}]
    e = lib.fetch_from_openverse(drive, "pop", "sfx", "Pop Soft", ["pop"], search_fn=lambda *a, **k: res, download_fn=dl,
                                 measure_fn=lambda p: (1.5, -6.0))
    assert e["licence"] == "cc0" and e["id"] == "sfx-pop-soft" and drive.exists(e["file"])
    assert lib.fetch_from_openverse(drive, "pop", "sfx", "x", search_fn=lambda *a, **k: [res[1]], download_fn=dl) is None
    e2 = lib.fetch_from_openverse(drive, "pop", "sfx", "Pop Again", search_fn=lambda *a, **k: res, download_fn=dl,
                                  measure_fn=lambda p: (1.5, -6.0))
    assert e2["id"] == e["id"] and "Pop Again" in e2["aliases"]  # same sound twice = alias, no second copy


def test_resolve_recipe_names(drive):
    from scripts import resolve
    lib.add_entry(drive, "font", "Space Mono Bold", "ofl", tags=["mono"])
    card = {"reel": "r1", "elements": {"fonts": [{"name": "Space Mono Bold"}, {"name": "Ransom Note"}],
                                       "music": {"title": "Some Song"}, "sfx": [{"label": "pop"}, {"type": "not analysed"}]}}
    r = resolve.resolve(drive, card)
    assert r["found"] == {"Space Mono Bold": "font-space-mono-bold"}
    assert {m["name"] for m in r["missing"]} == {"Ransom Note", "Some Song", "pop"}
