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


def scan(storage):
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
            new.append({"id": f"{t}-{_slug(stem)}", "type": t, "name": stem, "file": rel, "licence": "user-supplied",
                        "source": "Faiz", "credit": "", "tags": [w for w in re.split(r"[^a-z0-9]+", stem.lower()) if len(w) > 2],
                        "added": _now()})
    if new:
        save(storage, items + new)
    return new


def find(storage, word, type_=None):
    w = word.lower()
    return [i for i in load(storage) if (not type_ or i["type"] == type_)
            and (w in i["name"].lower() or w in i["id"] or w in i.get("tags", []))]
