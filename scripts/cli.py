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
    print(json.dumps(res, indent=2))
    return 0 if res["ok"] else 1


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
    f.write_text(f"{now_iso()} {a.reason}\n", encoding="utf-8")
    run_cmd(["git", "-C", str(ROOT), "add", "trigger/wake.txt"])
    rc, out, err = run_cmd(["git", "-C", str(ROOT), "commit", "-q", "-m", f"wake worker: {a.reason}"])
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

    s = sub.add_parser("worker", help="process jobs from Drive jobs/inbox")
    s.add_argument("--loop", action="store_true")
    s.add_argument("--until-idle", action="store_true", help="work, then stop after --grace idle seconds (GitHub Actions)")
    s.add_argument("--grace", type=int, default=180)
    s.add_argument("--max-minutes", type=int, default=60)
    s.add_argument("--no-sheet", action="store_true")
    s.set_defaults(fn=cmd_worker)

    s = sub.add_parser("wake", help="start the GitHub Actions worker now (after writing a job/approval/candidate)")
    s.add_argument("--reason", default="work waiting")
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
