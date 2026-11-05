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
    job = {"id": a.id, "type": a.type, "created": now_iso(), "command_text": a.command_text or ""}
    if a.type == "analyze":
        job.update({"mode": a.mode, "target": a.target, "gate1_approved_by_user": True})
        if a.link:
            job["link"] = a.link
        if a.file:
            job["file"] = a.file
    errs = validate("job", job)
    if errs:
        print("INVALID\n" + errors_tail(errs))
        return 1
    print(_storage().put_json(f"jobs/inbox/{a.id}.json", job))
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
    s.add_argument("--id", required=True)
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
