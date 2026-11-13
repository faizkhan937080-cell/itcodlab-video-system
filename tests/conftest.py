import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _no_real_review_push(monkeypatch):
    """Tests must never push to the real GitHub remote."""
    monkeypatch.setenv("ITCOD_NO_REVIEW", "1")


@pytest.fixture(autouse=True)
def _no_fake_cost_rows(monkeypatch, tmp_path):
    """Tests must never write fake rows into the real costs/local folder (they poisoned estimates once)."""
    from scripts import costs
    monkeypatch.setattr(costs, "LOCAL", tmp_path / "costs_local")


@pytest.fixture(scope="session")
def test_video(tmp_path_factory):
    """24 s portrait video: A B A B (repeats), a dissolve, a hard cut and a pan, plus a 120 BPM click track."""
    import math
    import struct
    import wave
    d = tmp_path_factory.mktemp("vid")
    sr = 22050
    with wave.open(str(d / "click.wav"), "w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
        data = bytearray()
        for n in range(sr * 24):
            t = n / sr
            ph = t % 0.5
            v = 0.8 * math.sin(2 * math.pi * 1000 * t) * (1 - ph / 0.03) if ph < 0.03 else 0.0
            data += struct.pack("<h", int(v * 32767))
        f.writeframes(bytes(data))
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30"]
    S = "540x960"

    def ff(*args):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True, cwd=d)

    ff("-f", "lavfi", "-i", f"testsrc2=s={S}:r=30:d=4", *enc, "seg1.mp4")
    ff("-f", "lavfi", "-i", f"smptebars=s={S}:r=30:d=4", *enc, "seg2.mp4")
    ff("-f", "lavfi", "-i", f"testsrc2=s={S}:r=30:d=4", *enc, "seg3.mp4")
    ff("-f", "lavfi", "-i", f"smptebars=s={S}:r=30:d=4", *enc, "seg4.mp4")
    ff("-f", "lavfi", "-i", f"testsrc2=s={S}:r=30:d=2", "-f", "lavfi", "-i", f"rgbtestsrc=s={S}:r=30:d=2",
       "-filter_complex", "[0][1]xfade=transition=fade:duration=1:offset=1,format=yuv420p", *enc, "seg5.mp4")
    ff("-f", "lavfi", "-i", "testsrc=s=1080x1920:r=30:d=6",
       "-vf", "crop=540:960:x='mod(t*300,540)':y=0", *enc, "seg6.mp4")
    (d / "list.txt").write_text("".join(f"file 'seg{i}.mp4'\n" for i in range(1, 7)))
    ff("-f", "concat", "-safe", "0", "-i", "list.txt", "-i", "click.wav", "-c:v", "copy", "-c:a", "aac",
       "-shortest", "test_video.mp4")
    return d / "test_video.mp4"


@pytest.fixture(scope="session")
def analysed(test_video, tmp_path_factory):
    from scripts.pack import run_pipeline
    out = tmp_path_factory.mktemp("analysis")
    return run_pipeline(test_video, out, job_id="t1", mode="both", with_transcript=False)


@pytest.fixture()
def drive(tmp_path, monkeypatch):
    """A local folder that behaves like the mounted Drive."""
    root = tmp_path / "drive"
    monkeypatch.setenv("ITCOD_DRIVE_ROOT", str(root))
    from scripts.storage import Storage
    return Storage(root=str(root))
