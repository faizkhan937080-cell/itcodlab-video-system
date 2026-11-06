"""Company assets that sit in THEIR Google Drive (shared with Faiz's account or 'anyone with link'): index only, no bulk copy.
The index (name, folder, type, size, md5, Drive id) is built by rclone listing - no tokens, no download. A file is downloaded
only when a recipe needs it. Same md5 twice = exact duplicate, listed once."""
import json
import re
import subprocess
from pathlib import PurePosixPath

KIND = {"audio": {".mp3", ".wav", ".m4a", ".flac", ".ogg"}, "video": {".mp4", ".mov", ".mkv", ".webm", ".avi"},
        "image": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".psd", ".ai"}, "font": {".ttf", ".otf", ".woff", ".woff2"},
        "motion": {".json", ".lottie", ".aep", ".mogrt", ".prproj"}, "archive": {".zip", ".rar", ".7z"}}


def folder_id(link_or_id):
    m = re.search(r"/folders/([A-Za-z0-9_-]{10,})", link_or_id) or re.search(r"[?&]id=([A-Za-z0-9_-]{10,})", link_or_id)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", link_or_id.strip()):
        return link_or_id.strip()
    raise ValueError("no Drive folder id in that link")


def kind_of(name):
    ext = PurePosixPath(name).suffix.lower()
    return next((k for k, v in KIND.items() if ext in v), "other")


def _remote_for(remote, fid):
    return f"{remote.split(',')[0].split(':')[0]},root_folder_id={fid}:"


def list_folder(remote, fid, depth=None, run=subprocess.run):
    """rclone lsjson of someone's shared folder. Raises with a plain reason when it cannot be read."""
    cmd = ["rclone", "lsjson", "-R", "--hash", "--no-modtime", _remote_for(remote, fid)]
    if depth:
        cmd[2:2] = ["--max-depth", str(depth)]
    r = run(cmd, capture_output=True, text=True, timeout=1500)
    if r.returncode != 0:
        raise RuntimeError("cannot read that folder (not shared with this Google account, or link restricted): " + (r.stderr or "")[-200:])
    return json.loads(r.stdout or "[]")


def build_index(raw, company, fid, licence_note=""):
    items, seen, dupes, total = [], {}, [], 0
    for x in raw:
        if x.get("IsDir"):
            continue
        md5 = (x.get("Hashes") or {}).get("md5", "")
        e = {"path": x["Path"], "type": kind_of(x["Path"]), "size": x.get("Size", 0), "md5": md5, "id": x.get("ID", ""),
             "mime": x.get("MimeType", "")}
        total += e["size"] or 0
        if md5 and md5 in seen:
            dupes.append({"path": e["path"], "same_as": seen[md5]})
            continue
        if md5:
            seen[md5] = e["path"]
        items.append(e)
    by_type = {}
    for e in items:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    return {"company": company, "folder_id": fid, "licence_note": licence_note or "NOT CONFIRMED: ask the company what use is allowed",
            "count": len(items), "total_bytes": total, "by_type": by_type, "exact_duplicates": dupes, "items": items}


def write_index(storage, idx):
    base = f"assets/external/{idx['company']}"
    storage.put_json(f"{base}/INDEX.json", idx, versioned=False)
    md = [f"# {idx['company']}: external assets (index only)", f"Folder id: {idx['folder_id']}", f"Licence: {idx['licence_note']}",
          f"Files: {idx['count']} ({idx['total_bytes'] / 1e9:.2f} GB), exact duplicates skipped: {len(idx['exact_duplicates'])}",
          "By type: " + ", ".join(f"{k} {v}" for k, v in sorted(idx["by_type"].items()))]
    storage.put_text(f"{base}/INDEX.md", "\n".join(md) + "\n", versioned=False)
    return base


def search(idx, word, type_=None, limit=30):
    w = word.lower()
    return [e for e in idx["items"] if (not type_ or e["type"] == type_) and w in e["path"].lower()][:limit]
