"""Rule smoke_before_long_run: a long runner-side job runs the tiny preflight test first and stops on failure."""
from pathlib import Path


def test_long_jobs_run_smoke_first():
    src = Path(__file__).resolve().parent.parent.joinpath("scripts", "cli.py").read_text(encoding="utf-8")
    i = src.index("from . import smoke")
    j = src.index("_stills_api_run(raw, name, a)", i)
    assert i < j, "smoke must run before the long stills job"
    assert "return 3" in src[i:j], "smoke failure must stop the run"


def test_smoke_skips_gpu_queue_modes():
    from scripts import smoke
    ok, why = smoke.run({"mode": "image", "engine": "flux"}, None, log=lambda *a: None)
    assert ok and why == "skipped"
