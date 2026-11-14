"""Rule run_must_show_truth: a workflow step that pipes a job into tail/head must use pipefail, else a failed job shows a green tick."""
import re
from pathlib import Path

WF = Path(__file__).resolve().parent.parent / ".github" / "workflows"


def test_piped_run_steps_use_pipefail():
    bad = []
    for f in sorted(WF.glob("*.yml")):
        txt = f.read_text(encoding="utf-8")
        for m in re.finditer(r"\./run [^\n|]*\|\s*(tail|head)", txt):
            if "pipefail" not in txt and "shell: bash" not in txt:
                bad.append(f.name)
    assert not bad, f"pipe to tail/head without pipefail in {sorted(set(bad))}"
