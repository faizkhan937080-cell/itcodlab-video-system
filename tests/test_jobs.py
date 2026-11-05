"""Storage rules, approval gates and the job state machine (Drive is a local folder here)."""
import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from scripts import render as render_mod
from scripts.common import ROOT
from scripts.dna import save_dna, validate
from scripts.jobs import Worker
from scripts.storage import Storage, StorageError


# ---------------------------------------------------------------- storage rules
def test_storage_never_overwrites(drive):
    drive.put_text("dna/x/dna-v1.json", "one")
    second = drive.put_text("dna/x/dna-v1.json", "two")
    assert second == "dna/x/dna-v1_v2.json"
    assert drive.read_text("dna/x/dna-v1.json") == "one"


def test_in_place_update_only_for_state(drive):
    with pytest.raises(StorageError):
        drive.put_text("analysis/a.json", "x", versioned=False)
    drive.write_state("jobs/state/a.json", {"a": 1})
    drive.write_state("jobs/state/a.json", {"a": 2})
    assert drive.read_json("jobs/state/a.json") == {"a": 2}


def test_code_has_no_delete_calls():
    banned = re.compile(r"os\.remove|os\.unlink|\.unlink\(|rmtree|os\.rmdir|rclone\s+sync|rclone\s+delete|rclone\s+purge")
    for p in (ROOT / "scripts").glob("*.py"):
        assert not banned.search(p.read_text()), f"delete call in {p.name}"


# ---------------------------------------------------------------- schemas
def editing_dna(job_id):
    return {"type": "editing", "source": {"job_id": job_id},
            "cut_rhythm": {"avg_shot_s": 1.8, "median_shot_s": 1.5, "cuts_per_min": 30, "pattern": "fast, even"},
            "transitions": [{"type": "hard_cut", "share": 0.8}, {"type": "dissolve", "share": 0.2}],
            "motion": {"camera": "slow push-in", "elements": "pop-in text"},
            "text": {"present": True, "style": "bold sans"},
            "color": {"palette": ["#0A192F", "#FF5A5F"], "grade": "high contrast"},
            "layout": {"orientation": "portrait"},
            "confidence": {"cut_rhythm": "measured", "motion": "estimated"}}


def scripting_dna(job_id):
    return {"type": "scripting", "source": {"job_id": job_id},
            "hook": {"kind": "question", "duration_s": 2.5},
            "structure": [{"beat": "hook", "purpose": "stop the scroll"}, {"beat": "cta", "purpose": "ask"}],
            "pacing": {"words_per_min": 150}, "tone": "friendly", "language": "hinglish",
            "cta": {"style": "soft"}, "confidence": {"hook": "estimated"}}


def sound_dna(job_id):
    return {"type": "sound", "source": {"job_id": job_id}, "bpm": 120,
            "beat_sync": {"share_within_80ms": 0.6}, "loudness_db": {"mean": -18},
            "confidence": {"bpm": "measured"}}


def test_schemas_accept_valid_and_reject_invalid():
    assert validate("editing", editing_dna("j1")) == []
    assert validate("scripting", scripting_dna("j1")) == []
    assert validate("sound", sound_dna("j1")) == []
    bad = editing_dna("j1")
    del bad["cut_rhythm"]
    bad["color"]["palette"] = ["red"]
    errs = validate("editing", bad)
    assert any("cut_rhythm" in e for e in errs) and any("palette" in e for e in errs)


def test_scene_plan_schema():
    plan = json.loads((ROOT / "templates" / "test-plan.json").read_text())
    assert validate("scene", plan) == []
    plan["scenes"][0]["template"] = "unknown"
    assert validate("scene", plan)


def test_dna_versions_are_added_not_overwritten(drive):
    p1, v1 = save_dna(drive, "general", "editing", editing_dna("a"), "a")
    p2, v2 = save_dna(drive, "general", "editing", editing_dna("b"), "b")
    c1, _ = save_dna(drive, "creator:rahul", "editing", editing_dna("c"), "c")
    assert (v1, v2) == (1, 2)
    assert p1 == "dna/general/editing/dna-v1.json" and p2 == "dna/general/editing/dna-v2.json"
    assert c1 == "dna/creators/rahul/editing/dna-v1.json"
    assert drive.exists(p1) and drive.exists(p2)


# ---------------------------------------------------------------- analyze job + gates
def approve(drive, job, gate, rev, decision, feedback=""):
    drive.put_json(f"jobs/approvals/{job}__gate{gate}__r{rev}.json",
                   {"job": job, "gate": gate, "rev": rev, "decision": decision, "feedback": feedback})


def test_invalid_job_needs_input(drive, tmp_path):
    drive.put_json("jobs/inbox/bad1.json", {"id": "bad1", "type": "analyze", "link": "http://x", "mode": "both",
                                           "target": "general"})  # gate1 flag missing
    w = Worker(drive, work=tmp_path / "work")
    assert w.process_once() == [("bad1", "NEEDS_INPUT")]


def test_analyze_job_stops_at_every_gate(drive, tmp_path, test_video):
    ref = "input/references/test.mp4"
    (drive.root / "input/references").mkdir(parents=True)
    shutil.copyfile(test_video, drive.root / ref)
    drive.put_json("jobs/inbox/an1.json", {"id": "an1", "type": "analyze", "file": ref, "mode": "both",
                                          "target": "creator:rahul", "gate1_approved_by_user": True})
    w = Worker(drive, work=tmp_path / "work")
    st = lambda: drive.read_json("jobs/state/an1.json")  # noqa: E731

    assert w.process_once() == [("an1", "AWAIT_GATE2")]
    assert drive.exists("analysis/an1/pack/collage_01.jpg")
    assert drive.exists("analysis/an1/pack/metrics_summary.json")
    assert drive.exists("analysis/an1/test.mp4")
    # no approval -> nothing moves, however often the worker runs
    for _ in range(3):
        assert w.process_once() == [("an1", "AWAIT_GATE2")]

    approve(drive, "an1", 2, 1, "Y")
    assert w.process_once() == [("an1", "AWAIT_CANDIDATE")]

    # a broken candidate is refused and a new version is requested (never overwritten)
    drive.put_json("analysis/an1/dna/candidate-editing-v1.json", {"type": "editing", "source": {"job_id": "an1"}})
    drive.put_json("analysis/an1/dna/candidate-scripting-v1.json", scripting_dna("an1"))
    drive.put_json("analysis/an1/dna/candidate-sound-v1.json", sound_dna("an1"))
    assert w.process_once() == [("an1", "AWAIT_CANDIDATE")]
    assert st()["candidate_ver"] == 2 and "cut_rhythm" in st()["validation_errors"]

    for t, fn in (("editing", editing_dna), ("scripting", scripting_dna), ("sound", sound_dna)):
        drive.put_json(f"analysis/an1/dna/candidate-{t}-v2.json", fn("an1"))
    assert w.process_once() == [("an1", "AWAIT_GATE3")]

    # rejection asks for v3 and needs a new approval file (rev 3), not the old one
    approve(drive, "an1", 3, 2, "N", "palette too dull")
    assert w.process_once() == [("an1", "AWAIT_CANDIDATE")]
    assert st()["candidate_ver"] == 3
    for t, fn in (("editing", editing_dna), ("scripting", scripting_dna), ("sound", sound_dna)):
        drive.put_json(f"analysis/an1/dna/candidate-{t}-v3.json", fn("an1"))
    assert w.process_once() == [("an1", "AWAIT_GATE3")]
    approve(drive, "an1", 3, 3, "Y")
    w.process_once()
    assert st()["status"] == "DONE"
    for t in ("editing", "scripting", "sound"):
        assert drive.exists(f"dna/creators/rahul/{t}/dna-v1.json")
    saved = drive.read_json("dna/creators/rahul/editing/dna-v1.json")
    assert saved["_meta"]["source_job"] == "an1" and saved["_meta"]["scope"] == "creator:rahul"
    # all earlier candidate versions are still there
    assert drive.exists("analysis/an1/dna/candidate-editing-v1.json")
    assert drive.exists("analysis/an1/dna/candidate-editing-v2.json")


def test_gate2_rejection_stops_the_job(drive, tmp_path, test_video):
    ref = "input/references/test.mp4"
    (drive.root / "input/references").mkdir(parents=True)
    shutil.copyfile(test_video, drive.root / ref)
    drive.put_json("jobs/inbox/an2.json", {"id": "an2", "type": "analyze", "file": ref, "mode": "video",
                                          "target": "general", "gate1_approved_by_user": True})
    w = Worker(drive, work=tmp_path / "work")
    assert w.process_once() == [("an2", "AWAIT_GATE2")]
    approve(drive, "an2", 2, 1, "N", "wrong video")
    assert w.process_once() == [("an2", "NEEDS_INPUT")]
    assert w.process_once() == []  # terminal: skipped


# ---------------------------------------------------------------- render job + gates
@pytest.fixture()
def fake_render(monkeypatch):
    calls = []

    def fake(plan, quality, out_path, storage=None, concurrency=None):
        calls.append(quality)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(b"fake-mp4-" + quality.encode())
        return {"ok": True, "problems": [], "probe": {"width": 1, "height": 1, "duration_s": 5.0}}

    monkeypatch.setattr(render_mod, "render_plan", fake)
    return calls


def test_render_job_gates_and_rejection(drive, tmp_path, fake_render):
    plan = json.loads((ROOT / "templates" / "test-plan.json").read_text())
    drive.put_json("jobs/inbox/rn1.json", {"id": "rn1", "type": "render"})
    w = Worker(drive, work=tmp_path / "work")
    st = lambda: drive.read_json("jobs/state/rn1.json")  # noqa: E731

    assert w.process_once() == [("rn1", "AWAIT_PLAN")]
    drive.put_json("jobs/plans/rn1-v1.json", plan)
    assert w.process_once() == [("rn1", "AWAIT_GATE4")]
    assert fake_render == []  # nothing rendered before gate 4

    approve(drive, "rn1", 4, 1, "Y")
    assert w.process_once() == [("rn1", "AWAIT_GATE5")]
    assert fake_render == ["preview"]
    assert drive.exists("output/previews/rn1_preview_v1.mp4")

    approve(drive, "rn1", 5, 1, "N", "text too small")  # rejected preview -> new plan needed
    assert w.process_once() == [("rn1", "AWAIT_PLAN")]
    assert st()["plan_ver"] == 2
    plan2 = copy.deepcopy(plan)
    plan2["title"] = "v2"
    drive.put_json("jobs/plans/rn1-v2.json", plan2)
    assert w.process_once() == [("rn1", "AWAIT_GATE4")]
    approve(drive, "rn1", 4, 2, "Y")
    assert w.process_once() == [("rn1", "AWAIT_GATE5")]
    approve(drive, "rn1", 5, 2, "Y")
    assert w.process_once() == [("rn1", "AWAIT_GATE6")]
    assert fake_render == ["preview", "preview", "final"]
    assert not drive.exists("output/final-4k/rn1_v2.mp4")  # not published before gate 6
    approve(drive, "rn1", 6, 2, "Y")
    w.process_once()
    assert st()["status"] == "DONE"
    assert drive.exists("output/final-4k/rn1_v2.mp4")
    assert drive.exists("output/previews/rn1_preview_v1.mp4")  # old preview still kept


def test_invalid_plan_requests_new_version(drive, tmp_path, fake_render):
    drive.put_json("jobs/inbox/rn2.json", {"id": "rn2", "type": "render"})
    w = Worker(drive, work=tmp_path / "work")
    w.process_once()
    drive.put_json("jobs/plans/rn2-v1.json", {"title": "x", "fps": 30, "orientation": "portrait", "scenes": []})
    assert w.process_once() == [("rn2", "AWAIT_PLAN")]
    s = drive.read_json("jobs/state/rn2.json")
    assert s["plan_ver"] == 2 and s["validation_errors"]


def test_render_failure_retries_then_fails(drive, tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("remotion exploded")

    monkeypatch.setattr(render_mod, "render_plan", boom)
    plan = json.loads((ROOT / "templates" / "test-plan.json").read_text())
    drive.put_json("jobs/inbox/rn3.json", {"id": "rn3", "type": "render"})
    drive.put_json("jobs/plans/rn3-v1.json", plan)
    w = Worker(drive, work=tmp_path / "work")
    w.process_once()
    approve(drive, "rn3", 4, 1, "Y")
    seen = [w.process_once()[0][1] for _ in range(3)]  # attempts 1, 2 retry; attempt 3 > max_retries
    assert seen == ["RENDERING_PREVIEW", "RENDERING_PREVIEW", "FAILED"]
    assert w.process_once() == []  # terminal: never retried again
    assert "remotion exploded" in drive.read_json("jobs/state/rn3.json")["error_tail"]


# ---------------------------------------------------------------- creator handle from link metadata
def test_creator_handle_is_read_from_metadata(drive, tmp_path):
    w = Worker(drive, work=tmp_path / "work")
    wd = tmp_path / "wd"
    wd.mkdir()
    (wd / "source.info.json").write_text(json.dumps(
        {"channel": "Some.Creator_01", "uploader_id": "12345", "uploader": "Some Creator", "title": "t"}))
    st = {"paths": {}}
    w._resolve_creator({"target": "creator:auto"}, st, wd)
    assert st["target"] == "creator:some.creator_01"
    st2 = {"paths": {}}
    w._resolve_creator({"target": "general"}, st2, wd)
    assert st2["target"] == "general"
    (wd / "source.info.json").write_text(json.dumps({"uploader_id": "999"}))
    with pytest.raises(RuntimeError):
        w._resolve_creator({"target": "creator:auto"}, {"paths": {}}, wd)
    assert validate("job", {"id": "abc", "type": "analyze", "link": "http://x", "mode": "both",
                            "target": "creator:auto", "gate1_approved_by_user": True}) == []


def test_review_retry_after_failed_push(tmp_path, monkeypatch):
    import json
    from scripts import review
    from scripts.jobs import Worker

    wd = tmp_path / "wd"
    (wd / "analysis" / "pack").mkdir(parents=True)
    (wd / "analysis" / "collage_index.json").write_text("{}")
    saved = []

    class Fake:
        def save(self, st, job):
            saved.append(json.loads(json.dumps(st)))

    calls = []
    monkeypatch.setattr(review, "publish", lambda p, j, i=None: calls.append(j) or {"status": "ok"})
    st = {"review": {"status": "failed", "error": "403", "tried": "2020-01-01T00:00:00Z"}}
    Worker._retry_review(Fake(), st, {"id": "job-q-001"}, wd)
    assert calls == ["job-q-001"] and st["review"]["status"] == "ok" and saved
    # fresh failure (tried just now) is not retried yet
    from scripts.common import now_iso
    st2 = {"review": {"status": "failed", "tried": now_iso()}}
    Worker._retry_review(Fake(), st2, {"id": "job-q-002"}, wd)
    assert calls == ["job-q-001"]
    # ok state is left alone
    Worker._retry_review(Fake(), {"review": {"status": "ok"}}, {"id": "x"}, wd)
    assert calls == ["job-q-001"]
