"""Shared helpers. There are NO delete helpers on purpose (nothing is ever deleted)."""
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def limits():
    return load_json(CONFIG / "limits.json")


def drive_cfg():
    return load_json(CONFIG / "drive.json")


def brand():
    return load_json(CONFIG / "brand.json")


def workdir():
    p = Path(os.environ.get("ITCOD_WORK", str(ROOT / "work")))
    p.mkdir(parents=True, exist_ok=True)
    return p


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def tail(text, n=None):
    """Last n lines only (limits.claude.error_log_tail_lines). Keeps tokens low."""
    n = n or limits()["claude"]["error_log_tail_lines"]
    return "\n".join((text or "").strip().splitlines()[-n:])


def run_cmd(cmd, timeout=None, cwd=None, env=None):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env)
    return r.returncode, r.stdout, r.stderr


def write_json_local(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


def fmt_ts(seconds):
    m, s = divmod(max(0.0, float(seconds)), 60)
    return f"{int(m):02d}:{s:04.1f}"
