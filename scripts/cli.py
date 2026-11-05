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
    if a.loop:
        w.loop(max_minutes=a.max_minutes)
    else:
        for jid, status in w.process_once():
            print(f"{jid}: {status}")
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
    s.add_argument("--schema", required=True, choices=["editing", "scripting", "sound", "scene", "job"])
    s.add_argument("--file", required=True)
    s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("render-local", help="render a scene plan locally")
    s.add_argument("--plan", required=True)
    s.add_argument("--quality", choices=["preview", "final"], default="preview")
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_render_local)

    s = sub.add_parser("worker", help="process jobs from Drive jobs/inbox")
    s.add_argument("--loop", action="store_true")
    s.add_argument("--max-minutes", type=int, default=60)
    s.add_argument("--no-sheet", action="store_true")
    s.set_defaults(fn=cmd_worker)

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
