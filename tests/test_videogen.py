import json

import pytest

from scripts import videogen as vg


def test_frames_are_8k_plus_1():
    assert vg.frames_for(4) == 97 and vg.frames_for(1) == 25 and vg.frames_for(0.1) == 9


def test_gate_ltx_free_others_blocked():
    assert vg.gate({"engine": "ltx"}) == "ltx" and vg.gate({"engine": "wan"}) == "wan" and vg.gate({}) == "wan"
    with pytest.raises(vg.EngineBlocked, match="Faiz's Y"):
        vg.gate({"engine": "minimax"}, {"minimax_approved": False})
    with pytest.raises(vg.EngineBlocked, match="not built"):
        vg.gate({"engine": "minimax"}, {"minimax_approved": True})
    with pytest.raises(vg.EngineBlocked, match="allow_paid"):
        vg.gate({"engine": "veo"})
    with pytest.raises(vg.EngineBlocked, match="unknown"):
        vg.gate({"engine": "x"})


def test_prepare_writes_dataset_and_kernel(tmp_path):
    img = tmp_path / "a.png"
    img.write_bytes(b"png")
    spec = vg.build_spec({"prompt": "p", "seconds": 4}, img)
    ds, kn = vg.prepare(spec, img, tmp_path / "w", "owner")
    assert json.loads((ds / "spec.json").read_text())["num_frames"] == 97 and "Wan" in json.loads((ds / "spec.json").read_text())["model"] and (ds / "in.png").exists()
    meta = json.loads((kn / "kernel-metadata.json").read_text())
    assert meta["enable_gpu"] and meta["id"] == "owner/itcod-vgen" and meta["dataset_sources"] == ["owner/itcod-vgen-in"]
    compile((kn / "vgen_kernel.py").read_text(), "kernel", "exec")


def test_run_without_credentials_is_a_clear_no(monkeypatch, tmp_path):
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    r = vg.run(vg.build_spec({}, None), None, tmp_path)
    assert r["ok"] is False and "Kaggle" in r["error_hint"]
