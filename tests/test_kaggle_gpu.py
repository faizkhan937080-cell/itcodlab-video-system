"""Kaggle GPU path: off by default, never raises, never leaks the key, rejects stale/mismatched output, falls back to CPU."""
import json
import os
from pathlib import Path

from scripts import audio, kaggle_gpu


def _wav(tmp_path):
    p = tmp_path / "a.wav"
    p.write_bytes(b"RIFFfake-wav-bytes")
    return p


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("ITCOD_KAGGLE_GPU", raising=False)
    assert kaggle_gpu.enabled() is False


def test_needs_env_and_config(monkeypatch):
    monkeypatch.setenv("ITCOD_KAGGLE_GPU", "1")
    assert kaggle_gpu.enabled() is False  # config flag kaggle_gpu is false until equality is proven


def test_token_mapping_and_no_leak(monkeypatch):
    monkeypatch.setenv("KAGGLE_KEY", "KGAT_secretvalue123")
    monkeypatch.setenv("KAGGLE_USERNAME", "u")
    e = kaggle_gpu._env()
    assert e["KAGGLE_API_TOKEN"] == "KGAT_secretvalue123" and "KAGGLE_KEY" not in e
    assert "KGAT_secretvalue123" not in kaggle_gpu._clean("boom KGAT_secretvalue123 end")
    monkeypatch.setenv("KAGGLE_KEY", "legacyhex")
    assert kaggle_gpu._env()["KAGGLE_KEY"] == "legacyhex"


def test_prepare_ships_same_code_and_gpu_kernel(tmp_path):
    ds, kn = kaggle_gpu.prepare(_wav(tmp_path), tmp_path / "w", "user1")
    names = {p.name for p in ds.iterdir()}
    assert {"ears.wav", "py__audio.py", "py__common.py", "py__script_metrics.py", "limits.json", "dataset-metadata.json"} <= names
    assert (ds / "py__audio.py").read_text() == Path("scripts/audio.py").read_text()
    meta = json.loads((kn / "kernel-metadata.json").read_text())
    assert meta["enable_gpu"] is True and meta["is_private"] is True and meta["dataset_sources"] == ["user1/itcod-ears-in"]
    compile((kn / "ears_kernel.py").read_text(), "kernel", "exec")


def test_missing_credentials_returns_none(monkeypatch, tmp_path):
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    assert kaggle_gpu.transcribe(_wav(tmp_path)) is None


def _fake_cli(tmp_path, wav, sha_override=None, final="COMPLETE"):
    calls = []

    def cli(args, timeout=300):
        calls.append(args[:2])
        if args[:2] == ["datasets", "status"]:
            return 0, "ready", ""
        if args[0] == "datasets":
            return 0, "ok", ""
        if args[:2] == ["kernels", "push"]:
            return 0, "pushed", ""
        if args[:2] == ["kernels", "status"]:
            return 0, f'has status "KernelWorkerStatus.{final}"', ""
        if args[:2] == ["kernels", "output"]:
            out = Path(args[args.index("-p") + 1])
            out.mkdir(parents=True, exist_ok=True)
            (out / "transcript.json").write_text(json.dumps({
                "input_sha1": sha_override or kaggle_gpu._sha1(wav),
                "transcript": {"available": True, "language": "en", "segments": [], "text": "hi", "coverage_ratio": 1.0}}))
            return 0, "", ""
        return 1, "", "unknown"
    return cli, calls


def _setup(monkeypatch):
    monkeypatch.setenv("KAGGLE_KEY", "KGAT_x")
    monkeypatch.setenv("KAGGLE_USERNAME", "user1")
    monkeypatch.setattr(kaggle_gpu.shutil, "which", lambda n: "/usr/bin/kaggle")
    monkeypatch.setattr(kaggle_gpu.time, "sleep", lambda s: None)


def test_happy_path(monkeypatch, tmp_path):
    _setup(monkeypatch)
    wav = _wav(tmp_path)
    cli, calls = _fake_cli(tmp_path, wav)
    monkeypatch.setattr(kaggle_gpu, "_cli", cli)
    res = kaggle_gpu.transcribe(wav, timeout_s=60, poll_s=0)
    assert res and res["text"] == "hi"
    assert ["kernels", "push"] in calls


def test_stale_input_hash_rejected(monkeypatch, tmp_path):
    _setup(monkeypatch)
    wav = _wav(tmp_path)
    cli, _ = _fake_cli(tmp_path, wav, sha_override="deadbeef")
    monkeypatch.setattr(kaggle_gpu, "_cli", cli)
    assert kaggle_gpu.transcribe(wav, timeout_s=60, poll_s=0) is None


def test_kernel_error_gives_none(monkeypatch, tmp_path):
    _setup(monkeypatch)
    wav = _wav(tmp_path)
    cli, _ = _fake_cli(tmp_path, wav, final="ERROR")
    monkeypatch.setattr(kaggle_gpu, "_cli", cli)
    assert kaggle_gpu.transcribe(wav, timeout_s=60, poll_s=0) is None


def test_audio_falls_back_to_cpu_when_gpu_returns_none(monkeypatch, tmp_path):
    monkeypatch.setenv("ITCOD_KAGGLE_GPU", "1")
    monkeypatch.setattr(kaggle_gpu, "enabled", lambda: True)
    monkeypatch.setattr(kaggle_gpu, "transcribe", lambda wav: None)
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", None)  # CPU path unavailable here: must not crash
    assert audio.transcribe(_wav(tmp_path)) == {"available": False}


def test_compare_detects_difference():
    a = {"language": "en", "text": "x y", "segments": [{"start": 0, "end": 1, "text": "x y", "words": [{"w": "x"}, {"w": "y"}]}]}
    assert kaggle_gpu.compare(a, json.loads(json.dumps(a)))["identical"] is True
    b = json.loads(json.dumps(a))
    b["segments"][0]["end"] = 1.2
    r = kaggle_gpu.compare(a, b)
    assert r["identical"] is False and r["segments_identical_share"] == 0.0
