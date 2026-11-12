"""Assets job: real pictures from outside (Faiz 2026-11-12: no fake backgrounds, outside sources only).
job = {"id": "assets-x", "type": "assets", "queries": [{"query": "dark room lamp", "name": "dark-room", "count": 6,
       "aspect": "tall|wide|square"}]}
Worker: Openverse image search (commercial licences only: cc0, pdm, by), safe download, store in Drive
assets/library/image/<name>/<n>.<ext>, add each to the library INDEX (licence + credit + source page), and publish a
numbered contact sheet (collage_assets_NN.jpg) to the review branch so Claude can LOOK and pick by number.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

OPENVERSE_IMG = "https://api.openverse.org/v1/images/"
OK = ("cc0", "pdm", "by")


def search_images(query, aspect=None, page_size=30, token=None):
    from .netguard import config, guard
    p = {"q": query, "license_type": "commercial", "page_size": page_size, "size": "large"}
    if aspect:
        p["aspect_ratio"] = aspect
    req = urllib.request.Request(f"{OPENVERSE_IMG}?{urllib.parse.urlencode(p)}", headers={"User-Agent": config()["user_agent"]})
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    def go():
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8")).get("results", [])
    return guard().call("openverse", go)


def _credit(it):
    lic = f"CC {it.get('license', '').upper()} {it.get('license_version', '')}".strip()
    return f"\"{it.get('title', '')}\" by {it.get('creator') or 'unknown'} ({lic}) {it.get('foreign_landing_url', '')}"


def _sheet(files, out, title):
    tiles = []
    for i, f in enumerate(files, 1):
        try:
            im = Image.open(f).convert("RGB")
        except Exception:  # noqa: BLE001
            continue
        im.thumbnail((300, 300))
        tile = Image.new("RGB", (300, 320), (30, 30, 30))
        tile.paste(im, ((300 - im.width) // 2, 20 + (300 - im.height) // 2))
        ImageDraw.Draw(tile).text((4, 3), f"#{i} {title}", fill=(255, 255, 0))
        tiles.append(tile)
    if not tiles:
        return None
    cols = min(4, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 300, rows * 320), (0, 0, 0))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 300, (i // cols) * 320))
    sheet.save(out, quality=88)
    return out


def run(storage, job, wd, token=None, search_fn=None, download_fn=None):
    from . import library
    from .netguard import safe_download
    wd = Path(wd)
    wd.mkdir(parents=True, exist_ok=True)
    report = []
    for qi, q in enumerate(job.get("queries") or [], 1):
        name = library._slug(q.get("name") or q["query"])
        want = max(1, min(int(q.get("count", 6)), 12))
        res = (search_fn or search_images)(q["query"], q.get("aspect"), 30, token)
        res = [r for r in res if str(r.get("license", "")).lower() in OK and r.get("url")]
        got = []
        for it in res:
            if len(got) >= want:
                break
            ext = "." + (it.get("filetype") or "jpg").lstrip(".").lower().replace("jpeg", "jpg")
            dest = wd / name / f"{len(got) + 1}{ext}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                (download_fn or safe_download)(it["url"], dest, "image")
            except Exception:  # noqa: BLE001
                continue
            rel = f"{library.BASE}/image/{name}/{dest.name}"
            storage.put_file(dest, rel)
            library.add_entry(storage, "image", f"{name}-{len(got) + 1}", str(it["license"]).lower(),
                              source=it.get("foreign_landing_url", ""), file=rel, credit=_credit(it),
                              tags=[w for w in q["query"].lower().split() if len(w) > 2])
            got.append({"n": len(got) + 1, "file": rel, "licence": it["license"], "w": it.get("width"), "h": it.get("height"),
                        "credit": _credit(it), "local": str(dest)})
        sheet = _sheet([g["local"] for g in got], wd / f"collage_assets_{qi:02d}.jpg", name) if got else None
        report.append({"query": q["query"], "name": name, "found": len(res), "kept": [{k: v for k, v in g.items() if k != "local"} for g in got],
                       "sheet": sheet.name if sheet else None})
    (wd / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report
