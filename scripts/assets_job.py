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
COMMONS = "https://commons.wikimedia.org/w/api.php"
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


def _commons_licence(meta):
    """Wikimedia extmetadata -> our licence code (only commercial-safe ones; share-alike / non-commercial -> None)."""
    lic = str((meta.get("License") or {}).get("value", "")).lower()
    short = str((meta.get("LicenseShortName") or {}).get("value", "")).lower()
    if lic in ("cc0", "cc-zero") or "cc0" in short:
        return "cc0"
    if lic.startswith("pd") or "public domain" in short:
        return "pdm"
    if lic.startswith("cc-by-") and "-sa" not in lic and "-nc" not in lic and "-nd" not in lic:
        return "by"
    return None


def search_commons(query, aspect=None, page_size=30, token=None):
    """Wikimedia Commons (official API): files with a commercial-safe licence, as Openverse-shaped results."""
    import re as _re
    from .netguard import config, guard
    p = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrsearch": f"{query} filetype:bitmap",
         "gsrlimit": page_size, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1600}
    req = urllib.request.Request(f"{COMMONS}?{urllib.parse.urlencode(p)}", headers={"User-Agent": config()["user_agent"]})

    def go():
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8"))
    data = guard().call("wikimedia", go)
    out = []
    for pg in sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda x: x.get("index", 0)):
        ii = (pg.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        lic = _commons_licence(meta)
        w, h = ii.get("width") or 0, ii.get("height") or 0
        if not lic or not ii.get("thumburl") or min(w, h) < 600:
            continue
        if aspect == "wide" and w < h * 1.2 or aspect == "tall" and h < w * 1.2:
            continue
        artist = _re.sub(r"<[^>]+>", "", str((meta.get("Artist") or {}).get("value", ""))).strip()
        out.append({"url": ii["thumburl"], "license": lic, "license_version": str((meta.get("LicenseShortName") or {}).get("value", "")),
                    "creator": artist or "unknown", "title": pg.get("title", "").replace("File:", ""), "foreign_landing_url": ii.get("descriptionurl", ""),
                    "filetype": ii["thumburl"].rsplit(".", 1)[-1].lower(), "width": w, "height": h, "source": "wikimedia"})
    return out


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
        res, errors = [], []
        for src in ([search_fn] if search_fn else [search_images, search_commons]):   # official APIs, one after the other
            try:
                res += [r for r in src(q["query"], q.get("aspect"), 30, token) if str(r.get("license", "")).lower() in OK and r.get("url")]
            except Exception as e:  # noqa: BLE001  (a host that said stop is not retried here: netguard keeps the cooldown)
                errors.append(f"{getattr(src, '__name__', 'source')}: {type(e).__name__}: {e}"[:160])
            if len(res) >= want * 2:
                break
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
        report.append({"query": q["query"], "name": name, "found": len(res), "errors": errors, "kept": [{k: v for k, v in g.items() if k != "local"} for g in got],
                       "sheet": sheet.name if sheet else None})
    (wd / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report
