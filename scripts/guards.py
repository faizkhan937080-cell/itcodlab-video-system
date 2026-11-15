"""Repeat-proofing: every mistake Faiz had to say more than once is a check here, run by code, not by memory.
Each check returns (ok, message). `./run gate-check` runs them; a failed check blocks "ready"."""
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
MEM = ROOT / "memory"
MAX_WPM = 195   # follows the reference: thebrainmaze reels speak 163-187 wpm; Faiz asked for faster, energetic (2026-11-16)
MIN_STYLE_SCORE = 7   # Checker's 0-10 score of "looks like the style card"


def _load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def voice_pace(script_text, seconds):
    """Voice must be clearly intelligible: spoken pace within MAX_WPM (pauses counted in)."""
    n = len(re.findall(r"[\w'’-]+", script_text))
    wpm = n / (seconds / 60.0) if seconds else 0
    return wpm <= MAX_WPM, f"voice pace {wpm:.0f} wpm (max {MAX_WPM}) over {n} words"


def prompts_fit(prompts):
    """A prompt longer than the image model reads is silently cut: the style words vanish. Fail instead."""
    from .stills_api import cut_report
    bad = [f"{p['id']}: {cut_report(p['prompt'])[0]} tokens" for p in prompts if cut_report(p["prompt"])[1]]
    return not bad, "prompts cut by the model: " + ", ".join(bad) if bad else "all prompts fit"


def motion_honest(spec, faiz_ok_substitute=False):
    """"3D motion graphics" must not be delivered as zoom/pan on still pictures unless Faiz said so."""
    still_based = any(s.get("image") or s.get("mode") == "parallax" for s in spec.get("scenes", [])) or spec.get("mode") == "parallax"
    if spec.get("claim") == "3d_motion_graphics" and still_based and not faiz_ok_substitute:
        return False, "claimed 3D motion graphics but scenes are zoom/camera on still pictures (tell Faiz first)"
    return True, "motion claim honest"


def looked(job_id, work=WORK):
    """'Ready' only after the Checker looked at the output and scored it against the style card."""
    r = _load(Path(work) / "checks" / f"{job_id}.json", {})
    if not r.get("looked"):
        return False, f"{job_id}: nobody looked at the output yet (./run looked {job_id} --score N --note ...)"
    if r.get("style_score", 0) < MIN_STYLE_SCORE:
        return False, f"{job_id}: style match {r.get('style_score')}/10 is below {MIN_STYLE_SCORE}. Do not hand it over; say what is missing"
    return True, f"{job_id}: looked, style match {r['style_score']}/10"


def record_look(job_id, score, note="", work=WORK):
    p = Path(work) / "checks" / f"{job_id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"looked": True, "style_score": score, "note": note, "at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())}), encoding="utf-8")
    return p


# --- waiting items and approvals (so nothing stalls at a gate and nothing is asked twice) ---
def _ledger(name, mem=MEM):
    return Path(mem) / name


def pending_add(key, text, mem=MEM):
    d = _load(_ledger("pending.json", mem), {})
    d[key] = {"text": text, "since": time.time()}
    _ledger("pending.json", mem).write_text(json.dumps(d), encoding="utf-8")


def pending_clear(key, mem=MEM):
    d = _load(_ledger("pending.json", mem), {})
    d.pop(key, None)
    _ledger("pending.json", mem).write_text(json.dumps(d), encoding="utf-8")


def approved_add(key, text, mem=MEM):
    d = _load(_ledger("approved.json", mem), {})
    d[key] = {"text": text, "at": time.time()}
    _ledger("approved.json", mem).write_text(json.dumps(d), encoding="utf-8")
    pending_clear(key, mem)


def is_approved(key, mem=MEM):
    return key in _load(_ledger("approved.json", mem), {})


def brief_lines(mem=MEM, stall_h=2, now=None):
    now = now or time.time()
    out = []
    for k, v in _load(_ledger("pending.json", mem), {}).items():
        h = (now - v["since"]) / 3600
        out.append(f"WAITING {k}: {v['text']} ({h:.0f} h)" + (" STALLED: ask Faiz now" if h >= stall_h else ""))
    ap = _load(_ledger("approved.json", mem), {})
    if ap:
        out.append("ALREADY APPROVED (never ask again): " + "; ".join(f"{k}" for k in list(ap)[-8:]))
    return out
