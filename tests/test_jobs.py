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
from dna_fixtures import SCRIPT_METRICS, editing_dna, fit_editing, scripting_dna, sound_dna


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
    assert c1 == "creators/rahul/dna/c__editing__v1.json"
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
    assert drive.exists("creators/rahul/videos/an1/pack/collage_01.jpg")
    assert drive.exists("creators/rahul/videos/an1/pack/metrics_summary.json")
    assert drive.exists("creators/rahul/videos/an1/test.mp4")
    for sub in ("videos", "dna", "style", "ideas", "scripts", "made"):  # creator folders exist from the start
        assert (drive.root / "creators/rahul" / sub).is_dir()
    # no approval -> nothing moves, however often the worker runs
    for _ in range(3):
        assert w.process_once() == [("an1", "AWAIT_GATE2")]

    approve(drive, "an1", 2, 1, "Y")
    assert w.process_once() == [("an1", "AWAIT_CANDIDATE")]

    # a broken candidate is refused and a new version is requested (never overwritten)
    drive.put_json("creators/rahul/videos/an1/dna/candidate-editing-v1.json", {"type": "editing", "source": {"job_id": "an1"}})
    drive.put_json("creators/rahul/videos/an1/dna/candidate-scripting-v1.json", scripting_dna("an1"))
    drive.put_json("creators/rahul/videos/an1/dna/candidate-sound-v1.json", sound_dna("an1"))
    assert w.process_once() == [("an1", "AWAIT_CANDIDATE")]
    assert st()["candidate_ver"] == 2 and "cut_rhythm" in st()["validation_errors"]

    # the accuracy gate cross-checks numbers against the pack: a wrong measured number is refused
    pack_summary = "creators/rahul/videos/an1/pack/metrics_summary.json"
    summ = drive.read_json(pack_summary)
    summ["script_metrics"] = SCRIPT_METRICS          # the synthetic test video has no speech
    summ["audio"] = {"has_audio": True, "bpm": 103.4, "silence_share": 0.0,
                     "cut_beat_sync": {"share_within_80ms": 0.733, "cuts_checked": 15},
                     "ebu_r128": {"integrated_lufs": -16.2, "true_peak_dbtp": -1.5}}
    (drive.root / pack_summary).write_text(json.dumps(summ), encoding="utf-8")  # test edits the pack in place
    wrong = fit_editing(editing_dna("an1"), summ)
    wrong["cut_rhythm"]["cuts_per_min"] = 99.0
    drive.put_json("creators/rahul/videos/an1/dna/candidate-editing-v2.json", wrong)
    drive.put_json("creators/rahul/videos/an1/dna/candidate-scripting-v2.json", scripting_dna("an1"))
    drive.put_json("creators/rahul/videos/an1/dna/candidate-sound-v2.json", sound_dna("an1"))
    assert w.process_once() == [("an1", "AWAIT_CANDIDATE")]
    assert st()["candidate_ver"] == 3 and "cuts_per_min" in st()["validation_errors"]
    st_ver = [3]

    def good(ver):
        drive.put_json(f"creators/rahul/videos/an1/dna/candidate-editing-v{ver}.json", fit_editing(editing_dna("an1"), summ))
        drive.put_json(f"creators/rahul/videos/an1/dna/candidate-scripting-v{ver}.json", scripting_dna("an1"))
        drive.put_json(f"creators/rahul/videos/an1/dna/candidate-sound-v{ver}.json", sound_dna("an1"))

    good(3)
    r = w.process_once()
    assert r == [("an1", "AWAIT_GATE3")], st().get("validation_errors")

    # rejection asks for v3 and needs a new approval file (rev 3), not the old one
    approve(drive, "an1", 3, 3, "N", "palette too dull")
    assert w.process_once() == [("an1", "AWAIT_CANDIDATE")]
    assert st()["candidate_ver"] == 4
    good(4)
    assert w.process_once() == [("an1", "AWAIT_GATE3")]
    approve(drive, "an1", 3, 4, "Y")
    w.process_once()
    assert st()["status"] == "DONE"
    for t in ("editing", "scripting", "sound"):
        assert drive.exists(f"creators/rahul/dna/an1__{t}__v1.json")
    saved = drive.read_json("creators/rahul/dna/an1__editing__v1.json")
    assert saved["_meta"]["source_job"] == "an1" and saved["_meta"]["scope"] == "creator:rahul"
    # all earlier candidate versions are still there
    assert drive.exists("creators/rahul/videos/an1/dna/candidate-editing-v1.json")
    assert drive.exists("creators/rahul/videos/an1/dna/candidate-editing-v2.json")


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
    st3 = {"paths": {}}  # handle unreadable: not a failure, the reel goes to creators/_unassigned
    w._resolve_creator({"target": "creator:auto"}, st3, wd)
    assert st3["target"] == "creator:_unassigned" and "_unassigned" in st3["note_creator"]
    assert validate("job", {"id": "abc", "type": "analyze", "link": "http://x", "mode": "both",
                            "target": "creator:_unassigned", "gate1_approved_by_user": True, "reel_id": "AbCdEf123"}) == []
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
    # backoff: 3rd try waits 8 min, so a failure 5 min ago is not retried; one 9 min ago is
    from datetime import datetime, timedelta, timezone
    def ago(m):
        return (datetime.now(timezone.utc) - timedelta(minutes=m)).strftime("%Y-%m-%dT%H:%M:%SZ")
    st3 = {"review": {"status": "failed", "tries": 3, "tried": ago(5)}}
    Worker._retry_review(Fake(), st3, {"id": "job-q-003"}, wd)
    assert calls == ["job-q-001"]
    st4 = {"review": {"status": "failed", "tries": 3, "tried": ago(9)}}
    Worker._retry_review(Fake(), st4, {"id": "job-q-004"}, wd)
    assert calls == ["job-q-001", "job-q-004"] and st4["review"]["status"] == "ok"
    # no give-up after many tries (30 min cap)
    st5 = {"review": {"status": "failed", "tries": 50, "tried": ago(31)}}
    Worker._retry_review(Fake(), st5, {"id": "job-q-005"}, wd)
    assert calls[-1] == "job-q-005"
    # ok state is left alone
    n = len(calls)
    Worker._retry_review(Fake(), {"review": {"status": "ok"}}, {"id": "x"}, wd)
    assert len(calls) == n


def test_self_update_rolls_back_broken_code(tmp_path, monkeypatch):
    """A bad push must never kill the worker: new code that cannot import is rolled back and an alert is written."""
    import subprocess
    from scripts import common

    def git(*a, cwd):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=cwd, check=True,
                       capture_output=True)

    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    seed = tmp_path / "seed"
    seed.mkdir()
    shutil.copytree(ROOT / "scripts", seed / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "config", seed / "config")
    shutil.copytree(ROOT / "schemas", seed / "schemas")
    shutil.copyfile(ROOT / "run", seed / "run")
    git("init", "-q", "-b", "main", cwd=seed)
    git("add", "-A", cwd=seed)
    git("commit", "-q", "-m", "good", cwd=seed)
    git("remote", "add", "origin", str(bare), cwd=seed)
    git("push", "-q", "origin", "main", cwd=seed)
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(bare), str(clone)], check=True)
    good = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    (seed / "scripts" / "review.py").write_text("this is not python (\n")
    git("add", "-A", cwd=seed)
    git("commit", "-q", "-m", "bad", cwd=seed)
    git("push", "-q", "origin", "main", cwd=seed)

    drive_root = tmp_path / "drive"
    w = Worker(Storage(root=drive_root), work=tmp_path / "work")
    monkeypatch.setattr(common, "ROOT", clone)
    w._self_update()  # must not restart (os.execv) and must roll back
    now = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert now == good
    alert = json.loads((drive_root / "jobs/state/_worker_alert.json").read_text())
    assert alert["status"] == "ALERT" and "rolled back" in alert["note"]


def test_finished_jobs_are_not_reread(drive, tmp_path):
    drive.put_json("jobs/inbox/bad2.json", {"id": "bad2", "type": "analyze", "link": "http://x", "mode": "both",
                                           "target": "general"})
    w = Worker(drive, work=tmp_path / "work")
    assert w.process_once() == [("bad2", "NEEDS_INPUT")]
    assert w.process_once() == []  # terminal job skipped without reading inbox/state again


def test_sheet_creator_row_and_folder_column():
    from scripts.sheets import SheetsClient

    class WS:
        def __init__(self):
            self.rows = [["Creator", "Videos analyzed", "Last job", "Notes"]]

        def col_values(self, c):
            return [r[c - 1] for r in self.rows]

        def append_row(self, row, value_input_option=None):
            self.rows.append(list(row))

        def cell(self, r, c):
            class C:
                value = str(self.rows[r - 1][c - 1])
            return C

        def update(self, range_name, values):
            r = int(re.search(r"A(\d+)", range_name).group(1))
            self.rows[r - 1] = list(values[0])

    ws = WS()
    sc = SheetsClient.__new__(SheetsClient)
    sc.enabled = True
    sc._ws = lambda name: ws
    sc.upsert_creator("sahilverma.ai", "job-1")
    sc.upsert_creator("sahilverma.ai", "job-2")
    assert ws.rows[1] == ["sahilverma.ai", 2, "job-2", "creators/sahilverma.ai"]
    jobs = WS()
    jobs.rows = [["ID"]]
    sc._ws = lambda name: jobs
    sc.upsert_job({"id": "j", "status": "DONE", "target": "creator:x", "paths": {"analysis": "creators/x/videos/j"}},
                  {"link": "l", "mode": "both", "target": "creator:auto"})
    assert jobs.rows[1][3] == "creators/x/videos/j"


def test_worker_follows_a_job_folder_moved_into_creator_folder(drive, tmp_path):
    w = Worker(drive, work=tmp_path / "work")
    (drive.root / "creators/rahul/videos/an9/pack").mkdir(parents=True)
    st = {"paths": {"analysis": "analysis/an9", "pack": "analysis/an9/pack"}, "target": "creator:rahul"}
    job = {"id": "an9", "target": "creator:auto"}
    assert w._analysis_rel(st, job) == "creators/rahul/videos/an9"
    assert st["paths"]["pack"] == "creators/rahul/videos/an9/pack"
    st2 = {"paths": {"analysis": "analysis/an8"}, "target": "creator:rahul"}  # nothing moved: unchanged
    assert w._analysis_rel(st2, {"id": "an8"}) == "analysis/an8"


def test_bulk_jobs_are_measured_only_outside_the_cap_and_build_a_corpus(drive, test_video, tmp_path):
    import shutil
    ref = "input/references/b.mp4"
    (drive.root / "input/references").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(test_video, drive.root / ref)
    for i in (1, 2):
        drive.put_json(f"jobs/inbox/bt-{i:03d}.json", {"id": f"bt-{i:03d}", "type": "analyze", "file": ref, "mode": "video",
                                                       "target": "creator:zed", "gate1_approved_by_user": True,
                                                       "bulk": True, "batch": "bt1", "batch_size": 2})
    w = Worker(drive, work=tmp_path / "work")
    res = w.process_once()
    assert res == [("bt-001", "MEASURED"), ("bt-002", "MEASURED")], drive.read_json("jobs/state/bt-001.json").get("note")
    assert drive.exists("creators/zed/videos/bt-001/dna/measured-editing.json")
    assert not (drive.root / "creators/zed/dna/bt-001__editing__v1.json").exists()      # nothing saved without gates
    assert drive.exists("creators/zed/style/_batches/bt1/corpus-editing-measured.json")
    c = drive.read_json("creators/zed/style/_batches/bt1/corpus-editing-measured.json")
    assert c["n_videos"] == 2 and c["provisional"] is True and "cut_rhythm.cuts_per_min" in c["signature"]
    assert w._started_today(bulk=False) == 0 and w._started_today(bulk=True) == 2


def test_pick_source_ignores_single_stream_leftovers(tmp_path):
    from scripts.jobs import pick_source
    for n, size in (("source.fdash-3688a.m4a", 10), ("source.fdash-3688b.mp4", 50), ("source.mp4", 60), ("source.info.json", 1)):
        (tmp_path / n).write_bytes(b"x" * size)
    assert pick_source(list(tmp_path.glob("source.*"))).name == "source.mp4"
    (tmp_path / "source.mp4").unlink()
    with pytest.raises(RuntimeError, match="no merged video"):
        pick_source(list(tmp_path.glob("source.*")))


def test_merge_streams_joins_leftover_video_and_audio(tmp_path, test_video):
    import subprocess
    from scripts.jobs import merge_streams, pick_source
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(test_video), "-an", "-c", "copy",
                    str(tmp_path / "source.fdash-1v.mp4")], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(test_video), "-vn", "-c", "copy",
                    str(tmp_path / "source.fdash-2a.m4a")], check=True)
    out = merge_streams(tmp_path)
    assert out and out.name == "source.mp4"
    assert pick_source(list(tmp_path.glob("source.*"))).name == "source.mp4"
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True).stdout
    assert "video" in probe and "audio" in probe
    assert merge_streams(tmp_path) is None   # already merged -> untouched


def test_creator_index_lists_reel_to_dna(drive):
    from scripts.creator_index import write_index
    drive.put_json("creators/rahul/videos/an1/reel.json",
                   {"job": "an1", "link": "http://x/1", "mode": "audio", "saved": "2026-11-06T10:00:00Z",
                    "dna": ["creators/rahul/dna/an1__scripting__v1.json"]})
    drive.put_json("creators/rahul/videos/an2/notfinished.json", {})
    assert write_index(drive, "rahul") == 1
    assert write_index(drive, "rahul") == 1  # refresh in place, no INDEX_v2
    md = drive.read_text("creators/rahul/INDEX.md")
    assert "an1__scripting__v1.json" in md and "http://x/1" in md
    assert not drive.exists("creators/rahul/INDEX_v2.md")


def test_recipe_card_links_reel_dna_and_elements(drive):
    from scripts.recipe import write
    drive.put_json("creators/rahul/videos/an1/elements.json",
                   {"fonts": [{"name": "Courier Prime Bold", "role": "title"}], "music": {"bpm": 103.4, "usable_audio": False},
                    "junk": 1})
    reel = {"creator": "rahul", "job": "an1", "link": "http://x/1", "mode": "audio", "saved": "t",
            "analysis": "creators/rahul/videos/an1",
            "dna": ["creators/rahul/dna/an1__scripting__v1.json", "creators/rahul/dna/an1__sound__v1.json"]}
    card = write(drive, reel)
    assert card["dna"]["scripting"].endswith("an1__scripting__v1.json") and "junk" not in card["elements"]
    write(drive, reel)  # refresh in place, no _v2
    assert not drive.exists("creators/rahul/videos/an1/recipe_v2.json")
    assert "Courier Prime Bold" in drive.read_text("creators/rahul/videos/an1/RECIPE.md")
    write(drive, {**reel, "job": "an2", "analysis": "creators/rahul/videos/an2"})  # no elements.json: still a card
    assert drive.exists("creators/rahul/videos/an2/recipe.json")


def test_analyzing_job_resumes_on_a_fresh_machine(drive, tmp_path, test_video, monkeypatch):
    """A new Actions run / new VM has no copy of the downloaded video: it is pulled back from our Drive copy.
    Regression: job reel-DfMQ7zqkuxO-b was cut off mid-analysis and would have burned its last attempt on 'file not found'."""
    from scripts import pack
    ref = "input/references/test.mp4"
    (drive.root / "input/references").mkdir(parents=True)
    shutil.copyfile(test_video, drive.root / ref)
    drive.put_json("jobs/inbox/rs1.json", {"id": "rs1", "type": "analyze", "file": ref, "mode": "both",
                                          "target": "creator:rahul", "gate1_approved_by_user": True})
    real = pack.run_pipeline

    def cut_off(*a, **k):
        raise RuntimeError("this run ended here")

    monkeypatch.setattr(pack, "run_pipeline", cut_off)
    assert Worker(drive, work=tmp_path / "work1").process_once() == [("rs1", "ANALYZING")]
    st = drive.read_json("jobs/state/rs1.json")
    assert st["attempts"]["analysis"] == 1 and st["paths"]["source_drive"]
    shutil.rmtree(tmp_path / "work1")                      # the old machine is gone
    monkeypatch.setattr(pack, "run_pipeline", real)
    assert Worker(drive, work=tmp_path / "work2").process_once() == [("rs1", "AWAIT_GATE2")]
    assert (tmp_path / "work2" / "rs1" / "source.mp4").is_file()


def test_pack_summary_recomputes_script_numbers_from_saved_transcript(drive):
    w = Worker(drive)
    st = {"paths": {"analysis": "analysis/x"}}
    job = {"id": "j"}
    drive.put_json("analysis/x/pack/metrics_summary.json",
                   {"video": {"duration_s": 10.0}, "script_metrics": {"available": True, "words_per_min_speaking": 5}})
    eng = [{"start": 0.0, "end": 5.0, "text": "one two three four five six seven eight nine ten"},
           {"start": 5.5, "end": 9.5, "text": "and then eleven twelve thirteen fourteen fifteen"}]
    drive.put_json("analysis/x/transcript.json", {"available": True, "segments": [{"start": 0, "end": 1, "text": "ek"}],
                   "coverage_ratio": 0.4, "loop_words_removed": 30,
                   "alt_english": {"segments": eng, "coverage_ratio": 1.0, "text": "x"}})
    m = w._pack_summary(st, job)["script_metrics"]
    assert m["pass_used"] == "english" and m["words"] == 17
