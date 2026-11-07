"""Cost/time ledger: rows are complete, estimates come from measured rows only, nothing leaks, nothing raises."""
import json

from scripts import costs


def _row(job="j1", total=60.0, media=60.0, machine="github-ubuntu-2core", gem=None):
    stages = {"frames": total * 0.5, "transcribe": total * 0.5}
    if gem:
        costs.add("gemini", **gem)
    return costs.build_row(job, "analysis", media={"duration_s": media, "width": 1080, "height": 1920},
                           stages=stages, extra={"machine": {"name": machine, "cpus": 2, "kaggle_gpu": False}})


def test_row_has_time_machine_and_all_plan_prices():
    costs.usage(reset=True)
    r = _row(gem={"calls": 3, "in_tok": 3000, "out_tok": 600, "model": "gemini-flash-latest"})
    assert r["total_s"] == 60.0 and r["stages"]["frames"] == 30.0
    eq = r["usd_equivalent"]
    for k in ("github_actions_free_gross", "gcp_t4_on_demand", "gcp_t4_spot", "kaggle_free", "colab_pro", "gemini"):
        assert k in eq
    assert eq["github_actions_free_gross"] == 0.006          # 1 whole minute x $0.006
    assert eq["gcp_t4_on_demand"] == round(60 / 3600 * 0.866, 4)
    assert eq["gemini"] == round((3000 * 0.75 + 600 * 3.75) / 1e6, 6)   # flash-latest priced as 3.8-flash
    assert r["usage"]["gemini"]["calls"] == 3
    assert costs.usage() == {}                              # build_row resets the counters


def test_actions_minutes_round_up():
    costs.usage(reset=True)
    assert _row(total=61.0)["usd_equivalent"]["github_actions_free_gross"] == 0.012


def test_estimate_scales_by_media_length_and_says_when_no_data():
    assert costs.estimate([], 60)["ok"] is False
    rows = [_row("a", total=60, media=60), _row("b", total=120, media=120)]
    e = costs.estimate(rows, 30)
    assert e["ok"] and e["total_s"] == 30.0 and e["rows_used"] == 2


def test_record_local_fallback_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(costs, "LOCAL", tmp_path)
    p = costs.record(None, "job9", "analysis", media={"duration_s": 10}, stages={"frames": 5})
    assert json.loads(open(p).read())["job"] == "job9"

    class Boom:
        def ensure_dir(self, *_):
            raise OSError("drive down")
    p2 = costs.record(Boom(), "job10", "analysis", stages={"frames": 1})
    assert p2 and "job10" in p2                              # falls back to local file


def test_report_counts_month_minutes_and_kaggle_hours():
    r1 = _row("a", total=125.0)
    r2 = _row("b", total=3600.0)
    r2["machine"]["kaggle_gpu"] = True
    rep = costs.report([r1, r2])
    assert rep["github_actions"]["minutes_counted_this_month"] >= 3 and rep["kaggle_gpu_hours_used_total"] == 1.0


def test_pricing_file_has_source_and_date_everywhere():
    pr = costs.pricing()
    for k in ("github_actions", "kaggle", "colab", "gemini", "claude"):
        assert "source" in pr[k], k
    assert pr["checked"] and pr["usd_inr"]["value"] > 0


def test_resources_rtf_queue_and_report_fields():
    m = costs.mark()
    sum(i * i for i in range(200000))
    r = costs.resources_since(m)
    assert r["cpu_s"] >= 0 and 0 <= r["cpu_util_pct"] <= 400 and r["peak_rss_mb"] and r["wall_s"] >= 0
    assert costs.queue_s("2020-01-01T00:00:00Z") > 1000 and costs.queue_s("bad") is None
    row = _row("rtf", total=30.0, media=60.0)
    assert row["rtf"] == 0.5
    row["failed"] = True
    row["queue_s"] = 12.0
    row["resources"] = r
    rep = costs.report([row, _row("b", total=90.0, media=60.0)])["kinds"]["analysis"]
    assert rep["failed_rows"] == 1 and rep["median_queue_s"] == 12.0 and rep["p95_total_s"] == 90.0
    assert rep["usd_github_per_media_min"] is not None and rep["median_rtf"] == 1.0


def test_setup_info_reads_run_start_and_step_times(tmp_path, monkeypatch):
    import time
    now = time.time()
    monkeypatch.setattr(costs, "PROC_START", now)
    monkeypatch.setattr(costs, "ROOT", tmp_path)
    (tmp_path / "work").mkdir()
    (tmp_path / "work" / "setup_times.txt").write_text("system_tools 40\nvirus_scanner 75\nbad line\n")
    monkeypatch.setenv("ITCOD_RUN_STARTED", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 200)))
    info = costs.setup_info()
    assert 195 <= info["run_to_worker_s"] <= 205 and info["setup_steps_s"] == {"system_tools": 40, "virus_scanner": 75}
