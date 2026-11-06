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


def json_default(o):
    """numpy numbers/arrays (and sets) are not JSON by default: convert them instead of crashing a whole analysis."""
    if hasattr(o, "item") and getattr(o, "shape", None) == ():
        return o.item()
    if hasattr(o, "tolist"):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")


def to_native(o):
    """Deep copy where numpy numbers/arrays (also as dict keys), tuples and sets become plain Python.
    Anything that goes into json.dumps without default= must pass through this first (lessons/core.md)."""
    if isinstance(o, dict):
        return {(k.item() if hasattr(k, "item") and getattr(k, "shape", None) == () else k): to_native(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_native(x) for x in o]
    if isinstance(o, (set, frozenset)):
        items = [to_native(x) for x in o]
        try:
            return sorted(items)
        except TypeError:
            return items
    if hasattr(o, "item") and getattr(o, "shape", None) == ():
        return o.item()
    if hasattr(o, "tolist"):
        return to_native(o.tolist())
    return o


def write_json_local(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=json_default)
    return path


def fmt_ts(seconds):
    m, s = divmod(max(0.0, float(seconds)), 60)
    return f"{int(m):02d}:{s:04.1f}"


# ---- stage timers (17-speed): how long each stage takes, so a speed claim is seconds saved at equal output ----
import contextlib as _cl
import threading as _th

_TIMES, _TLOCK = {}, _th.Lock()


@_cl.contextmanager
def stage(name):
    t0 = time.time()
    try:
        yield
    finally:
        dt = round(time.time() - t0, 1)
        with _TLOCK:
            _TIMES[name] = round(_TIMES.get(name, 0) + dt, 1)
        log(f"stage {name}: {dt}s")


def stage_times(reset=False):
    with _TLOCK:
        out = dict(_TIMES)
        if reset:
            _TIMES.clear()
    return out
