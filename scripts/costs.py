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


def record(storage, job_id, kind, media=None, stages=None, extra=None, name=None):
    """Write one row. Drive first, local file as fallback. Returns the path or None. Never raises."""
    try:
        row = build_row(job_id, kind, media, stages, extra)
        name = name or f"{job_id}__{kind}__{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
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
    if r.get("failed") or r.get("kind") == "claude":
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
    gh_usd = gh_min * pr["github_actions"]["linux_2core_usd_per_min"]
    cl = [r["usage"]["claude"] for r in rows if r.get("kind") == "claude" and r.get("usage", {}).get("claude")]
    claude = {"sessions": len(cl), "in_tok": sum(x.get("in_tok", 0) for x in cl), "out_tok": sum(x.get("out_tok", 0) for x in cl),
              "cache_read_tok": sum(x.get("cache_read_tok", 0) for x in cl), "exact_rows": sum(1 for x in cl if not x.get("estimated")),
              "limit_pct": "not exposed by Anthropic: only tokens + API-equivalent USD are known"}
    return {"rows": len(rows), "month": month, "claude": claude,
            "github_actions": {"minutes_counted_this_month": gh_min, "usd_gross": round(gh_usd, 2), "pct_of_included": round(100 * gh_usd / inc, 2) if inc else None,
                               "included_usd": inc, "left_usd": round(inc - gh_usd, 2)},
            "kaggle_gpu_hours_used_total": round(kg_h, 2), "kaggle_weekly_quota_h_reported": pr["kaggle"]["gpu_hours_per_week_reported"],
            "kinds": kinds}


class track:
    """Context manager: every job that renders or speaks writes ONE cost row, even when it fails. Never raises.
        with costs.track(storage, "spicy2", "render_preview", media={...}) as t: ...   # stage("x") blocks inside become row stages
    Remember the rule: no row = the job is not finished (gate-check cost <job>)."""

    def __init__(self, storage, job_id, kind, media=None, extra=None):
        self.storage, self.job, self.kind, self.media, self.extra = storage, job_id, kind, media or {}, dict(extra or {})
        self.path = None

    def __enter__(self):
        from .common import stage_times
        stage_times(reset=True)
        self._m = mark()
        return self

    def __exit__(self, et, ev, tb):
        from .common import stage_times
        st_ = stage_times(reset=True)
        if not st_:  # nothing wrapped in stage(): still time the whole block
            st_ = {"total": round(time.time() - self._m["wall"], 1)}
        extra = {**self.extra, "resources": resources_since(self._m)}
        if et is not None:
            extra.update(failed=True, error=et.__name__)
        self.path = record(self.storage, self.job, self.kind, media=self.media, stages=st_, extra=extra)
        return False


def job_has_row(job_id, storage=None):
    """True when a measured cost row exists for this job (Drive when connected, else costs/local)."""
    return any(r.get("job") == job_id and r.get("kind") != "claude" for r in load_rows(storage))


def claude_from_transcript(path):
    """Exact Claude tokens of one session, summed from its transcript file (usage blocks). Returns {model: {...}} or {}."""
    out = {}
    try:
        for ln in open(path, encoding="utf-8"):
            try:
                m = (json.loads(ln) or {}).get("message")
            except ValueError:
                continue
            u = m.get("usage") if isinstance(m, dict) else None
            if not u:
                continue
            d = out.setdefault(m.get("model", "unknown"), {"in_tok": 0, "out_tok": 0, "cache_read_tok": 0, "cache_write_tok": 0, "calls": 0})
            d["in_tok"] += u.get("input_tokens", 0)
            d["out_tok"] += u.get("output_tokens", 0)
            d["cache_read_tok"] += u.get("cache_read_input_tokens", 0)
            d["cache_write_tok"] += u.get("cache_creation_input_tokens", 0)
            d["calls"] += 1
    except OSError:
        return {}
    return out


def find_transcripts(hint=""):
    """Transcript files to count: the hook's path first, then $CLAUDE_TRANSCRIPT, then every ~/.claude/projects/**/*.jsonl touched today."""
    import glob
    seen, out = set(), []
    cands = [hint, os.environ.get("CLAUDE_TRANSCRIPT", "")]
    day = time.time() - 86400
    cands += sorted(glob.glob(os.path.expanduser("~/.claude/projects/**/*.jsonl"), recursive=True), key=os.path.getmtime)
    for c in cands:
        if c and c not in seen and os.path.isfile(c) and (c in (hint, os.environ.get("CLAUDE_TRANSCRIPT", "")) or os.path.getmtime(c) > day):
            seen.add(c)
            out.append(c)
    return out


def _hook_log(msg):
    try:
        LOCAL.mkdir(parents=True, exist_ok=True)
        with open(LOCAL.parent / "claude_hook.log", "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ ", time.gmtime()) + msg + "\n")
    except OSError:
        pass


def record_claude_session(storage, session_id, transcript_path):
    """Stop-hook target: one row per Claude session (overwritten as the session grows), tokens per model. Never raises.
    Never silent: when no transcript can be read, an explicit 'unmeasured' row + a log line are written, so the gap is visible and gate-check blocks."""
    sid = str(session_id)[:8]
    by = {}
    for path in find_transcripts(transcript_path):
        by = claude_from_transcript(path)
        if by:
            break
    if not by:
        _hook_log(f"NO transcript readable for session {sid} (hint={transcript_path!r}): tokens UNMEASURED")
        with _LOCK:
            _USE["claude"] = {"in_tok": 0, "out_tok": 0, "cache_read_tok": 0, "calls": 0, "model": "unknown", "estimated": True, "unmeasured": True}
        return record(storage, f"session-{sid}", "claude", extra={"note": "UNMEASURED: no transcript found", "unmeasured": True},
                      name=f"session-{sid}__claude__total.json")
    top = max(by, key=lambda k: by[k]["in_tok"] + by[k]["out_tok"])
    tot = {k: sum(v[k] for v in by.values()) for k in ("in_tok", "out_tok", "cache_read_tok", "cache_write_tok", "calls")}
    with _LOCK:
        _USE["claude"] = {**tot, "model": top, "estimated": False, "by_model": by}
    return record(storage, f"session-{sid}", "claude", extra={"note": "exact tokens from the session transcript"},
                  name=f"session-{sid}__claude__total.json")


def claude_status(storage=None, days=1):
    """-> (ok, message). ok only when a Claude row with real tokens exists from the last `days` days."""
    now = time.time()
    rows = [r for r in load_rows(storage) if r.get("kind") == "claude"]
    def _tok(r):
        c = (r.get("usage") or {}).get("claude") or {}
        return 0 if c.get("unmeasured") else c.get("in_tok", 0) + c.get("out_tok", 0)
    good = [r for r in rows if _tok(r) > 0]
    if good:
        return True, f"{len(good)} Claude session row(s) with real tokens"
    return False, "NO measured Claude tokens: run `./run cost claude-auto`, or `./run cost claude --job J --tin N --tout N` by hand (see costs/claude_hook.log)"


def backfill_github(repo, limit=40):
    """Rebuild render/voice rows from past GitHub Actions runs (real measured seconds), so estimates exist even when no row was written.
    Writes to costs/local; skips runs already written. Returns the number of rows added."""
    import re
    import subprocess

    def gh(args):
        p = subprocess.run(["gh", "api", *args], capture_output=True, text=True, timeout=120)
        return p.stdout if p.returncode == 0 else ""

    LOCAL.mkdir(parents=True, exist_ok=True)
    have = {p.name for p in LOCAL.glob("*.json")}
    added = 0
    for wf, kind_default in (("sample.yml", "render_preview"), ("voice.yml", "voice")):
        runs = json.loads(gh([f"repos/{repo}/actions/workflows/{wf}/runs?per_page={limit}&status=completed"]) or "{}").get("workflow_runs", [])
        for r in runs:
            nm = f"gh{r['id']}__{kind_default}__backfill.json"
            if nm in have or r.get("conclusion") != "success":
                continue
            jobs = json.loads(gh([f"repos/{repo}/actions/runs/{r['id']}/jobs"]) or "{}").get("jobs", [])
            if not jobs:
                continue
            steps = {s["name"]: s for s in jobs[0].get("steps", []) if s.get("started_at") and s.get("completed_at")}
            main = next((s for n, s in steps.items() if n.startswith(("Sample render", "Voice", "Synth"))), None)
            if not main:
                continue
            f = lambda s: time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))  # noqa: E731
            sec = f(main["completed_at"]) - f(main["started_at"])
            setup = f(jobs[0]["completed_at"]) - f(jobs[0]["started_at"]) - sec
            media, kind = {}, kind_default
            if wf == "sample.yml":
                log_txt = gh([f"repos/{repo}/actions/jobs/{jobs[0]['id']}/logs"])
                m = re.search(r"SAMPLE render ok=\w+ ([\d.]+)s", log_txt or "")
                kind = "render_final" if "FINAL delivered" in (log_txt or "") else "render_preview"
                if not m:
                    continue
                media = {"duration_s": float(m.group(1)), "width": 2160 if kind == "render_final" else 1080, "height": 3840 if kind == "render_final" else 1920, "fps": 30}
            row = build_row(f"gh{r['id']}", kind, media, {"setup": round(setup, 1), "render" if wf == "sample.yml" else "tts": round(sec, 1)},
                            {"at": r["created_at"], "basis": f"backfilled from GitHub run {r['id']} ({r.get('display_title', '')[:40]})"})
            row["machine"] = {"name": "github-ubuntu-2core", "cpus": 2, "kaggle_gpu": False}
            (LOCAL / f"gh{r['id']}__{kind}__backfill.json").write_text(json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8")
            added += 1
    return added
