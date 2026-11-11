"""The GitHub worker runs Python 3.11: every script must compile there (a 3.12-only f-string broke the key and gave a black video)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not shutil.which("python3.11"), reason="python3.11 missing")
def test_all_scripts_compile_on_python_311():
    files = [str(p) for p in sorted((ROOT / "scripts").glob("*.py"))]
    r = subprocess.run(["python3.11", "-m", "py_compile", *files], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
