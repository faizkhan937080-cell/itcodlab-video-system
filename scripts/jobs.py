"""Job engine: the worker reads jobs from Drive jobs/inbox, runs the machine steps, and STOPS at every
approval gate until a matching approval file (or Approvals-tab row) says Y.

Commands reach the worker as small JSON files in Drive (written by Claude from chat after the user
says so). State lives in Drive jobs/state/<id>.json. Nothing is deleted; inbox files stay forever.
"""
import re
import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from . import finish as finish_mod
from . import render as render_mod
from .common import limits, log, now_iso, tail, workdir
from .dna import REQUIRED_TYPES, errors_tail, save_dna, validate
from .dna_check import check as check_dna

TERMINAL = {"DONE", "FAILED", "NEEDS_INPUT", "MEASURED"}


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
        self.set_status(st, job, "NEEDS_INPUT", f"unknown job type: {job.get('type')}")
        return False

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
                res = run_pipeline(st["paths"]["source_local"], wd / "analysis", job_id=jid, mode=job["mode"])
                from .describe import describe_pack
                idx = json.loads((res["out_root"] / "collage_index.json").read_text(encoding="utf-8"))
                bulk = bool(job.get("bulk"))
                if not bulk:
                    st["describe"] = describe_pack(res["pack"], idx)
                    from .review import publish
                    st["review"] = publish(res["pack"], jid, idx)
                    st["review"]["tried"] = now_iso()
                self._write_measured_drafts(res, job, st)
                base = self._analysis_rel(st, job)
                self.storage.put_tree(res["out_root"], base)
                st["paths"]["analysis"] = base
                st["paths"]["pack"] = f"{base}/pack"
                st["pack_manifest"] = res["manifest"]
                if bulk:
                    self.set_status(st, job, "MEASURED", f"measured only (batch {job.get('batch', '-')}); "
                                    f"drafts in {base}/dna/measured-<type>.json")
                    self._maybe_corpus(job, st)
                    return False
                if job["mode"] == "audio" and self._audio_data_complete(res["pack"]):
                    types = REQUIRED_TYPES["audio"]  # no collages to judge: sound + scripting go straight to DNA drafting
                    self.set_status(st, job, "AWAIT_CANDIDATE",
                                    f"Audio data complete (gate 2 not needed). Waiting for DNA candidate(s): {', '.join(types)} "
                                    f"(file {base}/dna/candidate-<type>-v{st['candidate_ver']}.json)")
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
                                f"(file {self._analysis_rel(st, job)}/dna/candidate-<type>-v{st['candidate_ver']}.json)")
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
                        rel = f"{self._analysis_rel(st, job)}/dna/{rel.rsplit('/', 1)[-1]}"
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
        """Everything of a creator lives in ONE folder: creators/<h>/videos/<job>.
        Jobs started before this layout keep the path stored in their state (followed if the folder was moved)."""
        p = (st.get("paths") or {}).get("analysis")
        t = st.get("target") or job.get("target", "general")
        is_creator = t.startswith("creator:") and t != "creator:auto"
        if p:
            if not self.storage.exists(p) and is_creator:
                h = t.split(":", 1)[1]
                for alt in (f"creators/{h}/videos/{self._reel_code(job)}", f"creators/{h}/videos/{job['id']}",
                            f"analysis/creators/{h}/{job['id']}"):
                    if self.storage.exists(alt):  # folder was moved into the creator's folder: follow it
                        st["paths"]["analysis"] = alt
                        st["paths"]["pack"] = f"{alt}/pack"
                        return alt
            return p
        if is_creator:
            return f"creators/{t.split(':', 1)[1]}/videos/{self._reel_code(job)}"
        return f"analysis/general/{self._reel_code(job)}"

    def _make_creator_folders(self, st):
        t = st.get("target", "")
        if t.startswith("creator:") and t != "creator:auto":
            h = t.split(":", 1)[1]
            for sub in ("videos", "dna", "style", "ideas", "scripts", "made"):
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
            (res["out_root"] / "dna").mkdir(parents=True, exist_ok=True)
            (res["out_root"] / "dna" / f"measured-{t}.json").write_text(
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
                rel = f"{sj['paths'].get('analysis')}/dna/measured-{t}.json"
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
        try:
            return self.storage.read_json(f"{self._analysis_rel(st, job)}/pack/metrics_summary.json")
        except Exception:  # noqa: BLE001
            return None

    def _check_candidates(self, job, st):
        jid, ver = job["id"], st["candidate_ver"]
        types = REQUIRED_TYPES[job["mode"]]
        found, errors = {}, []
        for t in types:
            rel = f"{self._analysis_rel(st, job)}/dna/candidate-{t}-v{ver}.json"
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
            errs = validate("scene", plan)
            if errs:
                st["validation_errors"] = errors_tail(errs)
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
        if s == "AWAIT_GATE5":
            dec, fb = self.approval(st, job, 5, st["plan_ver"])
            if dec == "Y":
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
            rel = self.storage.put_file(out, f"{folder}/{fname}")
            key = "preview" if quality == "preview" else "final_candidate"
            st["paths"][key] = rel
            st["output_link"] = rel
            st[f"{quality}_check"] = chk["probe"]
            if "clone_ok" in st and dnas:
                note += " | clone check " + ("OK" if st["clone_ok"] else "DIFFERS, see " + st["clone_report"])
            self.set_status(st, job, next_status, note)
            return True
        except Exception as e:  # noqa: BLE001
            return self.failed(st, job, f"render_{quality}", e)
