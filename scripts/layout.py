"""One place that knows where a reel's files live (Faiz 2026-11-07: simple, not deep).

NEW: creators/<h>/reel-<code>/  holds everything of that reel in one folder: source, transcript, voice, listen,
     candidate-<type>-vN.json, measured-<type>.json, reel.json, RECIPE.md, and pack/ (collages + metrics).
OLD: creators/<h>/videos/<code>/ with a dna/ subfolder. Still read, never written for new jobs.
Approved DNA stays in creators/<h>/dna/ (flat, reel in the file name)."""
from pathlib import PurePosixPath

LEGACY = "videos"


def reel_rel(handle, code):
    return f"creators/{handle}/reel-{code}"


def reel_dirs(storage, handle):
    """[(folder name, rel path)] of every reel of a creator: new layout first, then the old videos/ folder."""
    out = [(n, f"creators/{handle}/{n}") for n in storage.list_dir(f"creators/{handle}") if n.startswith("reel-")]
    out += [(n, f"creators/{handle}/{LEGACY}/{n}") for n in storage.list_dir(f"creators/{handle}/{LEGACY}")]
    return out


def is_flat(base):
    p = PurePosixPath(base)
    return p.name.startswith("reel-") and p.parent.name != LEGACY


def cand_dir(base):
    """Folder that holds candidate-*/measured-* files of a reel folder."""
    return base if is_flat(base) else f"{base}/dna"
