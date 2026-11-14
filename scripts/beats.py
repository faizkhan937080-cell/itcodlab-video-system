"""Beats table (point 4): the plan Faiz approves BEFORE anything is built (Faiz 2026-11-14).
A beat = what appears, where, on which spoken word, for how long. Doc shape:
  {"id", "duration_s", "beats": [{"id", "anchor": {"phrase", "nth"?} | {"t"}, "hold_s", "zone", "component", "text"?}], "approved"?}
Claude writes it, `validate` checks it against the real word times, Faiz says Y in chat, `./run beats approve` stamps the sha.
The worker (protocol.check_plan) refuses a Director plan whose beats are not approved or were changed after approval."""
import hashlib
import json

from .anchors import find_phrase
from .common import limits, now_iso

ZONES = {"left", "right", "bottom", "top", "center", "full"}
DEFAULTS = {"hook_s": 3.0, "min_hold_s": 0.8, "words_per_s_read": 3.0, "lead_s": 0.15, "max_beats_per_s": 0.5}


def _lim():
    return {**DEFAULTS, **(limits().get("beats") or {})}


def sha(doc):
    body = {k: v for k, v in doc.items() if k != "approved"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def resolve(doc, words):
    """Beats with start_s/end_s from the spoken word. Unresolved anchors get start_s None (validate reports them)."""
    out = []
    for b in doc.get("beats", []):
        a = b.get("anchor") or {}
        hit = find_phrase(words, a["phrase"], a.get("nth", 1)) if a.get("phrase") else None
        t = (hit["t"] - _lim()["lead_s"]) if hit else a.get("t")
        t = max(0.0, t) if t is not None else None
        hold = float(b.get("hold_s", 0))
        out.append({**b, "start_s": None if t is None else round(t, 3), "end_s": None if t is None else round(t + hold, 3),
                    "exact": bool(hit and hit["exact"])})
    return out


def validate(doc, words, allowed_components=None):
    """List of problems (empty = fine). Same checks every time, so the same mistake cannot come back."""
    lim, errs = _lim(), []
    beats = resolve(doc, words)
    dur = float(doc.get("duration_s") or 0)
    if not beats:
        return ["beats: the table is empty"]
    ids = [b.get("id") for b in beats]
    if len(set(ids)) != len(ids):
        errs.append("beats: duplicate beat id")
    for b in beats:
        n = b.get("id")
        if b["start_s"] is None:
            errs.append(f"{n}: anchor phrase not found in the spoken words (or no t). Fix the phrase.")
            continue
        if b.get("zone") not in ZONES:
            errs.append(f"{n}: zone must be one of {sorted(ZONES)}")
        if float(b.get("hold_s", 0)) < lim["min_hold_s"]:
            errs.append(f"{n}: hold_s under {lim['min_hold_s']} s, too short to read or see")
        if dur and b["end_s"] > dur + 0.01:
            errs.append(f"{n}: ends at {b['end_s']} s, after the video ends ({dur} s)")
        words_n = len(str(b.get("text", "")).split())
        if words_n and float(b["hold_s"]) < words_n / lim["words_per_s_read"]:
            errs.append(f"{n}: {words_n} words need {words_n / lim['words_per_s_read']:.1f} s to read, hold_s is {b['hold_s']}")
        if allowed_components is not None and b.get("component") not in allowed_components:
            errs.append(f"{n}: component '{b.get('component')}' is not an approved template or outside add-on")
    placed = [b for b in beats if b["start_s"] is not None]
    for i, a in enumerate(placed):
        for b in placed[i + 1:]:
            if a.get("zone") == b.get("zone") and a["start_s"] < b["end_s"] and b["start_s"] < a["end_s"]:
                errs.append(f"{a['id']} and {b['id']} overlap in zone {a['zone']}")
            if "full" in (a.get("zone"), b.get("zone")) and a["start_s"] < b["end_s"] and b["start_s"] < a["end_s"]:
                errs.append(f"{a['id']} and {b['id']} overlap (one is full screen)")
    first = min((b["start_s"] for b in placed), default=None)
    if first is not None and first > lim["hook_s"]:
        errs.append(f"hook: first beat starts at {first} s, later than {lim['hook_s']} s")
    if dur and len(placed) / dur > lim["max_beats_per_s"]:
        errs.append(f"too busy: {len(placed)} beats in {dur:g} s (max {lim['max_beats_per_s']} per second)")
    return list(dict.fromkeys(errs))


def table(doc, words):
    """Short plain table for chat: time | zone | what | on which words."""
    rows = []
    for b in resolve(doc, words):
        s = "?" if b["start_s"] is None else f"{b['start_s']:.1f}"
        e = "?" if b["end_s"] is None else f"{b['end_s']:.1f}"
        rows.append(f"{b.get('id')}: {s}-{e}s | {b.get('zone')} | {b.get('component')} | {(b.get('text') or '')[:40]} | on \"{(b.get('anchor') or {}).get('phrase', '')}\"")
    return "\n".join(rows)


def approve(doc, by="Faiz"):
    """Only the CLI calls this, after Faiz's Y in chat (rulebooks/04-approvals)."""
    doc["approved"] = {"sha": sha(doc), "by": by, "at": now_iso()}
    return doc


def is_approved(doc):
    a = doc.get("approved") or {}
    return bool(a.get("sha")) and a["sha"] == sha(doc)
