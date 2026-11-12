"""rulebooks/23-protocol.md enforced by the worker: no protocol block / no look / no sample = no render."""
import copy
import json

import cv2
import pytest
import numpy as np

from scripts import protocol
from scripts.common import ROOT
from scripts.jobs import Worker
from test_jobs import _moving_video, approve, fake_render, look, stamped  # noqa: F401

_PLAN = json.loads((ROOT / "templates" / "test-plan.json").read_text())


@pytest.fixture()
def plan():
    return copy.deepcopy(_PLAN)



def test_plan_without_protocol_block_is_rejected(plan, drive):
    assert any("no protocol block" in e for e in protocol.check_plan(plan, drive))


def test_wrong_digest_is_rejected(plan, drive):
    p = stamped(plan, kind="sample")
    p["protocol"]["digest"] = "000000000000"
    assert any("digest" in e for e in protocol.check_plan(p, drive))


def test_sample_must_be_short(plan, drive):
    p = copy.deepcopy(plan)
    p["scenes"][0]["duration_s"] = 30
    assert any("at most" in e for e in protocol.check_plan(stamped(p, kind="sample"), drive))


def test_full_needs_approved_sample(plan, drive):
    p = protocol.stamp(plan, "full", reference="none", reference_reason="unit test, no reference")
    assert any("sample_job" in e for e in protocol.check_plan(p, drive))
    p = protocol.stamp(plan, "full", reference="none", reference_reason="unit test, no reference", sample_job="nope")
    assert any("not approved" in e for e in protocol.check_plan(p, drive))
    assert protocol.check_plan(stamped(plan, drive), drive) == []


def test_full_with_effect_missing_from_sample_is_rejected(plan, drive):
    p = stamped(plan, drive)
    p["scenes"][0] = {"template": "video", "duration_s": 2, "props": {"src": "x.mp4", "chroma_key": True}}
    assert any("effects not tested" in e or "sources not in" in e for e in protocol.check_plan(p, drive))


def test_reference_needs_complete_record_or_reason(plan, drive):
    p = protocol.stamp(plan, "sample", reference="none")
    assert any("reference_reason" in e for e in protocol.check_plan(p, drive))
    drive.put_json("creators/a/style_record.json", {"complete": False, "problems": ["no events"]})
    p = protocol.stamp(plan, "sample", reference="creators/a/style_record.json")
    assert any("incomplete" in e for e in protocol.check_plan(p, drive))
    drive.put_json("creators/b/style_record.json", {"complete": True})
    assert protocol.check_plan(protocol.stamp(plan, "sample", reference="creators/b/style_record.json"), drive) == []


def test_frame_check_catches_green_and_frozen(tmp_path):
    g = tmp_path / "green.mp4"
    w = cv2.VideoWriter(str(g), cv2.VideoWriter_fourcc(*"mp4v"), 10, (108, 192))
    for i in range(30):
        fr = np.zeros((192, 108, 3), np.uint8)
        fr[:] = (40, 230, 40)
        cv2.circle(fr, (20 + i, 90), 10, (255, 255, 255), -1)
        w.write(fr)
    w.release()
    r = protocol.frame_check(g, tmp_path / "o1")
    assert not r["ok"] and any("green" in p for p in r["problems"])
    ok = protocol.frame_check(_mk(tmp_path / "ok.mp4"), tmp_path / "o2")
    assert ok["ok"] and (tmp_path / "o2" / "collage_frames.jpg").exists()


def _mk(path):
    _moving_video(path)
    return path


def test_look_with_wrong_sha_does_not_pass(plan, drive, tmp_path, fake_render):  # noqa: F811
    drive.put_json("jobs/inbox/lk1.json", {"id": "lk1", "type": "render"})
    w = Worker(drive, work=tmp_path / "work")
    w.process_once()
    drive.put_json("jobs/plans/lk1-v1.json", stamped(plan, drive))
    w.process_once()
    approve(drive, "lk1", 4, 1, "Y")
    w.process_once()
    st = drive.read_json("jobs/state/lk1.json")
    assert st["status"] == "AWAIT_LOOK"
    name, body = protocol.look_marker("lk1", st["look_rev"], "badbadbadbad", "guess")
    drive.put_json(f"jobs/approvals/{name}", body)
    w.process_once()
    assert drive.read_json("jobs/state/lk1.json")["status"] == "AWAIT_LOOK"   # wrong sha = did not look at THIS collage


def test_sample_plan_ends_at_sample_ok(plan, drive, tmp_path, fake_render):  # noqa: F811
    drive.put_json("jobs/inbox/sm1.json", {"id": "sm1", "type": "render"})
    w = Worker(drive, work=tmp_path / "work")
    w.process_once()
    drive.put_json("jobs/plans/sm1-v1.json", stamped(plan, kind="sample"))
    w.process_once()
    approve(drive, "sm1", 4, 1, "Y")
    w.process_once()
    look(drive, w, "sm1", "AWAIT_GATE5")
    approve(drive, "sm1", 5, 1, "Y")
    w.process_once()
    st = drive.read_json("jobs/state/sm1.json")
    assert st["status"] == "SAMPLE_OK" and st["sample_ok"] and fake_render == ["preview"]


def test_protocol_file_is_in_the_worker_repo():
    """The worker checkout has no rulebooks/ (private repo). The protocol it checks must be a tracked file."""
    import subprocess
    assert protocol.PROTOCOL_FILE.exists()
    ignored = subprocess.run(["git", "check-ignore", "-q", str(protocol.PROTOCOL_FILE)], cwd=ROOT).returncode == 0
    assert not ignored, "config/protocol.md is git-ignored: the worker would not have it"
    rb = ROOT / "rulebooks" / "23-protocol.md"
    if rb.exists():   # the brain copy Claude reads must say the same
        assert rb.read_text().strip() == protocol.PROTOCOL_FILE.read_text().strip()


def test_grade_off_needs_what_faiz_said(plan, drive):
    plan["grade"] = {"mode": "off"}
    p = stamped(plan, kind="sample")
    assert any("grade.mode is 'off'" in e for e in protocol.check_plan(p, drive))
    p = protocol.stamp(plan, "sample", reference="none", reference_reason="unit test, no reference", grade_off_reason="Faiz: no grading on this one")
    assert protocol.check_plan(p, drive) == []


def test_full_plan_may_skip_the_sample_only_with_faiz_words():
    from scripts import protocol as P
    plan = {"scenes": [{"id": "s", "duration_s": 30, "template": "title", "props": {"text": "x"}}]}

    class S:
        def read_json(self, rel):
            return {}
    p = P.stamp(plan, "full", "creators/x/style_record.json")
    assert any("sample_job" in e for e in P.check_plan(p, S()))
    p = P.stamp(plan, "full", "creators/x/style_record.json", sample_skip="Faiz 21:31: Y, skip the 8 s sample")
    assert not any("sample_job" in e for e in P.check_plan(p, S()))
