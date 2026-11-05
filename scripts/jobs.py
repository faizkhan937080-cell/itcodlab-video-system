"""Job engine: the worker reads jobs from Drive jobs/inbox, runs the machine steps, and STOPS at every
approval gate until a matching approval file (or Approvals-tab row) says Y.

Commands reach the worker as small JSON files in Drive (written by Claude from chat after the user
says so). State lives in Drive jobs/state/<id>.json. Nothing is deleted; inbox files stay forever.
"""
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from . import render as render_mod
from .common import limits, log, now_iso, tail, workdir
from .dna import REQUIRED_TYPES, errors_tail, save_dna, validate

TERMINAL = {"DONE", "FAILED", "NEEDS_INPUT"}


class Worker:
    def __init__(self, storage, sheets=None, work=None):
        self.storage = storage
        self.sheets = sheets
        self.work = Path(work) if work else workdir()
        self.lim = limits()

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
    def _started_today(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        n = 0
        for name in self.storage.list_dir("jobs/state"):
            if name.endswith(".json"):
                try:
                    if self.storage.read_json(f"jobs/state/{name}").get("started", "").startswith(today):
                        n += 1
                except Exception:
                    pass
        return n

    # ------------------------------------------------------------ main loop
    def process_once(self):
        summary = []
        for name in self.storage.list_dir("jobs/inbox"):
            if not name.endswith(".json"):
                continue
            try:
                job = self.storage.read_json(f"jobs/inbox/{name}")
                jid = job["id"]
            except Exception:  # half-written or invalid file: try again next pass
                continue
            st = self.load_state(job)
            if st["status"] in TERMINAL:
                continue
            for _ in range(25):
                if not self.step(job, st):
                    break
            summary.append((jid, st["status"]))
        return summary

    def loop(self, max_minutes=60):
        poll = self.lim["jobs"]["poll_seconds"]
        end = time.time() + max_minutes * 60
        while time.time() < end:
            self.process_once()
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
            if self._started_today() >= self.lim["claude"]["daily_job_cap"] and "started" not in st:
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
                rel = self.storage.put_file(src, f"analysis/{jid}/{src.name}")
                st["paths"]["source_drive"] = rel
                self.set_status(st, job, "ANALYZING", "frame-by-frame analysis running")
                return True
            except Exception as e:  # noqa: BLE001
                return self.failed(st, job, "acquire", e, terminal="NEEDS_INPUT",
                                   terminal_note=("Could not get the video from the link. Put the video file in "
                                                  "Drive input/references/ and send a new job with 'file'."))
        if s == "ANALYZING":
            try:
                from .pack import run_pipeline
                res = run_pipeline(st["paths"]["source_local"], wd / "analysis", job_id=jid, mode=job["mode"])
                self.storage.put_tree(res["out_root"], f"analysis/{jid}")
                st["paths"]["analysis"] = f"analysis/{jid}"
                st["paths"]["pack"] = f"analysis/{jid}/pack"
                st["pack_manifest"] = res["manifest"]
                self.set_status(st, job, "AWAIT_GATE2",
                                f"Analysis ready: {res['manifest']['collage_count']} collage(s) in "
                                f"{st['paths']['pack']}. Look at them and approve gate 2.")
                return True
            except Exception as e:  # noqa: BLE001
                return self.failed(st, job, "analysis", e)
        if s == "AWAIT_GATE2":
            dec, fb = self.approval(st, job, 2, 1)
            if dec == "Y":
                types = REQUIRED_TYPES[job["mode"]]
                self.set_status(st, job, "AWAIT_CANDIDATE",
                                f"Waiting for DNA candidate(s): {', '.join(types)} "
                                f"(file analysis/{jid}/dna/candidate-<type>-v{st['candidate_ver']}.json)")
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
                for t, rel in st["candidates"].items():
                    obj = self.storage.read_json(rel)
                    path, ver = save_dna(self.storage, job["target"], t, obj, jid)
                    saved.append(path)
                    if self.sheets:
                        creator = job["target"].split(":", 1)[1] if ":" in job["target"] else ""
                        self.sheets.add_dna_index(f"{t}-{jid}-v{ver}", "creator" if creator else "general",
                                                  creator, t, ver, path, jid)
                st["dna_saved"] = saved
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
            return self.storage.fetch(job["file"], wd / name)
        import os
        from .common import run_cmd
        cmd = ["yt-dlp", "-f", "bv*+ba/b", "--merge-output-format", "mp4", "--no-playlist",
               "-o", str(wd / "source.%(ext)s")]
        cookies = os.environ.get("ITCOD_COOKIES")
        if cookies and Path(cookies).exists():
            cmd += ["--cookies", cookies]
        rc, out, err = run_cmd(cmd + [job["link"]], timeout=1800)
        if rc != 0:
            raise RuntimeError("yt-dlp failed:\n" + tail(err or out))
        files = sorted(wd.glob("source.*"))
        if not files:
            raise RuntimeError("download finished but no file found")
        return files[0]

    def _check_candidates(self, job, st):
        jid, ver = job["id"], st["candidate_ver"]
        types = REQUIRED_TYPES[job["mode"]]
        found, errors = {}, []
        for t in types:
            rel = f"analysis/{jid}/dna/candidate-{t}-v{ver}.json"
            if not self.storage.exists(rel):
                continue
            try:
                obj = self.storage.read_json(rel)
            except Exception:
                continue  # half written
            errs = validate(t, obj)
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

    def _render_stage(self, job, st, wd, quality, folder, fname, next_status, note):
        try:
            plan = self.storage.read_json(st["paths"]["plan"])
            out = wd / fname
            chk = render_mod.render_plan(plan, quality, out, storage=self.storage)
            if not chk["ok"]:
                raise RuntimeError("output check failed: " + "; ".join(chk["problems"]))
            rel = self.storage.put_file(out, f"{folder}/{fname}")
            key = "preview" if quality == "preview" else "final_candidate"
            st["paths"][key] = rel
            st["output_link"] = rel
            st[f"{quality}_check"] = chk["probe"]
            self.set_status(st, job, next_status, note)
            return True
        except Exception as e:  # noqa: BLE001
            return self.failed(st, job, f"render_{quality}", e)
