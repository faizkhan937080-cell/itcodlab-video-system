"""Job engine: the worker reads jobs from Drive jobs/inbox, runs the machine steps, and STOPS at every
approval gate until a matching approval file (or Approvals-tab row) says Y.

Commands reach the worker as small JSON files in Drive (written by Claude from chat after the user
says so). State lives in Drive jobs/state/<id>.json. Nothing is deleted; inbox files stay forever.
"""
import re
import json
import shutil
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from . import finish as finish_mod
from . import layout
from . import render as render_mod
from .common import limits, log, now_iso, tail, workdir
from .dna import REQUIRED_TYPES, errors_tail, save_dna, validate
from .dna_check import check as check_dna

TERMINAL = {"DONE", "FAILED", "NEEDS_INPUT", "MEASURED", "SAMPLE_OK"}


VIDEO_SUFFIXES = (".mp4", ".mkv", ".webm", ".mov")


def pick_source(files):
    """The merged video yt-dlp wrote. Never a leftover single stream (source.fdash-123.m4a / .fdash-123.mp4):
    those sort first alphabetically and are audio-only or video-only (job reel-DeoxIgMPlS-e failed on one)."""
    ok = [f for f in files if f.suffix.lower() in VIDEO_SUFFIXES and ".f" not in f.name[len("source"):-len(f.suffix)]]
    if not ok:
        raise RuntimeError("download has no merged video file (only single streams: "
                           + ", ".join(sorted(f.name for f in files)) + ")")
    return max(ok, key=lambda f: f.stat().st_size)


def merge_streams(wd):
    """yt-dlp sometimes leaves one video-only and one audio-only stream (merge skipped when ffmpeg was not found
    at download time). If there is no merged video but exactly those two, join them losslessly into source.mp4."""
    from .common import run_cmd
    files = list(Path(wd).glob("source.*"))
    if any(f.suffix.lower() in VIDEO_SUFFIXES and ".f" not in f.name[len("source"):-len(f.suffix)] for f in files):
        return None
    vids = [f for f in files if f.suffix.lower() in VIDEO_SUFFIXES]
    auds = [f for f in files if f.suffix.lower() in (".m4a", ".aac", ".opus", ".mp3", ".ogg")]
    if len(vids) != 1 or len(auds) != 1:
        return None
    out = Path(wd) / "source.mp4"
    rc, _, err = run_cmd(["ffmpeg", "-loglevel", "error", "-y", "-i", str(vids[0]), "-i", str(auds[0]),
                          "-c", "copy", "-movflags", "+faststart", str(out)], timeout=600)
    if rc != 0 or not out.exists():
        raise RuntimeError("could not join video and audio streams:\n" + tail(err))
    return out


class Worker:
    def __init__(self, storage, sheets=None, work=None):
        self.storage = storage
        self.sheets = sheets
        self.work = Path(work) if work else workdir()
        self.lim = limits()
        try:
            from .netguard import guard
            guard().attach(storage)        # shared per-host counters + cooldowns (Drive jobs/state/_net.json)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------ state
    def _state_rel(self, jid):
        return f"jobs/state/{jid}.json"

    def load_state(self, job):
        rel = self._state_rel(job["id"])
        if self.storage.exists(rel):
            return self.storage.read_json(rel)
        return {"id": job["id"], "type": job.get("type"), "status": "QUEUED", "created": now_iso(),
                "updated": now_iso(), "history": [], "attempts": {}, "candidate_ver": 1, "plan_ver": 1,
                "paths": {}, "note": "picked up by worker"}

    def save(self, st, job):
        st["updated"] = now_iso()
        self.storage.write_state(self._state_rel(st["id"]), st)
        if self.sheets:
            self.sheets.upsert_job(st, job)

    def set_status(self, st, job, status, note=""):
        st["status"] = status
        st["note"] = note
        st["history"].append({"ts": now_iso(), "status": status, "note": note[:200]})
        self.save(st, job)

    # ------------------------------------------------------------ approvals
    def approval(self, st, job, gate, rev):
        """Return 'Y' / 'N' / None, plus feedback. Files in Drive jobs/approvals win over the Sheet."""
        rel = f"jobs/approvals/{job['id']}__gate{gate}__r{rev}.json"
        dec, fb, src = None, "", None
        if self.storage.exists(rel):
            try:
                d = self.storage.read_json(rel)
                dec = str(d.get("decision", "")).strip().upper()[:1]
                fb, src = str(d.get("feedback", "")), "file"
            except Exception:  # half-written file: wait for the next pass
                dec = None
        if dec not in ("Y", "N") and self.sheets and self.sheets.enabled:
            dec, fb = self.sheets.find_approval(job["id"], gate, rev)
            src = "sheet"
        if dec in ("Y", "N"):
            key = f"g{gate}r{rev}"
            if key not in st.setdefault("gates_logged", []):
                st["gates_logged"].append(key)
                if self.sheets and src == "file":
                    self.sheets.log_approval(job["id"], gate, rev, dec, fb)
            return dec, fb
        return None, ""

    # ------------------------------------------------------------ failure handling
    def failed(self, st, job, stage, exc, terminal="FAILED", terminal_note=""):
        n = st["attempts"].get(stage, 0) + 1
        st["attempts"][stage] = n
        st["error_tail"] = tail(f"{exc}\n{traceback.format_exc()[-1200:]}")
        log(f"{job['id']} {stage} failed (attempt {n})")
        try:  # a failed step still cost time: record it so retries show up in the price
            from . import costs
            from .common import stage_times
            costs.record(self.storage, job["id"], f"{stage}_failed", stages=stage_times(reset=True),
                         extra={"failed": True, "attempt": n, "error": st["error_tail"][-160:]})
        except Exception:  # noqa: BLE001
            pass
        if n > self.lim["jobs"]["max_retries"]:
            self.set_status(st, job, terminal, terminal_note or f"{stage} failed {n} times. See error_tail.")
        else:
            self.save(st, job)
        return False

    # ------------------------------------------------------------ cap
    def _started_today(self, bulk=False):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        n = 0
        for name in self.storage.list_dir("jobs/state"):
            if name.endswith(".json"):
                try:
                    sj = self.storage.read_json(f"jobs/state/{name}")
                    if sj.get("started", "").startswith(today) and bool(sj.get("bulk")) == bulk:
                        n += 1
                except Exception:
                    pass
        return n

    # ------------------------------------------------------------ main loop
    def process_once(self):
        summary = []
        done = self.__dict__.setdefault("_finished", set())  # finished jobs are not re-read every 20 s
        for name in self.storage.list_dir("jobs/inbox"):
            if not name.endswith(".json") or name[:-5] in done:
                continue
            try:
                job = self.storage.read_json(f"jobs/inbox/{name}")
                jid = job["id"]
            except Exception:  # half-written or invalid file: try again next pass
                continue
            st = self.load_state(job)
            if st["status"] in TERMINAL:
                done.add(name[:-5])
                continue
            for _ in range(25):
                if not self.step(job, st):
                    break
            summary.append((jid, st["status"]))
        return summary

    def _self_update(self):
        """git pull the code; if it changed, check the new code imports, then restart (no human step).
        Broken new code is rolled back so the worker can never kill itself with a bad push."""
        import os
        import sys
        from .common import ROOT, run_cmd
        if not (ROOT / ".git").exists():
            return
        rc, before, _ = run_cmd(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
        rc2, _, _ = run_cmd(["git", "-C", str(ROOT), "pull", "--ff-only", "-q"], timeout=120)
        rc3, after, _ = run_cmd(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
        if not (rc == 0 and rc2 == 0 and rc3 == 0) or before.strip() == after.strip():
            return
        run_cmd([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")], timeout=600)  # new libs
        ok, _, err = run_cmd([sys.executable, "-c", "import scripts.cli, scripts.jobs, scripts.pack, scripts.review"],
                             cwd=str(ROOT), timeout=120)
        if ok != 0:
            run_cmd(["git", "-C", str(ROOT), "reset", "-q", "--hard", before.strip()])
            log(f"new code {after.strip()[:7]} does not import; rolled back to {before.strip()[:7]}")
            try:
                self.storage.write_state("jobs/state/_worker_alert.json", {
                    "id": "_worker", "status": "ALERT", "updated": now_iso(),
                    "note": f"update {after.strip()[:7]} broke imports, rolled back to {before.strip()[:7]}: " + tail(err, 3)})
            except Exception:  # noqa: BLE001
                pass
            return
        log(f"code updated {before.strip()[:7]} -> {after.strip()[:7]}; restarting worker")
        os.execv(str(ROOT / "run"), [str(ROOT / "run"), *sys.argv[1:]])

    def run_until_idle(self, max_minutes=330, grace_s=180):
        """For GitHub Actions / one-shot hosts: work until nothing changes for `grace_s` seconds (new inbox jobs,
        approvals or candidates that arrive meanwhile are still picked up), then return so the machine can stop."""
        poll = self.lim["jobs"]["poll_seconds"]
        end = time.time() + max_minutes * 60
        last, changed = None, time.time()
        while time.time() < end:
            res = self.process_once()
            if res != last:
                last, changed = res, time.time()
            elif time.time() - changed >= grace_s:
                return last or []
            time.sleep(poll)
        return last or []

    def loop(self, max_minutes=60):
        poll = self.lim["jobs"]["poll_seconds"]
        end = time.time() + max_minutes * 60
        n = 0
        while time.time() < end:
            self.process_once()
            n += 1
            if n % 15 == 0:  # jobs run inside process_once, so no job is mid-run here
                try:
                    self._self_update()
                except Exception as e:  # noqa: BLE001
                    log(f"self-update skipped: {e}")
            time.sleep(poll)

    def step(self, job, st):
        """Run one state transition. Return True if progress was made (call again)."""
        if job.get("type") == "analyze":
            return self.step_analyze(job, st)
        if job.get("type") == "render":
            return self.step_render(job, st)
        if job.get("type") == "style":
            return self.step_style(job, st)
        self.set_status(st, job, "NEEDS_INPUT", f"unknown job type: {job.get('type')}")
        return False

    def _ensure_local_source(self, st, wd):
        """A new Actions run (or a new VM) has no copy of the video the last run downloaded: pull our own Drive copy back,
        so a job that was cut off mid-analysis resumes instead of failing its last attempt on 'file not found'."""
        p = Path(st["paths"].get("source_local") or "")
        if p.is_file() and p.stat().st_size > 0:
            return p
        rel = st["paths"].get("source_drive")
        if not rel:
            raise FileNotFoundError("the source video is not on this machine and no Drive copy is recorded")
        dest = Path(wd) / ("source" + (Path(rel).suffix or ".mp4"))
        self.storage.fetch(rel, dest)
        log(f"source video restored from Drive: {rel}")
        st["paths"]["source_local"] = str(dest)
        return dest

    # ================================================================ analyze jobs
    def step_analyze(self, job, st):
        s, jid = st["status"], job["id"]
        wd = self.work / jid
        if s == "QUEUED":
            errs = validate("job", job)
            if errs:
                self.set_status(st, job, "NEEDS_INPUT", "invalid job file:\n" + errors_tail(errs))
                return False
            st["bulk"] = bool(job.get("bulk"))
            cap = self.lim["claude"]["bulk_daily_cap" if st["bulk"] else "daily_job_cap"]
            if self._started_today(st["bulk"]) >= cap and "started" not in st:
                st["note"] = "daily job cap reached; will start tomorrow (UTC) or raise the cap in limits.json"
                self.save(st, job)
                return False
            st["started"] = now_iso()
            self.set_status(st, job, "ACQUIRING", "getting the reference video")
            return True
        if s == "ACQUIRING":
            try:
                src = self._acquire(job, wd)
                st["paths"]["source_local"] = str(src)
                self._resolve_creator(job, st, wd)
                self._make_creator_folders(st)
                st["paths"]["analysis"] = self._analysis_rel(st, job)
                rel = self.storage.put_file(src, f"{st['paths']['analysis']}/{src.name}")
                st["paths"]["source_drive"] = rel
                self.set_status(st, job, "ANALYZING", "frame-by-frame analysis running")
                return True
            except Exception as e:  # noqa: BLE001
                from .netguard import HostBlocked
                from .security import SecurityError
                if isinstance(e, (HostBlocked, SecurityError)):      # no retries: retrying is exactly what gets accounts banned
                    why = ("ALERT a site asked us to stop | need: wait, or put the video file in Drive input/references/ and send a job with 'file'"
                           if isinstance(e, HostBlocked) else "ALERT the downloaded file failed the safety check | need: check the source, send another file")
                    try:
                        self.storage.write_state("jobs/state/_worker_alert.json", {"id": "_worker", "status": "ALERT", "updated": now_iso(),
                                                                                 "note": f"{why}: {str(e)[:200]}"})
                    except Exception:  # noqa: BLE001
                        pass
                    self.set_status(st, job, "NEEDS_INPUT", f"{why}. Detail: {str(e)[:200]}")
                    return False
                return self.failed(st, job, "acquire", e, terminal="NEEDS_INPUT",
                                   terminal_note=("Could not get the video from the link. Put the video file in "
                                                  "Drive input/references/ and send a new job with 'file'."))
        if s == "ANALYZING":
            try:
                from .pack import run_pipeline
                src = self._ensure_local_source(st, wd)
                from .common import stage, stage_times
                from . import costs as _costs
                _t0, _m0 = time.time(), _costs.mark()
                res = run_pipeline(str(src), wd / "analysis", job_id=jid, mode=job["mode"])
                if not job.get("bulk") and job["mode"] != "audio":     # rulebooks/23 rule 2: what MOVES, not only what cuts
                    try:
                        with stage("style_record"):
                            from . import style_record
                            rec = style_record.build(src, res["out_root"], self.lim)
                            if rec.get("event_collage"):
                                shutil.copy2(Path(res["out_root"]) / rec["event_collage"], Path(res["pack"]) / "collage_events.jpg")
                            st["style_record"] = {"complete": rec["complete"], "events": rec["event_count"], "problems": rec["problems"]}
                    except Exception as e:  # noqa: BLE001
                        st["style_record"] = {"complete": False, "error": f"{type(e).__name__}: {e}"[:160]}
                from .describe import describe_pack
                idx = json.loads((res["out_root"] / "collage_index.json").read_text(encoding="utf-8"))
                bulk = bool(job.get("bulk"))
                if not bulk:
                    with stage("describe"):
                        st["describe"] = describe_pack(res["pack"], idx)
                    with stage("review_publish"):
                        from .review import publish
                        st["review"] = publish(res["pack"], jid, idx)
                    st["review"]["tried"] = now_iso()
                try:  # cost/time ledger (never blocks the job)
                    from . import costs
                    stg = json.loads((res["out_root"] / "timings.json").read_text(encoding="utf-8"))
                    for k, v in stage_times(reset=True).items():
                        stg[k] = round(stg.get(k, 0) + v, 1)
                    inf = res.get("info", {})
                    costs.record(self.storage, jid, "analysis", stages=stg, extra={
                        "wall_s": round(time.time() - _t0, 1), "mode": job["mode"], "bulk": bulk,
                        "resources": _costs.resources_since(_m0), "queue_s": _costs.queue_s(job.get("created", "")),
                        "attempt": st["attempts"].get("analyze", 0) + 1,
                        "source_bytes": Path(src).stat().st_size if Path(src).exists() else None},
                        media={k: inf.get(k) for k in ("duration_s", "width", "height", "fps", "codec")})
                except Exception:  # noqa: BLE001
                    pass
                self._write_measured_drafts(res, job, st)
                base = self._analysis_rel(st, job)
                self.storage.put_tree(res["out_root"], base)
                st["paths"]["analysis"] = base
                st["paths"]["pack"] = f"{base}/pack"
                st["pack_manifest"] = res["manifest"]
                if bulk:
                    self.set_status(st, job, "MEASURED", f"measured only (batch {job.get('batch', '-')}); "
                                    f"drafts in {layout.cand_dir(base)}/measured-<type>.json")
                    self._maybe_corpus(job, st)
                    return False
                if job["mode"] == "audio" and self._audio_data_complete(res["pack"]):
                    types = REQUIRED_TYPES["audio"]  # no collages to judge: sound + scripting go straight to DNA drafting
                    self.set_status(st, job, "AWAIT_CANDIDATE",
                                    f"Audio data complete (gate 2 not needed). Waiting for DNA candidate(s): {', '.join(types)} "
                                    f"(file {layout.cand_dir(base)}/candidate-<type>-v{st['candidate_ver']}.json)")
                    return True
                self.set_status(st, job, "AWAIT_GATE2",
                                f"Analysis ready: {res['manifest']['collage_count']} collage(s) in "
                                f"{st['paths']['pack']}. Look at them and approve gate 2.")
                return True
            except Exception as e:  # noqa: BLE001
                return self.failed(st, job, "analysis", e)
        if s == "AWAIT_GATE2":
            self._retry_review(st, job, wd)
            dec, fb = self.approval(st, job, 2, 1)
            if dec == "Y":
                types = REQUIRED_TYPES[job["mode"]]
                self.set_status(st, job, "AWAIT_CANDIDATE",
                                f"Waiting for DNA candidate(s): {', '.join(types)} "
                                f"(file {layout.cand_dir(self._analysis_rel(st, job))}/candidate-<type>-v{st['candidate_ver']}.json)")
                return True
            if dec == "N":
                self.set_status(st, job, "NEEDS_INPUT", f"Gate 2 rejected: {fb}. Send a new job with other settings.")
            return False
        if s == "AWAIT_CANDIDATE":
            return self._check_candidates(job, st)
        if s == "AWAIT_GATE3":
            dec, fb = self.approval(st, job, 3, st["candidate_ver"])
            if dec == "Y":
                self.set_status(st, job, "SAVING_DNA", "saving approved DNA")
                return True
            if dec == "N":
                st["candidate_ver"] += 1
                self.set_status(st, job, "AWAIT_CANDIDATE",
                                f"Gate 3 rejected: {fb}. Waiting for candidate v{st['candidate_ver']}.")
                return True
            return False
        if s == "SAVING_DNA":
            try:
                saved = []
                target = st.get("target") or job["target"]
                for t, rel in st["candidates"].items():
                    if not self.storage.exists(rel):  # reel folder was moved: candidate sits under the followed folder
                        rel = f"{layout.cand_dir(self._analysis_rel(st, job))}/{rel.rsplit('/', 1)[-1]}"
                    obj = self.storage.read_json(rel)
                    path, ver = save_dna(self.storage, target, t, obj, jid)
                    saved.append(path)
                    if self.sheets:
                        creator = target.split(":", 1)[1] if ":" in target else ""
                        self.sheets.add_dna_index(f"{t}-{jid}-v{ver}", "creator" if creator else "general",
                                                  creator, t, ver, path, jid)
                st["dna_saved"] = saved
                if target.startswith("creator:"):
                    h = target.split(":", 1)[1]
                    ptr = {"layout_version": 2, "reel_id": self._reel_code(job), "creator": h, "job": jid,
                           "link": job.get("link", ""), "mode": job["mode"],
                           "analysis": self._analysis_rel(st, job), "dna": saved, "meta": st.get("source_meta", {}),
                           "saved": now_iso()}
                    self.storage.put_json(f"{self._analysis_rel(st, job)}/reel.json", ptr)
                    from .recipe import write as write_recipe
                    write_recipe(self.storage, ptr)
                    from .creator_index import write_index
                    write_index(self.storage, h)
                    if self.sheets:
                        self.sheets.upsert_creator(h, jid)
                st["output_link"] = saved[0] if saved else ""
                self.set_status(st, job, "DONE", "DNA saved: " + ", ".join(saved))
                return False
            except Exception as e:  # noqa: BLE001
                return self.failed(st, job, "save_dna", e)
        return False

    def _acquire(self, job, wd):
        wd.mkdir(parents=True, exist_ok=True)
        if job.get("file"):
            name = Path(job["file"]).name
            got = self.storage.fetch(job["file"], wd / name)
            from .security import require_safe
            require_safe(got, "video")
            return got
        import os
        from .common import run_cmd
        from .netguard import config as net_config, guard, host_key
        cfg = net_config()
        cmd = ["yt-dlp", "-f", "bv*+ba/b", "--merge-output-format", "mp4", "--no-playlist", "--write-info-json",
               "-o", str(wd / "source.%(ext)s"), *cfg["yt_dlp_polite"]]
        cookies = os.environ.get("ITCOD_COOKIES")
        if cookies and Path(cookies).exists():
            cmd += ["--cookies", cookies]
        key = host_key(job["link"], cfg)
        g = guard()
        g.before(key)                      # gap, daily maximum, cooldown (raises HostBlocked)
        rc, out, err = run_cmd(cmd + [job["link"]], timeout=1800)
        if rc != 0:
            g.after(key, None, err or out)  # a block signal starts the cooldown; nothing else is tried
            raise RuntimeError("yt-dlp failed:\n" + tail(err or out))
        merge_streams(wd)
        src = pick_source(list(wd.glob("source.*")))
        from .security import require_safe
        require_safe(src, "video")
        return src

    def _resolve_creator(self, job, st, wd):
        """target 'creator:auto' -> creator:<instagram handle> read from yt-dlp metadata. One name everywhere."""
        st["target"] = job["target"]
        if job["target"] not in ("creator:auto", "creator"):
            return
        import json
        handle = ""
        info = wd / "source.info.json"
        if info.exists():
            meta = json.loads(info.read_text(encoding="utf-8"))
            for k in ("channel", "uploader_id", "uploader"):
                v = str(meta.get(k) or "").strip().lstrip("@")
                if v and not v.isdigit():
                    handle = v
                    break
            st["source_meta"] = {k: meta.get(k) for k in ("channel", "uploader_id", "uploader", "title", "duration", "webpage_url")}
        handle = re.sub(r"[^a-z0-9_.-]", "", handle.lower())[:40]
        if len(handle) < 2:
            handle = "_unassigned"  # creator unknown: still one clear folder, nothing lost (Faiz can name it later)
            st["note_creator"] = "creator handle not readable from the link: kept in creators/_unassigned"
        st["target"] = f"creator:{handle}"

    @staticmethod
    def _audio_data_complete(pack_dir):
        """Transcript covers >= 90 %, loudness measured, audit passed -> nothing for a human to look at."""
        try:
            m = json.loads((Path(pack_dir) / "metrics_summary.json").read_text(encoding="utf-8"))
            return (m["transcript"]["coverage_ratio"] >= 0.9 and bool(m["audio"].get("ebu_r128"))
                    and m["audit"]["pass"] is True)
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    def _reel_code(job):
        """The reel's permanent folder name: job['reel_id'], else the Instagram code in the link, else the job id."""
        from .reelid import shortcode
        return job.get("reel_id") or shortcode(job.get("link", "")) or job["id"]

    def _analysis_rel(self, st, job):
        """Everything of one reel lives in ONE folder: creators/<h>/reel-<code>/ (see layout.py).
        Jobs started before this layout keep the path stored in their state (followed if the folder was moved)."""
        p = (st.get("paths") or {}).get("analysis")
        t = st.get("target") or job.get("target", "general")
        is_creator = t.startswith("creator:") and t != "creator:auto"
        if p:
            if not self.storage.exists(p) and is_creator:
                h = t.split(":", 1)[1]
                for alt in (layout.reel_rel(h, self._reel_code(job)), f"creators/{h}/videos/{self._reel_code(job)}",
                            f"creators/{h}/videos/{job['id']}", f"analysis/creators/{h}/{job['id']}"):
                    if self.storage.exists(alt):  # folder was moved into the creator's folder: follow it
                        st["paths"]["analysis"] = alt
                        st["paths"]["pack"] = f"{alt}/pack"
                        return alt
            return p
        if is_creator:
            return layout.reel_rel(t.split(":", 1)[1], self._reel_code(job))
        return f"analysis/general/{self._reel_code(job)}"

    def _make_creator_folders(self, st):
        t = st.get("target", "")
        if t.startswith("creator:") and t != "creator:auto":
            h = t.split(":", 1)[1]
            for sub in ("dna", "style", "ideas", "scripts", "made"):
                self.storage.ensure_dir(f"creators/{h}/{sub}")

    def _retry_review(self, st, job, wd):
        """If the collage copy to the review branch failed (e.g. token without write access), try again while the job
        waits at gate 2: after 2, 4, 8, 16 min, then every 30 min. So it also works when Faiz fixes the token later.
        No new job needed. Never raises."""
        rv = st.get("review") or {}
        if rv.get("status") != "failed":
            return
        try:
            tries = int(rv.get("tries", 1))
            wait = min(120 * 2 ** (tries - 1), 1800)
            last = rv.get("tried")
            if last and (datetime.now(timezone.utc) - datetime.fromisoformat(last.replace("Z", "+00:00"))).total_seconds() < wait:
                return
            from .review import publish
            pack = wd / "analysis" / "pack"
            idx_p = wd / "analysis" / "collage_index.json"
            if not pack.exists():
                return
            idx = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else None
            res = publish(pack, job["id"], idx)
            res["tried"] = now_iso()
            res["tries"] = tries + 1
            st["review"] = res
            self.save(st, job)
        except Exception:  # noqa: BLE001
            pass

    def _write_measured_drafts(self, res, job, st):
        """Measured part of every DNA type, saved next to the analysis (inputs for corpus building). Never raises."""
        from .dna_draft import DRAFTERS
        try:
            sm = json.loads((res["pack"] / "metrics_summary.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return
        creator = (st.get("target") or job.get("target") or "").split(":", 1)[-1]
        creator = "" if creator in ("", "general", "auto") else creator
        for t in REQUIRED_TYPES[job["mode"]]:
            try:
                d = DRAFTERS[t](sm, job["id"], job.get("link", ""), creator)
            except Exception as e:  # noqa: BLE001
                log(f"measured draft {t} skipped: {e}")
                continue
            dd = res["out_root"] if layout.is_flat(self._analysis_rel(st, job)) else res["out_root"] / "dna"
            dd.mkdir(parents=True, exist_ok=True)
            (dd / f"measured-{t}.json").write_text(
                json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    def _maybe_corpus(self, job, st):
        """When every video of a batch is measured, aggregate them (scripts only, zero Claude tokens)."""
        batch, size = job.get("batch"), job.get("batch_size")
        if not batch or not size:
            return
        from .dna_corpus import aggregate
        members = []
        for name in self.storage.list_dir("jobs/inbox"):
            try:
                j = self.storage.read_json(f"jobs/inbox/{name}")
                if j.get("batch") != batch:
                    continue
                sj = self.storage.read_json(self._state_rel(j["id"]))
                if sj.get("status") == "MEASURED":
                    members.append((j, sj))
            except Exception:  # noqa: BLE001
                continue
        if len(members) < size:
            return
        h = (st.get("target") or job.get("target") or "general").split(":", 1)[-1]
        outs = []
        for t in ("editing", "scripting", "sound"):
            dnas = []
            for j, sj in members:
                rel = f"{layout.cand_dir(sj['paths'].get('analysis'))}/measured-{t}.json"
                try:
                    dnas.append(self.storage.read_json(rel))
                except Exception:  # noqa: BLE001
                    pass
            if dnas:
                c = aggregate(t, h, dnas, [j["id"] for j, _ in members])
                outs.append(self.storage.put_json(f"creators/{h}/style/_batches/{batch}/corpus-{t}-measured.json", c))
        st["note"] += f" | batch complete: {', '.join(outs)}"
        self.save(st, job)

    def _pack_summary(self, st, job):
        """metrics_summary.json of this job (numbers the DNA is cross-checked against). None if unreadable."""
        base = self._analysis_rel(st, job)
        try:
            summary = self.storage.read_json(f"{base}/pack/metrics_summary.json")
        except Exception:  # noqa: BLE001
            return None
        try:  # packs made before best_pass(): recompute the script numbers from the saved transcript with the current code
            from . import script_metrics
            tr = self.storage.read_json(f"{base}/transcript.json")
            m = script_metrics.compute(tr, summary["video"]["duration_s"])
            if m.get("available") and m.get("pass_used") == "english" and \
                    (summary.get("script_metrics") or {}).get("pass_used") != "english":
                summary["script_metrics"] = m
        except Exception:  # noqa: BLE001
            pass
        return summary

    def _check_candidates(self, job, st):
        jid, ver = job["id"], st["candidate_ver"]
        types = REQUIRED_TYPES[job["mode"]]
        found, errors = {}, []
        for t in types:
            rel = f"{layout.cand_dir(self._analysis_rel(st, job))}/candidate-{t}-v{ver}.json"
            if not self.storage.exists(rel):
                continue
            try:
                obj = self.storage.read_json(rel)
            except Exception:
                continue  # half written
            errs = check_dna(t, obj, self._pack_summary(st, job))
            if not errs and obj.get("source", {}).get("job_id") != jid:
                errs = [f"source.job_id must be '{jid}'"]
            if errs:
                errors.append(f"{t}: " + errors_tail(errs))
            else:
                found[t] = rel
        if errors:
            st["validation_errors"] = "\n".join(errors)[-1500:]
            st["candidate_ver"] = ver + 1
            self.set_status(st, job, "AWAIT_CANDIDATE",
                            f"Candidate v{ver} was invalid (see validation_errors). Send v{ver + 1}.")
            return False
        if len(found) == len(types):
            st["candidates"] = found
            st.pop("validation_errors", None)
            self.set_status(st, job, "AWAIT_GATE3",
                            f"DNA candidate(s) valid: {', '.join(found)}. Review and approve gate 3 (rev {ver}).")
            return True
        return False

    # ================================================================ style record of an already stored reference
    def step_style(self, job, st):
        """job: {type: style, file: <Drive path of the reference video>, out: <Drive folder for the record>}"""
        if st["status"] != "QUEUED":
            return False
        src_rel, out_rel = job.get("file"), job.get("out")
        if not src_rel or not out_rel:
            self.set_status(st, job, "NEEDS_INPUT", "style job needs 'file' (reference video) and 'out' (folder)")
            return False
        try:
            from . import style_record
            from .common import stage
            wd = self.work / job["id"]
            wd.mkdir(parents=True, exist_ok=True)
            local = wd / ("source" + (Path(src_rel).suffix or ".mp4"))
            self.storage.fetch(src_rel, local)
            with stage("style_record"):
                rec = style_record.build(local, wd / "style", self.lim)
            self.storage.put_file(wd / "style" / "style_record.json", f"{out_rel}/style_record.json")
            self.storage.put_file(wd / "style" / "activity.json", f"{out_rel}/activity.json")
            if rec.get("event_collage"):
                self.storage.put_file(wd / "style" / rec["event_collage"], f"{out_rel}/{rec['event_collage']}")
                shutil.copy2(wd / "style" / rec["event_collage"], wd / "style" / "collage_events.jpg") if rec["event_collage"] != "collage_events.jpg" else None
            from .review import publish
            st["review"] = publish(wd / "style", job["id"], None)
            st["style_record"] = {"complete": rec["complete"], "events": rec["event_count"], "problems": rec["problems"], "path": f"{out_rel}/style_record.json"}
            self.set_status(st, job, "DONE", f"style record: {rec['event_count']} events, complete={rec['complete']} {rec['problems']}")
        except Exception as e:  # noqa: BLE001
            return self.failed(st, job, "style", e)
        return False

    # ================================================================ render jobs
    def _plan_rel(self, job, st):
        return f"jobs/plans/{job['id']}-v{st['plan_ver']}.json"

    def step_render(self, job, st):
        s, jid = st["status"], job["id"]
        wd = self.work / jid
        if s in ("QUEUED", "AWAIT_PLAN"):
            errs = validate("job", job)
            if errs:
                self.set_status(st, job, "NEEDS_INPUT", "invalid job file:\n" + errors_tail(errs))
                return False
            rel = self._plan_rel(job, st)
            if not self.storage.exists(rel):
                if s == "QUEUED":
                    self.set_status(st, job, "AWAIT_PLAN", f"Waiting for scene plan file {rel}")
                return False
            try:
                plan = self.storage.read_json(rel)
            except Exception:
                return False
            try:                       # a plan sent right after a code push must meet the NEW rules, not the old ones in memory
                self._self_update()
            except Exception as e:  # noqa: BLE001
                log(f"self-update before plan check skipped: {e}")
            errs = validate("scene", plan)
            if not errs:
                from . import protocol
                errs = protocol.check_plan(plan, self.storage, self.lim)
            if errs:
                st["validation_errors"] = errors_tail(errs) if not isinstance(errs, list) or not errs or not isinstance(errs[0], str) else "\n".join(errs)[:1500]
                st["plan_ver"] += 1
                self.set_status(st, job, "AWAIT_PLAN",
                                f"Plan v{st['plan_ver'] - 1} invalid (see validation_errors). Send v{st['plan_ver']}.")
                return False
            st.pop("validation_errors", None)
            st["paths"]["plan"] = rel
            self.set_status(st, job, "AWAIT_GATE4", f"Scene plan v{st['plan_ver']} is valid. Approve gate 4.")
            return True
        if s == "AWAIT_GATE4":
            dec, fb = self.approval(st, job, 4, st["plan_ver"])
            if dec == "Y":
                self.set_status(st, job, "RENDERING_PREVIEW", "rendering low-res preview")
                return True
            if dec == "N":
                return self._reject_plan(job, st, 4, fb)
            return False
        if s == "RENDERING_PREVIEW":
            return self._render_stage(job, st, wd, "preview", "output/previews",
                                      f"{jid}_preview_v{st['plan_ver']}.mp4", "AWAIT_GATE5",
                                      "Preview uploaded. Watch it and approve gate 5.")
        if s == "AWAIT_LOOK":
            from . import protocol
            fc = st.get("frame_check") or {}
            dec, fb = self.approval(st, job, protocol.LOOK_GATE, st.get("look_rev", st["plan_ver"]))
            if dec == "Y" and f"sha={fc.get('sha')}" in fb:
                self.set_status(st, job, st.get("after_look", "AWAIT_GATE5"), "Claude looked at the frames: " + fb.split("saw:", 1)[-1].strip()[:160])
                return True
            return False
        if s == "AWAIT_GATE5":
            dec, fb = self.approval(st, job, 5, st["plan_ver"])
            if dec == "Y":
                try:
                    kind = (self.storage.read_json(st["paths"]["plan"]).get("protocol") or {}).get("kind")
                except Exception:  # noqa: BLE001
                    kind = None
                if kind == "sample":
                    st["sample_ok"] = True
                    self.set_status(st, job, "SAMPLE_OK", "Sample approved. Send the FULL plan as a new job with protocol.sample_job = " + jid)
                    return False
                self.set_status(st, job, "RENDERING_FINAL", "rendering 4K master")
                return True
            if dec == "N":
                return self._reject_plan(job, st, 5, fb)
            return False
        if s == "RENDERING_FINAL":
            return self._render_stage(job, st, wd, "final", "output/previews",
                                      f"{jid}_final-candidate_v{st['plan_ver']}.mp4", "AWAIT_GATE6",
                                      "4K candidate uploaded to output/previews. Approve gate 6 to publish.")
        if s == "AWAIT_GATE6":
            dec, fb = self.approval(st, job, 6, st["plan_ver"])
            if dec == "Y":
                try:
                    src = st["paths"]["final_candidate"]
                    dst = self.storage.copy_within(src, f"output/final-4k/{jid}_v{st['plan_ver']}.mp4")
                    st["output_link"] = dst
                    self.set_status(st, job, "DONE", f"Final saved: {dst}")
                except Exception as e:  # noqa: BLE001
                    return self.failed(st, job, "publish", e)
                return False
            if dec == "N":
                return self._reject_plan(job, st, 6, fb)
            return False
        return False

    def _reject_plan(self, job, st, gate, fb):
        st["plan_ver"] += 1
        self.set_status(st, job, "AWAIT_PLAN",
                        f"Gate {gate} rejected: {fb}. Waiting for plan {self._plan_rel(job, st)}")
        return True

    def _plan_dnas(self, plan):
        """DNA files the plan was made from (plan.dna.editing / sound = Drive path of a dna-vN.json or corpus)."""
        out = {}
        for t, rel in (plan.get("dna") or {}).items():
            if t in ("editing", "sound") and isinstance(rel, str) and self.storage.exists(rel):
                try:
                    out[t] = self.storage.read_json(rel)
                except Exception:  # noqa: BLE001
                    pass
        return out

    def _render_stage(self, job, st, wd, quality, folder, fname, next_status, note):
        try:
            plan = self.storage.read_json(st["paths"]["plan"])
            out = wd / fname
            from .common import stage as _stage, stage_times as _stage_times
            with _stage(f"render_{quality}"):
                chk = render_mod.render_plan(plan, quality, out, storage=self.storage)
            if not chk["ok"]:
                raise RuntimeError("output check failed: " + "; ".join(chk["problems"]))
            dnas = self._plan_dnas(plan)
            fin = {"grade": chk.get("grade")} if chk.get("grade") else {}
            tl = finish_mod.target_lufs(plan, dnas) if quality == "final" else None
            if tl is not None and chk["probe"].get("has_audio"):
                fin["loudness"] = finish_mod.normalize_loudness(out, tl, wd)
            from . import qa as qa_mod
            fin["qa"] = qa_mod.run(out, plan, wd, tl, check_loudness=(quality == "final"))
            fin["safe_zone"] = chk.get("safe_zone")
            fin["effects"] = chk.get("effects")
            note += f" | QA {fin['qa']['warnings']} warning(s)"
            if quality == "final":
                try:
                    from .cover import make_cover
                    cov = make_cover(out, wd / (Path(fname).stem + "_cover.jpg"))
                    fin["cover"] = {k: cov[k] for k in ("t", "score")}
                    self.storage.put_file(cov["file"], f"{folder}/{Path(fname).stem}_cover.jpg")
                except Exception as e:  # noqa: BLE001
                    fin["cover"] = {"error": f"{type(e).__name__}: {e}"[:150]}
            if chk.get("grade"):
                from .grade_video import summary_line
                note += " | " + summary_line(chk["grade"])
            if dnas or fin:
                if dnas:
                    fin["clone_check"] = finish_mod.clone_check(out, plan, dnas, wd)
                rel_report = self.storage.put_json(f"{folder}/{Path(fname).stem}_clone_report.json", fin)
                st["clone_report"] = rel_report
            if dnas:
                st["clone_ok"] = all(v.get("pass") for k, v in fin["clone_check"].items() if isinstance(v, dict) and "pass" in v)
            try:  # cost/time ledger (never blocks the job)
                from . import costs
                pr_ = chk.get("probe", {})
                costs.record(self.storage, job["id"], f"render_{quality}", stages=_stage_times(reset=True),
                             media={"duration_s": pr_.get("duration_s") or pr_.get("duration"), "width": pr_.get("width"),
                                    "height": pr_.get("height"), "fps": pr_.get("fps")},
                             extra={"output_bytes": out.stat().st_size if out.exists() else None, "quality": quality})
            except Exception:  # noqa: BLE001
                pass
            rel = self.storage.put_file(out, f"{folder}/{fname}")
            fcheck = self._frame_check(job, st, wd, out, quality, folder, fname, chk)
            key = "preview" if quality == "preview" else "final_candidate"
            st["paths"][key] = rel
            st["output_link"] = rel
            st[f"{quality}_check"] = chk["probe"]
            if "clone_ok" in st and dnas:
                note += " | clone check " + ("OK" if st["clone_ok"] else "DIFFERS, see " + st["clone_report"])
            if fcheck is not None and not fcheck["ok"]:     # automatic frame problems: back to the plan, nothing goes to Faiz
                st["validation_errors"] = "frame check failed: " + "; ".join(fcheck["problems"])
                st["plan_ver"] += 1
                self.set_status(st, job, "AWAIT_PLAN", f"Frame check failed ({'; '.join(fcheck['problems'][:2])}). Fix and send plan v{st['plan_ver']}.")
                return True
            if fcheck is not None:
                st["frame_check"] = {k: fcheck[k] for k in ("sha", "collage", "times", "duration_s")}
                st["look_rev"] = st["plan_ver"] * 10 + (1 if quality == "preview" else 2)
                st["after_look"] = next_status
                self.set_status(st, job, "AWAIT_LOOK", note + " | frames ready: Claude must look (./run look-ok)")
                return True
            self.set_status(st, job, next_status, note)
            return True
        except Exception as e:  # noqa: BLE001
            return self.failed(st, job, f"render_{quality}", e)

    def _frame_check(self, job, st, wd, out, quality, folder, fname, chk=None):
        """rulebooks/23 rule 1: frames every ~6 s -> collage in Drive + review branch. Never silently skipped."""
        from . import protocol
        fc = protocol.frame_check(out, Path(wd) / "framecheck", self.lim)
        stem = Path(fname).stem
        try:   # raw | alpha | result of every keyed clip: the real-clip look of the key + grade (rulebooks/23 rule 3)
            from .render import REMOTION_DIR
            n = 0
            for clip in ((chk or {}).get("effects") or {}).get("clips", {}).values():
                img = (clip.get("chroma_key") or {}).get("check_image")
                src = REMOTION_DIR / "public" / "fx" / img if img else None
                if src and src.exists():
                    n += 1
                    shutil.copy2(src, Path(wd) / "framecheck" / f"collage_key_{n}.jpg")
                    self.storage.put_file(src, f"{folder}/{stem}_keycheck{n}.jpg")
        except Exception as e:  # noqa: BLE001
            log(f"key check image not published: {e}")
        try:
            self.storage.put_file(Path(wd) / "framecheck" / fc["collage"], f"{folder}/{stem}_frames.jpg")
        except Exception as e:  # noqa: BLE001
            log(f"frame collage upload to Drive failed: {e}")
        try:
            from .review import publish
            st["review"] = publish(Path(wd) / "framecheck", job["id"], None)
        except Exception as e:  # noqa: BLE001
            st["review"] = {"status": "failed", "error": str(e)[:150]}
        return fc
