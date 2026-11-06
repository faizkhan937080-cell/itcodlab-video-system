"""Company (client) side: clients/<company>/<video>/ holds what we MADE for them, linked back to the reference reel.
made_from.json pins the exact reel and the exact DNA files (sha256), so a later DNA v2 never silently changes an old video.
credits.json lists every third-party item used; the licence gate blocks delivery while any licence is not commercial-ok."""
import hashlib
import re

from .common import now_iso
from .library import SAFE

SUBDIRS = ("brand", "briefs", "videos")
NO_COPY = ("Style is learned from the reference reel; its footage, music and assets are never put in the output. "
           "Same named elements are re-used only from licensed sources (assets/library).")


def _slug(s):
    return re.sub(r"[^a-z0-9._-]+", "-", s.strip().lower()).strip("-")


def init_company(storage, company):
    c = _slug(company)
    for sub in SUBDIRS:
        storage.ensure_dir(f"clients/{c}/{sub}")
    return f"clients/{c}"


def sha256_text(storage, rel):
    return hashlib.sha256(storage.read_text(rel).encode("utf-8")).hexdigest()


def find_reel_json(storage, ref):
    """ref = reel code or job id. Returns (reel.json dict, folder)."""
    for h in storage.list_dir("creators"):
        for d in storage.list_dir(f"creators/{h}/videos"):
            if d == ref or d == f"reel-{ref}":
                try:
                    return storage.read_json(f"creators/{h}/videos/{d}/reel.json"), f"creators/{h}/videos/{d}"
                except Exception:  # noqa: BLE001
                    continue
    raise LookupError(f"reel {ref} not found in any creators/<h>/videos (analysis finished?)")


def write_made_from(storage, company, video, ref, credits=()):
    reel, folder = find_reel_json(storage, ref)
    base = f"clients/{_slug(company)}/videos/{_slug(video)}"
    pins = {}
    for p in reel.get("dna", []):
        pins[p] = sha256_text(storage, p)
    mf = {"schema_version": 1, "company": _slug(company), "video": _slug(video), "created": now_iso(),
          "reference": {"reel_id": reel.get("reel_id") or reel.get("job"), "creator": reel.get("creator"),
                        "link": reel.get("link"), "folder": folder, "recipe": f"{folder}/RECIPE.md"},
          "dna_pinned": pins, "rule": NO_COPY}
    storage.put_json(f"{base}/made_from.json", mf)
    storage.put_json(f"{base}/credits.json", list(credits))
    return base, mf


def licence_blockers(credits):
    """Items whose licence is not commercial-ok (unknown, non-commercial, needs-licence). Empty list = free to deliver."""
    return [c.get("name", c.get("id", "?")) for c in credits
            if str(c.get("licence", "")).lower() not in SAFE and not c.get("risk_accepted")]


def accept_risk(credits, reason, date=None):
    """Faiz decides (rulebook 18): mark every item that is not commercial-ok as 'risk accepted' with his words and the date.
    Returns (new_credits, names_marked). The item stays visible in credits.json, so the alert is never lost."""
    from .common import now_iso
    out, marked = [], []
    for c in credits:
        c = dict(c)
        if str(c.get("licence", "")).lower() not in SAFE and not c.get("risk_accepted"):
            c["risk_accepted"] = {"by": "faiz", "reason": reason, "date": date or now_iso()}
            marked.append(c.get("name", c.get("id", "?")))
        out.append(c)
    return out, marked


def check_made_from(storage, company_dir):
    """Problems in one made video: missing reel, DNA file gone or changed since it was pinned."""
    out = []
    try:
        mf = storage.read_json(f"{company_dir}/made_from.json")
    except Exception:  # noqa: BLE001
        return [f"{company_dir}: made_from.json missing"]
    if not storage.exists(mf["reference"]["folder"]):
        out.append(f"{company_dir}: reference folder gone: {mf['reference']['folder']}")
    for p, h in mf.get("dna_pinned", {}).items():
        if not storage.exists(p):
            out.append(f"{company_dir}: pinned DNA missing: {p}")
        elif sha256_text(storage, p) != h:
            out.append(f"{company_dir}: pinned DNA changed: {p}")
    return out
