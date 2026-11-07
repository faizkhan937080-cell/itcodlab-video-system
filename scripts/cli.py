"""Command line for ./run. Each subcommand is small; the logic lives in the other modules."""
import argparse
import json
import sys
from pathlib import Path


def _storage():
    from .storage import Storage
    return Storage()


def cmd_doctor(a):
    from .doctor import run
    return run()


def cmd_selftest(a):
    import subprocess
    from .common import ROOT
    return subprocess.call([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")] + a.extra)


def cmd_analyze_local(a):
    from .pack import run_pipeline
    res = run_pipeline(a.video, a.out, job_id=a.job_id, mode=a.mode, with_transcript=not a.no_transcript)
    print(json.dumps(res["manifest"], indent=2))
    return 0


def cmd_validate(a):
    from .dna import errors_tail, validate
    obj = json.loads(Path(a.file).read_text(encoding="utf-8"))
    errs = validate(a.schema, obj)
    print("VALID" if not errs else "INVALID\n" + errors_tail(errs))
    return 0 if not errs else 1


def cmd_dna_check(a):
    from .dna_check import check
    obj = json.loads(Path(a.file).read_text(encoding="utf-8"))
    summary = json.loads(Path(a.summary).read_text(encoding="utf-8")) if a.summary else None
    probs = check(a.type, obj, summary)
    print("PASS" + ("" if summary else " (schema+honesty only; give --summary to cross-check numbers)")
          if not probs else "FAIL\n" + "\n".join(probs[:20]))
    return 0 if not probs else 1


def cmd_dna_draft(a):
    from .dna_draft import DRAFTERS
    sm = json.loads(Path(a.summary).read_text(encoding="utf-8"))
    d = DRAFTERS[a.type](sm, a.job, a.link or "", a.creator or "")
    Path(a.out).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"measured part of {a.type} DNA written to {a.out}. Claude adds the judged sections, then ./run dna-check.")
    return 0


def cmd_clone_report(a):
    from .dna_check import clone_report
    tgt = json.loads(Path(a.target).read_text(encoding="utf-8"))
    out = json.loads(Path(a.summary).read_text(encoding="utf-8"))
    r = clone_report(a.type, tgt, out)
    print("CLONE OK" if r["pass"] else "CLONE DIFFERS\n" + "\n".join(r["differences"][:20]))
    return 0 if r["pass"] else 1


def cmd_corpus(a):
    from .dna import errors_tail, validate
    from .dna_corpus import aggregate
    dnas = [json.loads(Path(f).read_text(encoding="utf-8")) for f in a.files]
    out = aggregate(a.type, a.creator, dnas)
    errs = validate("corpus", out)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"corpus of {out['n_videos']} video(s): {len(out['signature'])} signature, "
          f"{len(out['situational'])} situational, provisional={out['provisional']}"
          + ("" if not errs else "\nINVALID\n" + errors_tail(errs)))
    return 0 if not errs else 1


def cmd_render_local(a):
    from .render import render_plan
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    res = render_plan(plan, a.quality, a.out)
    if res.get("ok"):
        # Loophole fix (2026-11-07): the mix came out at -20.7 LUFS because render-local skipped the loudness step
        # that jobs.py runs. Every final render gets the same -14 LUFS pass here.
        import tempfile
        from . import finish as finish_mod
        with tempfile.TemporaryDirectory(prefix="itcod-norm-") as wd:
            res["loudness"] = finish_mod.normalize_loudness(a.out, -14.0, Path(wd))
    print(json.dumps(res, indent=2, default=str))
    return 0 if res.get("ok") else 1


def cmd_check(a):
    from .habits import survey
    rows = survey()
    for r in rows:
        print("CHECK " + r)
    if not rows and not a.quiet:
        print("check: OK")
    return 0


def cmd_test(a):
    from .habits import run_tests
    return run_tests(a.files)


def cmd_guard_install(a):
    from .habits import install_global_hook
    ch = install_global_hook()
    print("guard hooks installed globally: " + (", ".join(ch) if ch else "already present"))
    return 0


def cmd_voice(a):
    from . import voice_providers as vp
    try:
        if a.what == "list":
            for k, v in vp.registry().items():
                ok = (v.get("consent") or {}).get("verified") if v.get("kind") == "clone" else "stock"
                print(f"{k}: {v['provider']} {v.get('kind')} {v.get('person')} consent={ok}")
        elif a.what == "register":
            vp.register(a.id, a.provider, a.person, a.kind, a.voice, a.remote_id, a.ref_audio, a.consent_doc, expires=a.expires)
            print(f"registered {a.id} (clone stays locked until: ./run voice verify {a.id})")
        elif a.what == "verify":
            vp.verify(a.id)
            print(f"{a.id}: consent verified")
    except vp.ConsentError as e:
        print("CONSENT: " + str(e))
        return 1
    return 0


def cmd_voice_run(a):
    """Worker side of a voice job: synth a script file (secrets from env), upload wav + timings to Drive output/voice/<name>/."""
    import tempfile
    from . import costs, tts
    from .common import stage, to_native
    script = json.loads(Path(a.script).read_text(encoding="utf-8"))
    name = a.name or Path(a.script).stem
    with tempfile.TemporaryDirectory(prefix="itcod-voice-") as wd:
        wav, js = Path(wd) / f"{name}.wav", Path(wd) / f"{name}.json"
        with stage("tts"):
            res = tts.synth(script, wav, js)
        costs.add("tts", calls=len(script["segments"]), audio_s=res["duration_s"], words=res["words"], chars=res.get("chars", 0), engine=res["engine"])
        if a.no_upload:   # test runs: nothing goes to Drive (rule: tests never save)
            print(json.dumps(to_native({k: v for k, v in res.items() if k != "segments"}), ensure_ascii=False))
            print("test run: not uploaded")
            return 0
        stg = _storage()
        rel = f"output/voice/{name}"
        stg.ensure_dir(rel)
        stg.put_file(wav, f"{rel}/{name}.wav")
        stg.put_file(js, f"{rel}/{name}.json")
    print(json.dumps(to_native({k: v for k, v in res.items() if k != "segments"}), ensure_ascii=False))
    print(f"uploaded to Drive {rel}")
    return 0


def cmd_worker(a):
    from .jobs import Worker
    from .sheets import SheetsClient
    sheets = None if a.no_sheet else SheetsClient()
    w = Worker(_storage(), sheets)
    if a.until_idle:
        for jid, status in w.run_until_idle(max_minutes=a.max_minutes, grace_s=a.grace):
            print(f"{jid}: {status}")
    elif a.loop:
        w.loop(max_minutes=a.max_minutes)
    else:
        for jid, status in w.process_once():
            print(f"{jid}: {status}")
    return 0


def cmd_wake(a):
    """Claude's doorbell: push a tiny file under trigger/ so the GitHub Actions worker starts now."""
    from .common import ROOT, now_iso, run_cmd
    f = ROOT / "trigger" / "wake.txt"
    f.parent.mkdir(exist_ok=True)
    reason = a.reason + (" [turbo]" if getattr(a, "turbo", False) else "")
    f.write_text(f"{now_iso()} {reason}\n", encoding="utf-8")
    run_cmd(["git", "-C", str(ROOT), "add", "trigger/wake.txt"])
    rc, out, err = run_cmd(["git", "-C", str(ROOT), "commit", "-q", "-m", f"wake worker: {reason}"])
    if rc != 0:
        print("nothing to commit: " + (err or out)[-200:])
        return 1
    rc, out, err = run_cmd(["git", "-C", str(ROOT), "push", "-q", "origin", "HEAD:main"], timeout=120)
    print("worker woken (GitHub Actions starts in ~10 s)" if rc == 0 else "push failed: " + err[-300:])
    return 0 if rc == 0 else 1


def cmd_bulk_jobs(a):
    """Many reels of one creator: one job file per link, measured only. Needs ONE Y from Faiz for the whole batch."""
    from .common import now_iso
    from .dna import errors_tail, validate
    links = [x.strip() for x in Path(a.links_file).read_text(encoding="utf-8").splitlines() if x.strip()]
    st = _storage()
    made = []
    for i, link in enumerate(links, 1):
        job = {"id": f"{a.batch}-{i:03d}", "type": "analyze", "created": now_iso(), "link": link, "mode": a.mode,
               "target": f"creator:{a.creator}", "gate1_approved_by_user": True, "bulk": True, "batch": a.batch,
               "batch_size": len(links)}
        errs = validate("job", job)
        if errs:
            print("INVALID\n" + errors_tail(errs))
            return 1
        st.put_json(f"jobs/inbox/{job['id']}.json", job)
        made.append(job["id"])
    print(f"{len(made)} bulk job(s) queued for creator {a.creator}: {made[0]} .. {made[-1]}")
    return 0


def cmd_status(a):
    st = _storage()
    names = [n for n in st.list_dir("jobs/state") if n.endswith(".json")]
    if a.job:
        names = [f"{a.job}.json"] if f"{a.job}.json" in names else []
    if not names:
        print("no jobs")
        return 0
    for n in names:
        s = st.read_json(f"jobs/state/{n}")
        print(f"{s['id']:30} {s['status']:18} {s.get('note', '')[:110]}")
    return 0


def cmd_new_job(a):
    """Write a job file to Drive jobs/inbox (normally Claude does this from chat)."""
    from .dna import errors_tail, validate
    from .common import now_iso
    from . import reelid
    job = {"id": a.id, "type": a.type, "created": now_iso(), "command_text": a.command_text or ""}
    if a.type == "analyze":
        job.update({"mode": a.mode, "target": a.target, "gate1_approved_by_user": True})
        if a.link:
            code = reelid.shortcode(a.link)
            job["link"] = reelid.canonical(a.link)
            if code:  # one reel = one ID = one folder
                where = reelid.find_reel(_storage(), code)
                if where and not a.rerun:
                    print(f"ALREADY ANALYSED: {where}. Use the existing folder (or --rerun to make a new run).")
                    return 1
                try:
                    job["id"] = reelid.new_job_id(_storage(), code)
                except ValueError as e:
                    print(f"REFUSED: {e}")
                    return 1
                job["reel_id"] = code
        if a.file:
            job["file"] = a.file
    errs = validate("job", job)
    if errs:
        print("INVALID\n" + errors_tail(errs))
        return 1
    print(_storage().put_json(f"jobs/inbox/{job['id']}.json", job))
    return 0


def cmd_approve(a):
    """Write an approval file (normally Claude does this from chat after the user's clear Y/N)."""
    from .common import now_iso
    rel = f"jobs/approvals/{a.job}__gate{a.gate}__r{a.rev}.json"
    print(_storage().put_json(rel, {"job": a.job, "gate": a.gate, "rev": a.rev, "decision": a.decision.upper(),
                                    "feedback": a.feedback or "", "by": "user", "ts": now_iso()}))
    return 0


def cmd_mem(a):
    from . import mem
    if a.action == "brief":
        print(mem.brief())
    elif a.action == "index":
        print("\n".join(mem.build_index()))
    elif a.action == "find":
        hits = mem.find(a.words)
        print("\n".join(hits) if hits else "no match")
    elif a.action == "add":
        if len(a.words) < 2:
            print("usage: mem add <shard> <text..>")
            return 1
        p = mem.add(a.words[0], " ".join(a.words[1:]), keys=a.keys or "")
        mem.build_index()
        print(f"added to {p.relative_to(mem.ROOT)}")
    return 0


def cmd_sfx(a):
    """Add sound effects to a scene plan: Openverse (commercial licences only) -> number check -> plan.audio."""
    import os
    from . import sfx
    plan_path = Path(a.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    res = sfx.fetch_all(plan, a.assets_dir, token=os.environ.get("OPENVERSE_TOKEN"))
    cues = sfx.plan_cues(plan)
    if not a.dry_run:
        plan["audio"] = [x for x in plan.get("audio", []) if not str(x.get("src", "")).startswith("assets/sfx/")]
        plan["audio"] += sfx.audio_defs(cues, res["files"])
        if getattr(a, "meme_fx", False):
            print(f"meme fx added: {sfx.fx_for_cues(plan, cues)}")
        plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
        if res["credits"]:
            (plan_path.parent / "sfx_credits.json").write_text(json.dumps(res["credits"], indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"cues": len(cues), "files": res["files"], "credits": len(res["credits"]), "skipped": res["skipped"]}, indent=2))
    return 0


def cmd_library(a):
    """Asset library: scan (index files Faiz dropped in), add (free item with licence), find, list."""
    from . import library
    st = _storage()
    if a.action == "scan":
        res = library.scan(st)
        print(json.dumps({"new": [r["id"] for r in res]}, indent=2))
    elif a.action == "fetch":
        import os
        e = library.fetch_from_openverse(st, a.word, a.type or "sfx", a.name, [t for t in (a.tags or "").split(",") if t],
                                         token=os.environ.get("OPENVERSE_TOKEN"))
        print(json.dumps(e, indent=2, ensure_ascii=False) if e else "NOTHING USABLE (no cc0/pdm/by match within limits)")
        return 0 if e else 1
    elif a.action == "add":
        print(json.dumps(library.add_entry(st, a.type, a.name, a.licence, a.source, a.file, a.credit,
                                           [t for t in (a.tags or "").split(",") if t], accept_risk=a.accept_risk), indent=2, ensure_ascii=False))
    else:
        items = library.find(st, a.word, a.type) if a.action == "find" else library.load(st)
        print("\n".join(f"{i['id']} | {i['licence']} | {i.get('file') or i.get('source')}" for i in items) or "empty")
    return 0


def cmd_resolve(a):
    """Which named elements of this reel's recipe are in the library, which must be fetched/licensed."""
    from . import clients, resolve
    st = _storage()
    reel, folder = clients.find_reel_json(st, a.reel)
    card = st.read_json(f"{folder}/recipe.json")
    res = resolve.resolve(st, card)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


def cmd_ext_index(a):
    """Index a company's shared Drive folder (no copy). --check only lists the top level to test access."""
    import os
    from . import extdrive
    st = _storage()
    fid = extdrive.folder_id(a.link)
    remote = st.remote or os.environ.get("ITCOD_RCLONE_REMOTE", "gdrive")
    if a.check:
        top = extdrive.list_folder(remote, fid, depth=1)
        print(f"ACCESS OK: {len(top)} top-level entries: " + ", ".join(x["Path"] for x in top[:15]))
        return 0
    idx = extdrive.build_index(extdrive.list_folder(remote, fid), a.company, fid, a.licence_note or "")
    base = extdrive.write_index(st, idx)
    print(f"indexed {idx['count']} files ({idx['by_type']}) -> {base}/INDEX.json; exact duplicates skipped: {len(idx['exact_duplicates'])}")
    return 0


def cmd_snapshot(a):
    from . import snapshot
    p = snapshot.write_local(_storage(), a.out)
    print(f"manifest written: {p} ({p.stat().st_size} bytes)")
    return 0


def cmd_kaggle_compare(a):
    """Same wav on CPU and on the free Kaggle GPU: prints equality + seconds. The GPU path stays OFF until identical=true.
    `--job <id>` (worker): pulls the job's own Drive copy of the reel, extracts the audio and saves the report to Drive costs/compare/."""
    import os
    import tempfile
    import time
    from . import audio, kaggle_gpu
    os.environ.pop("ITCOD_KAGGLE_GPU", None)
    stg, wav, tmp = None, a.wav, None
    if a.job:
        stg = _storage()
        st = stg.read_json(f"jobs/state/{a.job}.json")
        rel = (st.get("paths") or {}).get("source_drive")
        if not rel:
            print(json.dumps({"ok": False, "why": "job has no source_drive"}))
            return 1
        tmp = tempfile.mkdtemp(prefix="itcod-kc-")
        src = stg.fetch(rel, Path(tmp) / ("source" + (Path(rel).suffix or ".mp4")))
        wav = str(audio.extract_wav(src, Path(tmp) / "ears.wav"))
    if not wav:
        print(json.dumps({"ok": False, "why": "give a wav or --job"}))
        return 1
    t = time.time()
    cpu = audio.transcribe(wav)
    cpu_s = round(time.time() - t, 1)
    t = time.time()
    gpu = kaggle_gpu.transcribe(wav)
    gpu_s = round(time.time() - t, 1)
    if not gpu:
        rep = {"ok": False, "why": "gpu path returned nothing (see log lines above)", "cpu_s": cpu_s}
        code = 1
    else:
        rep = {"ok": True, "cpu_s": cpu_s, "gpu_s": gpu_s, **kaggle_gpu.compare(cpu, gpu)}
        code = 0 if rep["identical"] else 2
    print(json.dumps(rep, ensure_ascii=False))
    if stg is not None:
        try:
            stg.put_json(f"costs/compare/{a.job}__kaggle__{time.strftime('%Y%m%dT%H%M%S')}.json", {"job": a.job, **rep})
        except Exception as e:  # noqa: BLE001
            print("report not saved: " + type(e).__name__)
    return code


def cmd_qa_sheet(a):
    """Frames of our own render at given times, in one image (QA)."""
    from .render import contact_sheet
    times = [float(x) for x in a.times.split(",") if x.strip()]
    print(contact_sheet(a.video, times, a.out, cols=a.cols))
    return 0


def cmd_tts(a):
    """Voiceover from a script JSON (Kokoro, free). Writes the wav + timings JSON; measured like every step."""
    from . import costs, tts
    from .common import to_native
    script = json.loads(Path(a.script).read_text(encoding="utf-8"))
    from .common import stage
    with stage("tts"):
        res = tts.synth(script, a.out_wav, a.out_json)
    costs.add("tts", calls=len(script["segments"]), audio_s=res["duration_s"], words=res["words"], chars=res.get("chars", 0), engine=res["engine"])
    print(json.dumps(to_native({k: v for k, v in res.items() if k != "segments"}), ensure_ascii=False))
    return 0


def cmd_cost(a):
    """Time + money data. report = totals and free quota left; estimate = predict a reel; claude = log Claude tokens for a job."""
    from . import costs
    try:
        stg = _storage()
    except Exception:  # noqa: BLE001
        stg = None
    if a.what == "claude":
        costs.add("claude", model=a.model, in_tok=a.tin, out_tok=a.tout, calls=1, estimated=True)
        p = costs.record(stg, a.job, "claude", stages={}, extra={"note": a.note or "tokens are Claude's own estimate"})
        print("saved: " + str(p))
        return 0
    rows = costs.load_rows(stg)
    if a.what == "report":
        print(json.dumps(costs.report(rows), ensure_ascii=False, indent=1))
        return 0
    out = costs.estimate(rows, a.seconds, kind=a.kind, machine_name=a.machine)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["ok"] else 1


def cmd_security(a):
    from . import security
    if a.baseline:
        d = security.write_baseline()
        print(f"baseline written for {len(d)} critical file(s)")
        return 0
    r = security.report()
    print(f"SECURITY {r['verdict']}")
    for k in ("secrets", "workflows", "integrity"):
        for x in r[k]:
            print(f"  [{k}] {x}")
    if a.net:
        from .netguard import guard
        try:
            guard().attach(_storage())
        except Exception as e:  # noqa: BLE001
            print(f"  [net] could not read the shared ledger: {type(e).__name__}")
        for host, v in guard().status().items():
            print(f"  [net] {host}: today {v['today']}, strikes {v['strikes']}, {'BLOCKED' if v['blocked'] else 'ok'}{' - ' + str(v['reason']) if v['reason'] else ''}")
    return 1 if r["verdict"] == "FAIL" and a.strict else 0


def cmd_vet(a):
    from . import security
    v = security.vet_file(a.file, a.kind)
    print(json.dumps(v))
    return 0 if v["ok"] else 1


def cmd_audit_links(a):
    from . import linkcheck
    issues = linkcheck.run(_storage())
    print("\n".join(issues) if issues else "OK: no broken links, duplicates or orphans")
    return 1 if issues else 0


def cmd_clients(a):
    """clients init <company> | made-from <company> <video> <reel> | gate <company> <video>"""
    from . import clients
    st = _storage()
    if a.action == "init":
        print(clients.init_company(st, a.company))
    elif a.action == "made-from":
        base, mf = clients.write_made_from(st, a.company, a.video, a.reel)
        print(base, "pinned", len(mf["dna_pinned"]), "DNA files")
    else:
        base = f"clients/{clients._slug(a.company)}/videos/{clients._slug(a.video)}"
        credits = st.read_json(f"{base}/credits.json")
        if getattr(a, "accept_risk", None):
            credits, marked = clients.accept_risk(credits, a.accept_risk)
            st.put_json(f"{base}/credits.json", credits)
            print("RISK ACCEPTED by Faiz (" + a.accept_risk + "): " + (", ".join(marked) or "nothing needed it"))
            return 0
        bad = clients.licence_blockers(credits)
        print("ALERT (Faiz decides, rulebook 18): licence not cleared for commercial use: " + ", ".join(bad) if bad
              else "OK: all licences commercial-ok or risk accepted")
        return 1 if bad else 0
    return 0


def cmd_story(a):
    """'Kahani update': rebuild the memory index, check the 60-line rule, then save everything to GitHub so a lost
    sandbox never loses the story. Claude runs it when Faiz says "kahani update" and on its own after work chats."""
    from . import mem
    from .common import ROOT, now_iso, run_cmd
    mem.build_index()
    over = []
    for d in ("memory", "lessons", "rulebooks"):
        for f in sorted((ROOT / d).rglob("*.md")):
            n = len(f.read_text(encoding="utf-8").splitlines())
            if n > 60:
                over.append(f"{f.relative_to(ROOT)} ({n} lines)")
    state = (ROOT / "memory" / "state.md").read_text(encoding="utf-8").splitlines()
    upd = next((x for x in state if x.startswith("updated:")), "updated: ?")
    print(f"state.md {upd}")
    if over:
        print("TOO LONG (split or roll): " + ", ".join(over))
    paths = ["memory", "lessons", "rulebooks", "CLAUDE.md", "config"]
    run_cmd(["git", "-C", str(ROOT), "add", *paths])
    rc, out, err = run_cmd(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"])
    if rc == 0:
        print("story already saved (nothing new)")
        return 1 if over else 0
    rc, out, err = run_cmd(["git", "-C", str(ROOT), "commit", "-q", "-m", f"story update {now_iso()}"])
    if rc != 0:
        print("commit failed: " + (err or out)[-200:])
        return 1
    rc, out, err = run_cmd(["git", "-C", str(ROOT), "push", "-q", "origin", "HEAD:main"], timeout=120)
    print("story saved to GitHub" if rc == 0 else "push failed: " + err[-300:])
    return 0 if rc == 0 and not over else 1


def cmd_review_fetch(a):
    from .review import fetch
    for f in fetch(a.job, a.out):
        print(f)
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="run", description="itcodlab video system")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("mem", help="project memory: brief | find | add | index")
    s.add_argument("action", choices=["brief", "find", "add", "index"])
    s.add_argument("words", nargs="*")
    s.add_argument("--keys", default="")
    s.set_defaults(fn=cmd_mem)

    s = sub.add_parser("sfx", help="add SFX to a scene plan (Openverse, commercial licences only, number-checked)")
    s.add_argument("--plan", required=True)
    s.add_argument("--assets-dir", required=True, help="folder that becomes assets/sfx for the render")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--meme-fx", action="store_true", help="also add picture effects (zoom-punch, shake, flash, RGB split) on the hit/whoosh cues")
    s.set_defaults(fn=cmd_sfx)
    s = sub.add_parser("resolve", help="clone by name: recipe elements -> library found / missing")
    s.add_argument("reel")
    s.set_defaults(fn=cmd_resolve)
    s = sub.add_parser("ext-index", help="index a company's shared Drive folder (no copy)")
    s.add_argument("--company", required=True)
    s.add_argument("--link", required=True)
    s.add_argument("--licence-note", default="")
    s.add_argument("--check", action="store_true", help="only test that the folder can be read")
    s.set_defaults(fn=cmd_ext_index)
    s = sub.add_parser("snapshot", help="text manifest of what is in Drive (goes to GitHub)")
    s.add_argument("--out", default="docs/snapshots/drive-manifest.json")
    s.set_defaults(fn=cmd_snapshot)
    s = sub.add_parser("kaggle-compare", help="prove the Kaggle GPU transcript equals the CPU one on the same wav")
    s.add_argument("wav", nargs="?", default="")
    s.add_argument("--job", default="", help="worker mode: use this job's Drive copy and save the report to Drive costs/compare/")
    s.set_defaults(fn=cmd_kaggle_compare)

    s = sub.add_parser("qa-sheet", help="frames of our own render at given times in one image (QA)")
    s.add_argument("video")
    s.add_argument("--times", required=True, help="comma-separated seconds")
    s.add_argument("--out", required=True)
    s.add_argument("--cols", type=int, default=4)
    s.set_defaults(fn=cmd_qa_sheet)

    s = sub.add_parser("tts", help="voiceover from a script JSON (Kokoro, free, CPU): wav + segment timings")
    s.add_argument("script")
    s.add_argument("--out-wav", required=True)
    s.add_argument("--out-json", required=True)
    s.set_defaults(fn=cmd_tts)

    s = sub.add_parser("cost", help="time + cost data: report | estimate --seconds N | claude --job J --model M --tin N --tout N")
    s.add_argument("what", choices=["report", "estimate", "claude"])
    s.add_argument("--seconds", type=float, default=60.0, help="reel length for estimate")
    s.add_argument("--kind", default="analysis", help="analysis | render_preview | render_final")
    s.add_argument("--machine", default=None, help="github-ubuntu-2core | gcp-gpu-vm | local")
    s.add_argument("--job", default="session")
    s.add_argument("--model", default="sonnet-5.5")
    s.add_argument("--tin", type=int, default=0)
    s.add_argument("--tout", type=int, default=0)
    s.add_argument("--note", default="")
    s.set_defaults(fn=cmd_cost)

    s = sub.add_parser("security", help="secrets, workflows, guard-file integrity (+ --net: per-host counters and cooldowns)")
    s.add_argument("--baseline", action="store_true", help="renew the integrity baseline AFTER checking the change")
    s.add_argument("--net", action="store_true")
    s.add_argument("--strict", action="store_true", help="exit 1 on FAIL (CI)")
    s.set_defaults(fn=cmd_security)
    s = sub.add_parser("vet", help="safety-check one incoming file (type, size, virus scan)")
    s.add_argument("file")
    s.add_argument("kind", choices=["video", "audio", "image", "font", "pdf", "model", "other"])
    s.set_defaults(fn=cmd_vet)
    s = sub.add_parser("audit-links", help="find orphans, duplicates, broken links (read-only)")
    s.set_defaults(fn=cmd_audit_links)
    s = sub.add_parser("clients", help="company folders: init | made-from | gate")
    s.add_argument("action", choices=["init", "made-from", "gate"])
    s.add_argument("company")
    s.add_argument("video", nargs="?", default="")
    s.add_argument("reel", nargs="?", default="")
    s.add_argument("--accept-risk", default=None, help="gate only: Faiz's words; marks items as risk accepted and passes")
    s.set_defaults(fn=cmd_clients)
    s = sub.add_parser("library", help="asset library: scan | add | find | list")
    s.add_argument("action", choices=["scan", "add", "fetch", "find", "list"])
    s.add_argument("word", nargs="?", default="")
    s.add_argument("--type", default=None)
    s.add_argument("--name"); s.add_argument("--licence"); s.add_argument("--source", default="")
    s.add_argument("--file", default=None); s.add_argument("--credit", default=""); s.add_argument("--tags", default="")
    s.add_argument("--accept-risk", default=None, help="Faiz's words: add an item whose licence is not cleared for commercial use anyway")
    s.set_defaults(fn=cmd_library)
    s = sub.add_parser("story", help="kahani update: index + 60-line check + save memory/rules to GitHub")
    s.set_defaults(fn=cmd_story)

    s = sub.add_parser("review-fetch", help="Claude: pull collages of a job from the review branch")
    s.add_argument("job")
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_review_fetch)

    s = sub.add_parser("doctor", help="check tools and libraries")
    s.set_defaults(fn=cmd_doctor)

    s = sub.add_parser("selftest", help="run the automatic tests")
    s.add_argument("extra", nargs="*")
    s.set_defaults(fn=cmd_selftest)

    s = sub.add_parser("analyze-local", help="analyse a local video file (no Drive, no gates)")
    s.add_argument("--video", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--job-id", default="local")
    s.add_argument("--mode", choices=["video", "audio", "both"], default="both")
    s.add_argument("--no-transcript", action="store_true")
    s.set_defaults(fn=cmd_analyze_local)

    s = sub.add_parser("validate", help="validate a JSON file against a schema")
    s.add_argument("--schema", required=True, choices=["editing", "scripting", "sound", "corpus", "scene", "job"])
    s.add_argument("--file", required=True)
    s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("dna-check", help="accuracy gate for a DNA candidate (schema + honesty + cross-check)")
    s.add_argument("--type", required=True, choices=["editing", "scripting", "sound"])
    s.add_argument("--file", required=True)
    s.add_argument("--summary", help="metrics_summary.json of the same job")
    s.set_defaults(fn=cmd_dna_check)

    s = sub.add_parser("dna-draft", help="pre-fill the measured sections of a DNA candidate from the pack")
    s.add_argument("--type", required=True, choices=["editing", "scripting", "sound"])
    s.add_argument("--summary", required=True)
    s.add_argument("--job", required=True)
    s.add_argument("--link")
    s.add_argument("--creator")
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_dna_draft)

    s = sub.add_parser("clone-report", help="compare our rendered video's metrics with the DNA it was made from")
    s.add_argument("--type", required=True, choices=["editing", "scripting", "sound"])
    s.add_argument("--target", required=True, help="DNA or corpus json")
    s.add_argument("--summary", required=True, help="metrics_summary.json of OUR output video")
    s.set_defaults(fn=cmd_clone_report)

    s = sub.add_parser("corpus", help="aggregate many v2 DNA files of one creator into corpus DNA")
    s.add_argument("--type", required=True, choices=["editing", "scripting", "sound"])
    s.add_argument("--creator", required=True)
    s.add_argument("--files", nargs="+", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_corpus)

    s = sub.add_parser("render-local", help="render a scene plan locally")
    s.add_argument("--plan", required=True)
    s.add_argument("--quality", choices=["preview", "final"], default="preview")
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_render_local)

    s = sub.add_parser("check", help="tiny survey of my own mistakes + token habits (silent when clean)")
    s.add_argument("--quiet", action="store_true")
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("test", help="run tests; full suite is skipped when already green for this exact tree")
    s.add_argument("files", nargs="*")
    s.set_defaults(fn=cmd_test)
    s = sub.add_parser("guard-install", help="make the guard + survey hooks active from any folder (~/.claude/settings.json)")
    s.set_defaults(fn=cmd_guard_install)
    s = sub.add_parser("voice", help="voice registry: list | register | verify (clone needs signed consent, verified by Faiz in chat)")
    s.add_argument("what", choices=["list", "register", "verify"])
    s.add_argument("id", nargs="?")
    s.add_argument("--provider", default="elevenlabs")
    s.add_argument("--person", default="")
    s.add_argument("--kind", default="stock", choices=["stock", "clone"])
    s.add_argument("--voice")
    s.add_argument("--remote-id")
    s.add_argument("--ref-audio")
    s.add_argument("--consent-doc")
    s.add_argument("--expires")
    s.set_defaults(fn=cmd_voice)
    s = sub.add_parser("voice-run", help="worker: synth a voice script file (needs engine secrets in env) and upload to Drive output/voice/")
    s.add_argument("script")
    s.add_argument("--name")
    s.add_argument("--no-upload", action="store_true")
    s.set_defaults(fn=cmd_voice_run)
    s = sub.add_parser("worker", help="process jobs from Drive jobs/inbox")
    s.add_argument("--loop", action="store_true")
    s.add_argument("--until-idle", action="store_true", help="work, then stop after --grace idle seconds (GitHub Actions)")
    s.add_argument("--grace", type=int, default=180)
    s.add_argument("--max-minutes", type=int, default=60)
    s.add_argument("--no-sheet", action="store_true")
    s.set_defaults(fn=cmd_worker)

    s = sub.add_parser("wake", help="start the GitHub Actions worker now (after writing a job/approval/candidate)")
    s.add_argument("--reason", default="work waiting")
    s.add_argument("--turbo", action="store_true", help="run this on the GPU VM (only when Faiz says speed up)")
    s.set_defaults(fn=cmd_wake)

    s = sub.add_parser("bulk-jobs", help="queue many reels of one creator (measured only, one approval)")
    s.add_argument("--creator", required=True)
    s.add_argument("--batch", required=True)
    s.add_argument("--links-file", required=True)
    s.add_argument("--mode", choices=["video", "audio", "both"], default="both")
    s.set_defaults(fn=cmd_bulk_jobs)

    s = sub.add_parser("status", help="show job status")
    s.add_argument("--job")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("new-job", help="create a job file in Drive jobs/inbox")
    s.add_argument("--id", default="job", help="ignored for reel links: the ID is reel-<instagram code>")
    s.add_argument("--rerun", action="store_true", help="analyse a reel again (new run)")
    s.add_argument("--type", choices=["analyze", "render"], required=True)
    s.add_argument("--link")
    s.add_argument("--file")
    s.add_argument("--mode", choices=["video", "audio", "both"], default="both")
    s.add_argument("--target", default="general")
    s.add_argument("--command-text")
    s.set_defaults(fn=cmd_new_job)

    s = sub.add_parser("approve", help="write an approval file (user said Y or N)")
    s.add_argument("--job", required=True)
    s.add_argument("--gate", type=int, required=True, choices=[2, 3, 4, 5, 6])
    s.add_argument("--rev", type=int, default=1)
    s.add_argument("--decision", required=True, choices=["Y", "N", "y", "n"])
    s.add_argument("--feedback")
    s.set_defaults(fn=cmd_approve)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
