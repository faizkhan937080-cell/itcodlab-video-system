"""Green-screen key: synthetic clip (grey box on green) -> alpha WebM; green gone, box kept, colour found automatically."""
import shutil
import subprocess

import cv2
import numpy as np
import pytest

from scripts import matte

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg missing")


def _clip(path):
    w, h, n = 160, 288, 12
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 12, (w, h))
    for _ in range(n):
        fr = np.zeros((h, w, 3), np.uint8)
        fr[:] = (40, 190, 50)                      # BGR studio green
        fr[90:200, 50:110] = (120, 120, 120)       # the "person"
        vw.write(fr)
    vw.release()


def test_key_color_and_alpha(tmp_path):
    src = tmp_path / "gs.mp4"
    _clip(src)
    col = matte.key_color(src)
    r, g, b = int(col[0:2], 16), int(col[2:4], 16), int(col[4:6], 16)
    assert g > 150 and r < 90 and b < 90
    out, used = matte.chroma_key(src, tmp_path / "fx")
    assert out.suffix == ".webm" and out.stat().st_size > 0
    png = tmp_path / "f.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(out), "-frames:v", "1", str(png)], check=True)
    a = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
    assert a.shape[2] == 4
    assert a[10, 10, 3] < 30            # green corner -> transparent
    assert a[145, 80, 3] > 220          # grey box -> solid
    assert matte.chroma_key(src, tmp_path / "fx")[0] == out    # cached
