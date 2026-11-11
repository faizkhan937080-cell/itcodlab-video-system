"""rulebooks/23-protocol.md enforced in code. Without these checks a render job does not move forward.
- plan.protocol.digest must equal the digest of the protocol file on the worker (proves it was read, and is current)
- kind "sample": short plan (<= sample_max_s); kind "full": needs an approved sample job using the same sources + effects
- reference: path of a COMPLETE style_record.json, or "none" + reason
- frame_check(): frames every ~6 s -> collage + automatic problems (green left, blank, frozen); Claude must look (look-ok)
"""
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .common import ROOT, limits

PROTOCOL_FILE = ROOT / "rulebooks" / "23-protocol.md"
FX_KEYS = ("stabilize", "speed", "speed_ramp", "clean_voice", "chroma_key", "remove_bg", "reframe", "track_from", "denoise")
LOOK_GATE = 7   # approvals/<job>__gate7__r<plan_ver>.json: written after Claude looked at the frame collage


def protocol_text():
    return PROTOCOL_FILE.read_text(encoding="utf-8")


def digest():
    return hashlib.sha256(protocol_text().replace("\r\n", "\n").strip().encode("utf-8")).hexdigest()[:12]


def stamp(plan, kind, reference="none", reference_reason="", sample_job=None):
    """Add the protocol block to a plan (the CLI prints the protocol text first)."""
    plan = json.loads(json.dumps(plan))
    blk = {"digest": digest(), "kind": kind, "reference": reference}
    if reference == "none":
        blk["reference_reason"] = reference_reason
    if sample_job:
        blk["sample_job"] = sample_job
    plan["protocol"] = blk
    return plan


def plan_total_s(plan):
    return sum(float(s.get("duration_s") or 0) for s in plan.get("scenes", []))


def plan_fx(plan):
    """{(src, effect)} for every effect used on a clip."""
    out = set()
    for s in plan.get("scenes", []):
        p = s.get("props") or {}
        if isinstance(p.get("src"), str):
            for k in FX_KEYS:
                if p.get(k):
                    out.add((p["src"], k))
    return out


def plan_sources(plan):
    return {(s.get("props") or {}).get("src") for s in plan.get("scenes", []) if isinstance((s.get("props") or {}).get("src"), str)}


def check_plan(plan, storage, lim=None):
    """List of problems (empty = protocol satisfied). Runs on the worker, so it cannot be skipped by Claude."""
    lim = lim or limits()
    pl = lim.get("protocol", {})
    b = plan.get("protocol")
    if not isinstance(b, dict):
        return ["protocol: plan has no protocol block. Run `./run plan-stamp` (it prints rulebooks/23-protocol.md first)."]
    errs = []
    if b.get("digest") != digest():
        errs.append(f"protocol: digest {b.get('digest')} is not the current protocol {digest()}. Read rulebooks/23-protocol.md and stamp again.")
    kind = b.get("kind")
    if kind == "sample":
        mx = float(pl.get("sample_max_s", 8))
        if plan_total_s(plan) > mx + 0.01:
            errs.append(f"protocol: a sample plan is at most {mx:g} s (this one is {plan_total_s(plan):.1f} s). Cut a 5-6 s piece.")
    elif kind == "full":
        sj = b.get("sample_job")
        if not sj:
            errs.append("protocol: a full plan needs protocol.sample_job (an approved 5-6 s sample of the SAME clip and effects).")
        else:
            try:
                sst = storage.read_json(f"jobs/state/{sj}.json")
            except Exception:  # noqa: BLE001
                sst = None
            if not sst or not sst.get("sample_ok"):
                errs.append(f"protocol: sample job {sj} is not approved by Faiz yet (gate 5 = Y on the sample).")
            else:
                try:
                    splan = storage.read_json(sst["paths"]["plan"])
                    miss_src = plan_sources(plan) - plan_sources(splan)
                    miss_fx = plan_fx(plan) - plan_fx(splan)
                    if miss_src:
                        errs.append(f"protocol: sources not in the approved sample: {sorted(miss_src)}")
                    if miss_fx:
                        errs.append(f"protocol: effects not tested in the sample: {sorted(miss_fx)}")
                except Exception as e:  # noqa: BLE001
                    errs.append(f"protocol: could not read the sample plan: {e}")
    else:
        errs.append("protocol: protocol.kind must be 'sample' or 'full'.")
    ref = b.get("reference")
    if not ref:
        errs.append("protocol: protocol.reference missing (style_record.json path, or 'none' with reference_reason).")
    elif ref == "none":
        if len(str(b.get("reference_reason", ""))) < 8:
            errs.append("protocol: reference 'none' needs a reference_reason (why no reference).")
    else:
        try:
            rec = storage.read_json(ref)
            if not rec.get("complete"):
                errs.append(f"protocol: reference record {ref} is incomplete: {rec.get('problems')}")
        except Exception:  # noqa: BLE001
            errs.append(f"protocol: reference record {ref} not found. Analyse the reference first (style_record.json).")
    return errs


# ------------------------------------------------------------------ frame check (after every render)
def _label(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 8 + 7 * len(text), 16], fill=(0, 0, 0))
    d.text((3, 2), text, fill=(255, 255, 255))


def frame_times(duration, step_s=6.0, max_tiles=10):
    n = max(3, min(max_tiles, int(math.ceil(duration / step_s)) + 1))
    first, last = min(0.4, duration / 4), max(duration - 0.4, duration * 0.75)
    return [round(first + (last - first) * i / (n - 1), 2) for i in range(n)]


def green_residue(bgr):
    b, g, r = [bgr[..., i].astype(int) for i in range(3)]
    return float(np.mean((g - np.maximum(r, b) > 40) & (g > 110)))


def frame_check(video, out_dir, lim=None):
    """Frames at start, middle, end and about every frame_step_s. Writes collage_frames.jpg + returns problems/metrics."""
    pl = (lim or limits()).get("protocol", {})
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    dur = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / fps
    if dur <= 0:
        raise RuntimeError("frame check: cannot read the video")
    times = frame_times(dur, pl.get("frame_step_s", 6), pl.get("frame_max_tiles", 10))
    tiles, mets, sigs = [], [], []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if not ok:
            continue
        gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        mets.append({"t": t, "green": round(green_residue(fr), 4), "std": round(float(gray.std()), 1)})
        sigs.append(cv2.resize(gray, (16, 16)).astype(float))
        h, w = fr.shape[:2]
        tw = 300 if h >= w else 480
        im = Image.fromarray(cv2.cvtColor(cv2.resize(fr, (tw, int(h * tw / w))), cv2.COLOR_BGR2RGB))
        _label(im, f"t={t:.1f}s")
        tiles.append(im)
    cap.release()
    if not tiles:
        raise RuntimeError("frame check: no frames could be read")
    cols = min(5, len(tiles))
    rows = int(math.ceil(len(tiles) / cols))
    tw_, th_ = tiles[0].size
    sheet = Image.new("RGB", (cols * tw_, rows * th_), (255, 0, 255))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * tw_, (i // cols) * th_))
    path = out_dir / "collage_frames.jpg"
    sheet.save(path, quality=88)
    problems = []
    gmax = float(pl.get("green_residue_max", 0.01))
    for m in mets:
        if m["green"] > gmax:
            problems.append(f"green left at t={m['t']}s ({m['green'] * 100:.1f}% of the frame)")
        if m["std"] < 6 and m["t"] > 1:
            problems.append(f"frame at t={m['t']}s is almost blank")
    if len(sigs) > 2 and max(float(np.abs(sigs[i] - sigs[0]).mean()) for i in range(1, len(sigs))) < 1.0:
        problems.append("nothing changes between the sampled frames (frozen video)")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return {"ok": not problems, "problems": problems[:6], "times": times, "metrics": mets,
            "collage": path.name, "sha": sha, "duration_s": round(dur, 2)}


def look_marker(job_id, plan_ver, sha, saw):
    """File Claude uploads to Drive jobs/approvals/<job>__gate7__r<ver>.json after looking at the collage."""
    return (f"{job_id}__gate{LOOK_GATE}__r{plan_ver}.json",
            {"job": job_id, "gate": LOOK_GATE, "rev": plan_ver, "decision": "Y", "feedback": f"sha={sha} | saw: {saw}"})
