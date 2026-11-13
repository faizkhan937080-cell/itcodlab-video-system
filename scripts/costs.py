"""Time + cost ledger. One small JSON row per job step (analysis / render), saved in Drive costs/jobs/.
Never raises, never blocks a job. Rates live in config/pricing.json (source + date on every block).
USD columns are EQUIVALENTS: what the same measured work would cost on each plan (basis says what was measured).
"""
import json
import math
import os
import statistics as st
import threading
import time

from .common import ROOT, CONFIG, load_json, log, now_iso, to_native

_USE, _LOCK = {}, threading.Lock()
PROC_START = time.time()
LOCAL = ROOT / "costs" / "local"


def add(kind, **nums):
    """Accumulate counters, e.g. add('gemini', calls=1, in_tok=900, out_tok=120, model='gemini-flash-latest')."""
    with _LOCK:
        d = _USE.setdefault(kind, {})
        for k, v in nums.items():
            if isinstance(v, (int, float)):
                d[k] = d.get(k, 0) + v
            else:
                d[k] = v


def usage(reset=False):
    with _LOCK:
        out = json.loads(json.dumps(_USE))
        if reset:
            _USE.clear()
    return out


def mark():
    """Start of a measured step: wall clock + CPU seconds so far (this process + children such as ffmpeg/node)."""
    t = os.times()
    return {"wall": time.time(), "cpu": t[0] + t[1] + t[2] + t[3]}


def resources_since(m):
    """CPU seconds, CPU utilisation and peak memory of the step (industry: utilisation shows if a bigger machine would help)."""
    t = os.times()
    wall = max(time.time() - m["wall"], 0.001)
    cpu = max(t[0] + t[1] + t[2] + t[3] - m["cpu"], 0.0)
    n = os.cpu_count() or 1
    peak = None
    try:
        import resource
        peak = round((resource.getrusage(resource.RUSAGE_SELF).ru_maxrss + resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 0)
    except Exception:  # noqa: BLE001
        pass
    return {"wall_s": round(wall, 1), "cpu_s": round(cpu, 1), "cpu_util_pct": round(100 * cpu / (wall * n), 1), "peak_rss_mb": peak,
            "worker_age_s": round(time.time() - PROC_START, 1)}


def setup_info():
    """Runner boot + installs before the worker started (GitHub: ITCOD_RUN_STARTED) and per-step seconds (work/setup_times.txt)."""
    out = {}
    try:
        started = os.environ.get("ITCOD_RUN_STARTED")
        if started:
            t = time.mktime(time.strptime(started, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
            out["run_to_worker_s"] = round(max(PROC_START - t, 0), 1)
        f = ROOT / "work" / "setup_times.txt"
        if f.exists():
            steps = {}
            for line in f.read_text(encoding="utf-8").splitlines():
                k, _, v = line.partition(" ")
                if v.strip().isdigit():
                    steps[k] = int(v)
            out["setup_steps_s"] = steps
    except Exception:  # noqa: BLE001
        pass
    return out


def queue_s(created_iso):
    """Seconds the job waited in the inbox before this step started (queue time)."""
    try:
        t = time.mktime(time.strptime(created_iso, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
        return round(max(time.time() - t, 0), 1)
    except Exception:  # noqa: BLE001
        return None


def _pct(vals, q):
    v = sorted(vals)
    return round(v[min(len(v) - 1, int(math.ceil(q * len(v))) - 1)], 1) if v else None


def pricing():
    return load_json(CONFIG / "pricing.json")


def machine():
    """Where this ran. ITCOD_MACHINE overrides; GitHub-hosted = free runner; self-hosted = our VM."""
    if os.environ.get("ITCOD_MACHINE"):
        name = os.environ["ITCOD_MACHINE"]
    elif os.environ.get("GITHUB_ACTIONS") == "true":
        name = "gcp-gpu-vm" if os.environ.get("RUNNER_ENVIRONMENT") == "self-hosted" else "github-ubuntu-2core"
    else:
        name = "local"
    return {"name": name, "cpus": os.cpu_count(), "kaggle_gpu": os.environ.get("ITCOD_KAGGLE_GPU") == "1"}


def _tok_usd(table, model, tin, tout):
    p = table.get(model)
    if not p:
        return None
    return round((tin * p["in"] + tout * p["out"]) / 1e6, 6)


def equivalents(row, pr=None):
    """Price the measured seconds + tokens on each plan. Never invents a speed: same seconds on every plan (basis says so)."""
    pr = pr or pricing()
    s, u = float(row.get("total_s", 0)), row.get("usage", {})
    g, c = u.get("gemini", {}), u.get("claude", {})
    gem_model = g.get("model") or "gemini-flash-latest"
    gem_key = pr["gemini"]["alias_priced_as"] if "latest" in gem_model else gem_model
    eq = {
        "github_actions_free_gross": round(math.ceil(s / 60) * pr["github_actions"]["linux_2core_usd_per_min"], 4),
        "gcp_t4_on_demand": round(s / 3600 * pr["gcp"]["t4_n1_8vcpu_30gb_asia_south1"]["on_demand_usd_hr"], 4),
        "gcp_t4_spot": round(s / 3600 * pr["gcp"]["t4_n1_8vcpu_30gb_asia_south1"]["spot_usd_hr"], 4),
        "kaggle_free": 0.0,
        "colab_pro": round(s / 3600 * pr["colab"]["t4_units_per_hour"] * pr["colab"]["pro_usd_month"] / pr["colab"]["pro_units"], 4),
        "gemini": _tok_usd(pr["gemini"]["usd_per_mtok"], gem_key, g.get("in_tok", 0), g.get("out_tok", 0)) if g else 0.0,
        "claude_api_equivalent": _tok_usd(pr["claude"]["usd_per_mtok"], c.get("model", ""), c.get("in_tok", 0), c.get("out_tok", 0)) if c else 0.0,
    }
    eq["inr_factor"] = pr["usd_inr"]["value"]
    return eq


def build_row(job_id, kind, media=None, stages=None, extra=None):
    stages = {k: round(float(v), 1) for k, v in (stages or {}).items()}
    row = {"job": job_id, "kind": kind, "at": now_iso(), "machine": machine(), "media": media or {},
           "stages": stages, "total_s": round(sum(stages.values()), 1), "usage": usage(reset=True),
           "basis": "seconds measured on machine.name; other plans priced with the SAME seconds until measured there"}
    if extra:
        row.update(extra)
    row.update(setup_info())
    d = (row["media"] or {}).get("duration_s") or 0
    if d:  # real-time factor: processing seconds per second of video (lower = faster; <1 = faster than real time)
        row["rtf"] = round(row["total_s"] / d, 3)
    try:
        row["usd_equivalent"] = equivalents(row)
    except Exception as e:  # noqa: BLE001
        row["usd_equivalent"] = {"error": type(e).__name__}
    return to_native(row)


def record(storage, job_id, kind, media=None, stages=None, extra=None):
    """Write one row. Drive first, local file as fallback. Returns the path or None. Never raises."""
    try:
        row = build_row(job_id, kind, media, stages, extra)
        name = f"{job_id}__{kind}__{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
        if storage is not None:
            try:
                storage.ensure_dir("costs/jobs")
                storage.put_json(f"costs/jobs/{name}", row, versioned=False)
                log(f"cost row saved: costs/jobs/{name} ({row['total_s']} s)")
                return f"costs/jobs/{name}"
            except Exception as e:  # noqa: BLE001
                log(f"cost row to Drive failed: {type(e).__name__}; keeping local")
        LOCAL.mkdir(parents=True, exist_ok=True)
        (LOCAL / name).write_text(json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8")
        return str(LOCAL / name)
    except Exception as e:  # noqa: BLE001
        log(f"cost row skipped: {type(e).__name__}")
        return None


def load_rows(storage=None):
    rows = []
    if storage is not None:
        try:
            for n in storage.list_dir("costs/jobs"):
                if n.endswith(".json"):
                    rows.append(storage.read_json(f"costs/jobs/{n}"))
        except Exception:  # noqa: BLE001
            pass
    if LOCAL.exists():
        rows += [json.loads(p.read_text(encoding="utf-8")) for p in sorted(LOCAL.glob("*.json"))]
    return [r for r in rows if _real(r)]


def _real(r):
    """A row counts only if something was really timed (test/fake rows have 0 s or a 1x1 video)."""
    m = r.get("media") or {}
    if r.get("failed"):
        return True
    return (r.get("total_s") or 0) > 0 and (m.get("width") or 2) > 1


def _per_media_s(rows, kind=None, machine_name=None):
    """stage -> list of (seconds per second of video) so a 60 s and a 5 min reel scale the same way."""
    out = {}
    for r in rows:
        d = (r.get("media") or {}).get("duration_s") or 0
        if d <= 0 or (kind and r.get("kind") != kind) or (machine_name and r["machine"]["name"] != machine_name):
            continue
        for k, v in r["stages"].items():
            out.setdefault(k, []).append(v / d)
    return out


def estimate(rows, seconds, kind="analysis", machine_name=None, pr=None):
    """Predict time + cost for a reel of `seconds` from measured rows. No data = says so, invents nothing."""
    pr = pr or pricing()
    per = _per_media_s(rows, kind, machine_name)
    if not per:
        return {"ok": False, "why": f"no measured {kind} rows yet" + (f" on {machine_name}" if machine_name else "")}
    stages = {k: round(st.median(v) * seconds, 1) for k, v in per.items()}
    row = {"total_s": round(sum(stages.values()), 1), "usage": {}}
    usd = equivalents(row, pr)
    tok = [r["usage"].get("gemini", {}) for r in rows if r.get("kind") == kind and r.get("usage", {}).get("gemini")]
    if tok:
        mi, mo = st.median(t.get("in_tok", 0) for t in tok), st.median(t.get("out_tok", 0) for t in tok)
        usd["gemini"] = _tok_usd(pr["gemini"]["usd_per_mtok"], pr["gemini"]["alias_priced_as"], mi, mo)
        usd["gemini_tokens_median"] = {"in": mi, "out": mo}
    return {"ok": True, "media_s": seconds, "stages_s": stages, "total_s": row["total_s"], "usd_equivalent": usd,
            "rows_used": sum(1 for r in rows if r.get("kind") == kind), "inr": {k: round(v * pr["usd_inr"]["value"], 2) for k, v in usd.items() if isinstance(v, float) and k != "inr_factor"}}


def report(rows, pr=None):
    pr = pr or pricing()
    month = time.strftime("%Y-%m", time.gmtime())
    gh_min = sum(math.ceil(r["total_s"] / 60) for r in rows if r["machine"]["name"] == "github-ubuntu-2core" and r.get("at", "").startswith(month))
    inc = pr["github_actions"]["included_usd_per_month"][pr["github_actions"]["plan_now"]]
    kg_h = sum(r["total_s"] for r in rows if r["machine"].get("kaggle_gpu")) / 3600
    by = {}
    for r in rows:
        by.setdefault(r["kind"], []).append(r)
    kinds = {}
    for k, rs in by.items():
        per = _per_media_s(rs)
        tot = [r["total_s"] for r in rs]
        mins = [r["media"]["duration_s"] / 60 for r in rs if (r.get("media") or {}).get("duration_s")]
        gross = [r["usd_equivalent"]["github_actions_free_gross"] for r in rs if "github_actions_free_gross" in r.get("usd_equivalent", {})]
        kinds[k] = {"rows": len(rs), "median_total_s": round(st.median(tot), 1), "p95_total_s": _pct(tot, 0.95),
                    "median_rtf": round(st.median([r["rtf"] for r in rs if "rtf" in r]), 3) if any("rtf" in r for r in rs) else None,
                    "usd_github_per_media_min": round(sum(gross) / sum(mins), 4) if gross and mins else None,
                    "cache_hits": sum(1 for r in rs if r.get("usage", {}).get("flags", {}).get("ears_cache_hit")),
                    "failed_rows": sum(1 for r in rs if r.get("failed")),
                    "median_queue_s": round(st.median([r["queue_s"] for r in rs if r.get("queue_s") is not None]), 1) if any(r.get("queue_s") is not None for r in rs) else None,
                    "median_cpu_util_pct": round(st.median([r["resources"]["cpu_util_pct"] for r in rs if r.get("resources")]), 1) if any(r.get("resources") for r in rs) else None,
                    "max_peak_rss_mb": max([r["resources"]["peak_rss_mb"] or 0 for r in rs if r.get("resources")], default=None),
                    "stage_s_per_media_min": {s: round(st.median(v) * 60, 1) for s, v in per.items()}}
    return {"rows": len(rows), "month": month,
            "github_actions": {"minutes_counted_this_month": gh_min, "usd_gross": round(gh_min * pr["github_actions"]["linux_2core_usd_per_min"], 2),
                               "included_usd": inc, "left_usd": round(inc - gh_min * pr["github_actions"]["linux_2core_usd_per_min"], 2)},
            "kaggle_gpu_hours_used_total": round(kg_h, 2), "kaggle_weekly_quota_h_reported": pr["kaggle"]["gpu_hours_per_week_reported"],
            "kinds": kinds}
