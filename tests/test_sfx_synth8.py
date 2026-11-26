import shutil
import pytest
from scripts import sfx, sfx_synth


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="no ffmpeg here")
def test_every_beat_kind_has_a_working_recipe(tmp_path):
    kinds = {k for _, k in sfx.BEAT_KINDS}
    for k in kinds:
        assert k in sfx_synth.RECIPES, k
        out = sfx_synth.make(k, tmp_path / f"{k}.wav")
        assert (tmp_path / f"{k}.wav").stat().st_size > 500
