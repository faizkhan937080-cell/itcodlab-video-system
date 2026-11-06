"""./run audit-links: finds orphan/unfinished reel folders, the same reel in two places, broken made_from links,
library entries without a file and exact-duplicate library files. Read-only. Run after every job."""
from . import clients, layout, library
from .reelid import shortcode


import re

_TEST = re.compile(r"^(test|tmp|scratch|trial|probe)[-_]", re.I)


def run(storage):
    issues, seen = [], {}
    for base in ("creators", "clients", "assets/library"):
        for n in storage.list_dir(base):
            if _TEST.match(n):
                issues.append(f"test/trial data inside the system (never save tests): {base}/{n}")
    for h in storage.list_dir("creators"):
        for d, rel in layout.reel_dirs(storage, h):
            if d in seen:
                issues.append(f"duplicate reel {d}: {seen[d]} and {rel}")
            seen[d] = rel
            if not storage.exists(f"{rel}/reel.json"):
                issues.append(f"unfinished (no reel.json): {rel}")
                continue
            r = storage.read_json(f"{rel}/reel.json")
            if r.get("layout_version") != 2:
                issues.append(f"old layout (no layout_version 2): {rel}")
            code = shortcode(r.get("link", ""))
            if code and code != d.removeprefix("reel-") and r.get("reel_id") != code:
                issues.append(f"folder name {d} is not the reel code {code}: {rel}")
            for p in r.get("dna", []):
                if not storage.exists(p):
                    issues.append(f"{rel}: DNA file missing {p}")
    for c in storage.list_dir("clients"):
        for v in storage.list_dir(f"clients/{c}/videos"):
            issues += clients.check_made_from(storage, f"clients/{c}/videos/{v}")
    seen_hash = {}
    for i in library.load(storage):
        if i.get("file") and not storage.exists(i["file"]):
            issues.append(f"library item without file: {i['id']}")
        h = (i.get("fingerprint") or {}).get("sha256")
        if h and h in seen_hash and seen_hash[h] != i["id"]:
            issues.append(f"library exact duplicate: {i['id']} = {seen_hash[h]}")
        if h:
            seen_hash[h] = i["id"]
    return issues
