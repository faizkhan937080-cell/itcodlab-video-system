"""./run doctor : PASS / WARN / FAIL list of everything the pipeline needs."""
import importlib
import os
import shutil
import sys

from .common import run_cmd

REQUIRED_BIN = ["ffmpeg", "ffprobe"]
RECOMMENDED_BIN = ["yt-dlp", "node", "npm", "rclone", "tesseract"]
REQUIRED_PY = ["cv2", "numpy", "PIL", "skimage", "jsonschema"]
RECOMMENDED_PY = ["librosa", "gspread", "google.auth", "faster_whisper", "pytesseract", "anthropic"]


def _ver(cmd):
    rc, out, err = run_cmd(cmd)
    text = (out or err).strip().splitlines()
    return text[0][:80] if text else ""


def run():
    rows, failed = [], False

    def add(level, name, detail=""):
        nonlocal failed
        rows.append((level, name, detail))
        if level == "FAIL":
            failed = True

    add("PASS" if sys.version_info >= (3, 9) else "FAIL", "python", sys.version.split()[0])
    for b in REQUIRED_BIN + RECOMMENDED_BIN:
        path = shutil.which(b)
        if path:
            flag = "-version" if b in ("ffmpeg", "ffprobe") else "--version"
            add("PASS", b, _ver([b, flag]))
        else:
            add("FAIL" if b in REQUIRED_BIN else "WARN", b, "not found")
    if shutil.which("node"):
        major = int(_ver(["node", "--version"]).lstrip("v").split(".")[0] or 0)
        add("PASS" if major >= 18 else "WARN", "node >= 18", f"v{major}")
    for m in REQUIRED_PY + RECOMMENDED_PY:
        try:
            importlib.import_module(m)
            add("PASS", f"py:{m}")
        except Exception:
            add("FAIL" if m in REQUIRED_PY else "WARN", f"py:{m}", "not installed")
    root = os.environ.get("ITCOD_DRIVE_ROOT")
    remote = os.environ.get("ITCOD_RCLONE_REMOTE")
    if root and os.path.isdir(root):
        add("PASS", "drive root", root)
    elif remote:
        add("PASS", "rclone remote", remote)
    else:
        add("WARN", "drive", "set ITCOD_DRIVE_ROOT (mounted Drive) or ITCOD_RCLONE_REMOTE")
    if os.environ.get("GEMINI_API_KEY"):
        add("PASS", "GEMINI_API_KEY", "frame descriptions on")
    else:
        add("WARN", "GEMINI_API_KEY", "not set: collages stay images only (no text descriptions)")
    free_gb = shutil.disk_usage(".").free / 1e9
    add("PASS" if free_gb >= 30 else "WARN", "free disk", f"{free_gb:.0f} GB")
    for level, name, detail in rows:
        print(f"{level:5} {name:18} {detail}")
    print("\nRESULT:", "FAIL (fix the FAIL lines)" if failed else "OK")
    return 1 if failed else 0
