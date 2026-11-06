"""Per-creator INDEX: which reel gave which DNA. Rebuilt from creators/<h>/videos/*/reel.json (never edited by hand)."""
from pathlib import PurePosixPath


def rows(storage, handle):
    base = f"creators/{handle}/videos"
    out = []
    for name in sorted(storage.list_dir(base)):
        try:
            r = storage.read_json(f"{base}/{name}/reel.json")
        except Exception:  # noqa: BLE001  (folder without reel.json yet = analysis not finished)
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


def render(handle, reels):
    lines = [f"# {handle}: kaun si reel ka kaun sa DNA", "",
             "| Reel | Link | Date | Mode | DNA files (folder: dna/) | Recipe card |", "|---|---|---|---|---|---|"]
    for r in reels:
        dna = ", ".join(PurePosixPath(p).name for p in r.get("dna", [])) or "-"
        lines.append(f"| {r.get('job', '?')} | {r.get('link', '')} | {str(r.get('saved', ''))[:10]} | {r.get('mode', '')} | {dna} | {r.get('analysis', '')}/RECIPE.md |")
    lines += ["", "Folders: videos/ (reel ka source, collages, metrics) - dna/ (approved DNA, naam mein reel ka naam) - "
              "style/ (poore creator ka clone) - ideas/ - scripts/ - made/ (is style mein bani videos)."]
    return "\n".join(lines) + "\n"


def write_index(storage, handle):
    reels = rows(storage, handle)
    base = f"creators/{handle}"
    storage.put_text(f"{base}/INDEX.md", render(handle, reels), versioned=False)
    storage.put_json(f"{base}/INDEX.json", reels, versioned=False)
    return len(reels)
