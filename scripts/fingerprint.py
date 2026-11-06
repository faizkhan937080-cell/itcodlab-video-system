"""Content fingerprints for the asset library. Names never decide 'same'. Four tiers:
exact (same bytes) / near (re-encode, level change: same item) / variant (micro change: keep both, linked) / different.
Audio descriptor = level-free spectrum shape + loudness envelope + duration. Image = 64-bit difference hash."""
import hashlib
from pathlib import Path

NEAR = 0.06      # distance at or below: same item (re-encoded, gain changed)
VARIANT = 0.45   # above NEAR up to this: a variant (different mix/EQ/edit): kept as its own item, linked
AUDIO_EXT = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def audio_descriptor(path, bands=24, chunks=8):
    import librosa
    import numpy as np
    y, sr = librosa.load(str(path), sr=22050, mono=True)
    dur = float(len(y)) / sr if sr else 0.0
    if len(y) < 2048:
        return {"kind": "audio", "dur": round(dur, 3), "spec": [0.0] * bands, "env": [0.0] * chunks}
    mel = librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=sr, n_mels=bands) + 1e-10)
    spec = mel.mean(axis=1)
    spec = (spec - spec.mean()) / (spec.std() + 1e-6)  # level free
    parts = np.array_split(y, chunks)
    env = np.array([20 * np.log10(np.sqrt(np.mean(p ** 2)) + 1e-9) for p in parts])
    env = env - env.mean()  # level free
    return {"kind": "audio", "dur": round(dur, 3), "spec": [round(float(x), 3) for x in spec],
            "env": [round(float(x), 2) for x in env]}


def image_descriptor(path):
    from PIL import Image
    im = Image.open(path).convert("L")
    w, h = im.size
    px = list(im.resize((9, 8)).getdata())
    bits = 0
    for r in range(8):
        for c in range(8):
            bits = (bits << 1) | (1 if px[r * 9 + c] > px[r * 9 + c + 1] else 0)
    return {"kind": "image", "dhash": f"{bits:016x}", "w": w, "h": h}


def fingerprint(path, type_=None):
    p = Path(path)
    fp = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    ext = p.suffix.lower()
    try:
        if ext in AUDIO_EXT:
            fp["d"] = audio_descriptor(p)
        elif ext in IMAGE_EXT:
            fp["d"] = image_descriptor(p)
    except Exception as e:  # noqa: BLE001  (unreadable media: only the exact tier can apply)
        fp["d_error"] = type(e).__name__
    return fp


def distance(a, b):
    """0 = same sound/picture, 1 = unrelated. None when the two cannot be compared (then only 'exact' can apply)."""
    if not a or not b or a.get("kind") != b.get("kind"):
        return None
    if a["kind"] == "image":
        return bin(int(a["dhash"], 16) ^ int(b["dhash"], 16)).count("1") / 64.0
    ds = sum(abs(x - y) for x, y in zip(a["spec"], b["spec"])) / len(a["spec"])
    de = sum(abs(x - y) for x, y in zip(a["env"], b["env"])) / len(a["env"]) / 12.0
    d = 0.5 * ds + 0.5 * de
    if max(a["dur"], b["dur"]) > 0 and abs(a["dur"] - b["dur"]) / max(a["dur"], b["dur"]) > 0.03:
        d += 0.2  # different length (trimmed/extended) can never be 'near': at best a variant
    return round(min(1.0, d), 4)


def classify(fp_new, fp_old):
    if fp_new.get("sha256") == fp_old.get("sha256"):
        return "exact", 0.0
    d = distance(fp_new.get("d"), fp_old.get("d"))
    if d is None:
        return "different", None
    if d <= NEAR:
        return "near", d
    if d <= VARIANT:
        return "variant", d
    return "different", d


def better(fp_new, fp_old):
    """True when the new file is the higher quality copy (more bytes per second / larger picture)."""
    dn, do = fp_new.get("d") or {}, fp_old.get("d") or {}
    if dn.get("kind") == "image" and do.get("kind") == "image":
        return dn["w"] * dn["h"] > do["w"] * do["h"]
    if dn.get("kind") == "audio" and do.get("kind") == "audio" and dn["dur"] and do["dur"]:
        return fp_new["bytes"] / dn["dur"] > fp_old["bytes"] / do["dur"]
    return fp_new["bytes"] > fp_old["bytes"]
