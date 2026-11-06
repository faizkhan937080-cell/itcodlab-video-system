"""Asset library (Drive assets/library): fonts, music, SFX, motion, textures, brushes. One INDEX.json says what each item is,
its licence, where it came from and its tags, so Claude can pick items by name for a recipe. Faiz drops files into
assets/library/<type>/ and runs `./run library scan` (or Claude does): new files get an entry (licence 'user-supplied').
Free items Claude fetches itself are added with `library add` (licence + source + credit required)."""
import re
from datetime import datetime, timezone

TYPES = ("font", "music", "sfx", "motion", "texture", "brush", "image", "other")
BASE = "assets/library"
SAFE = ("cc0", "pdm", "by", "ofl", "mit", "apache-2.0", "user-supplied")  # commercial use ok (BY needs credit)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "item"


def load(storage):
    try:
        d = storage.read_json(f"{BASE}/INDEX.json")
    except Exception:  # noqa: BLE001
        return []
    return d if isinstance(d, list) else []


def save(storage, items):
    storage.put_json(f"{BASE}/INDEX.json", items, versioned=False)
    storage.put_text(f"{BASE}/INDEX.md", render(items), versioned=False)


def render(items):
    out = ["# Asset library", "", "| ID | Type | Name | Licence | Source | Tags |", "|---|---|---|---|---|---|"]
    for i in items:
        out.append(f"| {i['id']} | {i['type']} | {i['name']} | {i['licence']} | {i.get('source', '')} | {', '.join(i.get('tags', []))} |")
    return "\n".join(out) + "\n"


def add_entry(storage, type_, name, licence, source="", file=None, credit="", tags=()):
    if type_ not in TYPES:
        raise ValueError(f"type must be one of {TYPES}")
    if licence.lower() not in SAFE:
        raise ValueError(f"licence '{licence}' not allowed for commercial use (allowed: {SAFE})")
    items = load(storage)
    iid = f"{type_}-{_slug(name)}"
    if any(i["id"] == iid for i in items):
        return next(i for i in items if i["id"] == iid)  # same item twice = one entry (versions are new names)
    e = {"id": iid, "type": type_, "name": name, "file": file, "licence": licence.lower(), "source": source,
         "credit": credit, "tags": [t.lower() for t in tags], "added": _now()}
    save(storage, items + [e])
    return e


def scan(storage, fingerprints=True):
    """Index files Faiz dropped into assets/library/<type>/ that have no entry yet."""
    items = load(storage)
    known = {i.get("file") for i in items}
    new = []
    for t in TYPES:
        for name in sorted(storage.list_dir(f"{BASE}/{t}")):
            rel = f"{BASE}/{t}/{name}"
            if rel in known or name.startswith("."):
                continue
            stem = name.rsplit(".", 1)[0]
            e = {"id": f"{t}-{_slug(stem)}", "type": t, "name": stem, "file": rel, "licence": "user-supplied",
                 "source": "Faiz", "credit": "", "tags": [w for w in re.split(r"[^a-z0-9]+", stem.lower()) if len(w) > 2],
                 "added": _now(), "aliases": [], "used_by": []}
            if fingerprints:
                import tempfile
                from .fingerprint import fingerprint
                with tempfile.TemporaryDirectory() as td:
                    try:
                        e["fingerprint"] = fingerprint(storage.fetch(rel, f"{td}/{name}"), t)
                    except Exception:  # noqa: BLE001  (cannot read: indexed by name only, fingerprint next scan)
                        pass
                hit, tier, dist = _classify_against(items + new, e["fingerprint"], t) if e.get("fingerprint") else (None, "different", None)
                if tier in ("exact", "near"):
                    e["duplicate_of"], e["tier"] = hit["id"], tier  # listed for ONE batch clean-up question, never auto-deleted
                elif tier == "variant":
                    e["variant_of"], e["variant_distance"] = hit["id"], dist
            if any(i["id"] == e["id"] for i in items + new):
                e["id"] += "-" + (e.get("fingerprint", {}).get("sha256", "x")[:6])
            new.append(e)
    if new:
        save(storage, items + new)
    return new


def _classify_against(items, fp, type_):
    """Best match among same-type items that have a fingerprint: (item, tier, distance). Exact beats near beats variant."""
    from .fingerprint import classify
    order = {"exact": 0, "near": 1, "variant": 2}
    best = None
    for i in items:
        if i["type"] != type_ or not i.get("fingerprint"):
            continue
        tier, d = classify(fp, i["fingerprint"])
        if tier in order and (best is None or (order[tier], d or 0) < (order[best[1]], best[2] or 0)):
            best = (i, tier, d)
    return best or (None, "different", None)


def add_file(storage, local_path, type_, name, licence, source="", credit="", tags=(), used_by=None):
    """Add a real file. Same content under another name never makes a second copy:
    exact -> only an alias; near (same item, re-encoded) -> alias, the better quality copy becomes primary (old one kept, listed);
    variant (micro change) -> its own item, linked variant_of; different -> new item. Returns (entry, tier)."""
    from pathlib import Path
    from .fingerprint import better, fingerprint
    if type_ not in TYPES:
        raise ValueError(f"type must be one of {TYPES}")
    if licence.lower() not in SAFE:
        raise ValueError(f"licence '{licence}' not allowed for commercial use (allowed: {SAFE})")
    from .security import require_safe
    require_safe(local_path, {"music": "audio", "sfx": "audio", "font": "font", "image": "image", "texture": "image", "brush": "image"}.get(type_, "other"))
    fp = fingerprint(local_path, type_)
    items = load(storage)
    hit, tier, dist = _classify_against(items, fp, type_)
    ext = Path(local_path).suffix.lower()
    if tier in ("exact", "near"):
        if name not in hit.setdefault("aliases", []) and name != hit["name"]:
            hit["aliases"].append(name)
        if tier == "near" and better(fp, hit["fingerprint"]):
            rel = storage.put_file(local_path, f"{BASE}/{type_}/{_slug(name)}{ext}")
            hit.setdefault("previous_files", []).append(hit["file"])
            hit["file"], hit["fingerprint"] = rel, fp
        if used_by:
            hit.setdefault("used_by", []).append(used_by)
        save(storage, items)
        return hit, tier
    rel = storage.put_file(local_path, f"{BASE}/{type_}/{_slug(name)}{ext}")
    iid = f"{type_}-{_slug(name)}"
    n = 2
    while any(i["id"] == iid for i in items):  # same name, different content: its own item
        iid = f"{type_}-{_slug(name)}-{n}"
        n += 1
    e = {"id": iid, "type": type_, "name": name, "file": rel, "licence": licence.lower(), "source": source, "credit": credit,
         "tags": [t.lower() for t in tags], "added": _now(), "fingerprint": fp, "aliases": [],
         "used_by": [used_by] if used_by else []}
    if tier == "variant":
        e["variant_of"], e["variant_distance"] = hit["id"], dist
    save(storage, items + [e])
    return e, tier


def mark_used(storage, item_id, reel, creator=""):
    items = load(storage)
    for i in items:
        if i["id"] == item_id:
            i.setdefault("used_by", []).append({"reel": reel, "creator": creator})
            save(storage, items)
            return i
    raise KeyError(item_id)


def find(storage, word, type_=None):
    w = word.lower()
    return [i for i in load(storage) if (not type_ or i["type"] == type_)
            and (w in i["name"].lower() or w in i["id"] or w in i.get("tags", []))]


def fetch_from_openverse(storage, query, type_, name=None, tags=(), token=None, search_fn=None, download_fn=None, measure_fn=None):
    """Download the best licensed (cc0 > pdm > by) match for `query`, number-check it, add it by `name`. None if nothing usable."""
    import tempfile
    from . import sfx
    category = "music" if type_ == "music" else "sound_effect"
    max_s = 600 if type_ == "music" else sfx.MAX_DURATION_S
    results = (search_fn or sfx.search_q)(query, category, None if type_ == "music" else "short", 20, token)
    item, credit = sfx.pick(results, max_s)
    if not item:
        return None
    with tempfile.TemporaryDirectory() as td:
        ext = "." + (item.get("filetype") or "mp3").lstrip(".")
        dest = f"{td}/{_slug(name or query)}{ext}"
        (download_fn or sfx.download)(item["url"], dest)
        if type_ == "sfx":
            dur, peak = (measure_fn or sfx.measure)(dest)
            if sfx.judge(dur, peak):  # reason string = unusable (clipped, too quiet, too long)
                return None
        e, tier = add_file(storage, dest, type_, name or query, item["license"].lower(), item.get("foreign_landing_url") or item["url"],
                           credit or "", list(tags) + [query.lower()])
    e["fetch_tier"] = tier
    return e
