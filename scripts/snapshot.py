"""Small, text-only picture of what is in Drive (reels, DNA files with sha256, client videos, library items), saved to GitHub.
Big media files are NOT copied: a reel can be fetched again from its link, and this manifest says exactly what existed."""
import hashlib
import json

from . import layout
from .common import now_iso


def build(storage):
    out = {"taken": now_iso(), "creators": {}, "clients": {}, "library": [], "external": []}
    for h in storage.list_dir("creators"):
        reels = []
        for d, rel in layout.reel_dirs(storage, h):
            try:
                r = storage.read_json(f"{rel}/reel.json")
            except Exception:  # noqa: BLE001
                reels.append({"reel": d, "finished": False})
                continue
            dna = {}
            for p in r.get("dna", []):
                try:
                    dna[p] = hashlib.sha256(storage.read_text(p).encode("utf-8")).hexdigest()
                except Exception:  # noqa: BLE001
                    dna[p] = "MISSING"
            reels.append({"reel": d, "link": r.get("link"), "mode": r.get("mode"), "saved": r.get("saved"), "dna": dna})
        out["creators"][h] = reels
    for c in storage.list_dir("clients"):
        out["clients"][c] = []
        for v in storage.list_dir(f"clients/{c}/videos"):
            try:
                mf = storage.read_json(f"clients/{c}/videos/{v}/made_from.json")
                out["clients"][c].append({"video": v, "reference": mf["reference"]["reel_id"], "dna_pinned": mf["dna_pinned"]})
            except Exception:  # noqa: BLE001
                out["clients"][c].append({"video": v, "made_from": "MISSING"})
    try:
        out["library"] = [{k: i.get(k) for k in ("id", "type", "name", "licence", "source", "file")}
                          for i in storage.read_json("assets/library/INDEX.json")]
    except Exception:  # noqa: BLE001
        pass
    for c in storage.list_dir("assets/external"):
        try:
            x = storage.read_json(f"assets/external/{c}/INDEX.json")
            out["external"].append({"company": c, "folder_id": x["folder_id"], "count": x["count"], "licence_note": x["licence_note"]})
        except Exception:  # noqa: BLE001
            pass
    return out


def write_local(storage, path):
    from pathlib import Path
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(build(storage), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return p
