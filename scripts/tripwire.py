"""Tripwire (Faiz 2026-11-14): a written rule must be ENFORCED, and a broken tracking/learning feed must STOP the system.
- Registry config/rules.json: every hard rule names its enforcer (guard | test | worker | check). `verify_registry()` fails when
  the enforcer text is not found in the repo, `none` is listed openly (visible loophole, not a silent one).
- Halt: `jobs/state/_halt.json` on Drive (worker stops taking new jobs) + ~/.cache/itcod/halt.json (Claude's guard allows only
  fix/learn commands). Reasons: tracking_failed (cost row not written), learning_needed (a job FAILED with no lesson yet).
- Scope: `./run scope set <paths>` limits Write/Edit to those paths for N hours (wrong-track work is blocked by the guard).
"""
import json
import re
import time
from pathlib import Path

from .common import ROOT

CACHE = Path.home() / ".cache" / "itcod"
HALT = CACHE / "halt.json"
SCOPE = CACHE / "scope.json"
RULES = ROOT / "config" / "rules.json"
HALT_REL = "jobs/state/_halt.json"
KINDS = {"guard", "test", "worker", "check", "none"}
# While halted Claude may still fix the system and feed the learning; nothing that starts new work.
HALT_OK = re.compile(r"^\s*(\./run\s+(learn|halt|check|mem|story|test|rules|scope|guard-install)\b|git\s+(status|diff|log|add|commit|push|pull)\b|"
                     r"(ls|cat|head|tail|grep|sed|wc|sleep|python3\s+-m\s+pytest)\b)")
HALT_WRITE_OK = ("lessons/", "memory/", "rulebooks/", "scripts/", "tests/", "config/")


# ---------------------------------------------------------------- halt
def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def raise_halt(reason, detail="", storage=None):
    row = {"status": "HALT", "reason": reason, "detail": str(detail)[:300], "since": _now()}
    CACHE.mkdir(parents=True, exist_ok=True)
    HALT.write_text(json.dumps(row), encoding="utf-8")
    if storage is not None:
        try:
            storage.write_state(HALT_REL, dict(row, id="_halt", updated=row["since"]))
        except Exception:  # noqa: BLE001
            pass   # the local stop still holds; the worker is stopped by the next successful write
    return row


def current_halt():
    try:
        return json.loads(HALT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def worker_halt(storage):
    """Reason string when the worker must not take new jobs, else None."""
    try:
        row = storage.read_json(HALT_REL)
    except Exception:  # noqa: BLE001
        return None
    return (row or {}).get("reason") if (row or {}).get("status") == "HALT" else None


def worker_halt_listed(worker, states):
    """Same as worker_halt but costs no extra Drive call: look at the state listing the worker already fetched."""
    if not states or "_halt.json" not in states:
        return None
    seen = getattr(worker, "_halt_seen", None)
    if seen and seen[0] == states["_halt.json"]:
        return seen[1]
    reason = worker_halt(worker.storage)
    worker._halt_seen = (states["_halt.json"], reason)
    return reason


def clear_halt(storage=None, reason=None):
    h = current_halt()
    if h is None or (reason and h.get("reason") != reason):
        return False
    if HALT.exists():
        HALT.replace(HALT.with_suffix(".cleared"))
    if storage is not None:
        try:
            storage.write_state(HALT_REL, {"id": "_halt", "status": "CLEAR", "updated": _now()})
        except Exception:  # noqa: BLE001
            pass
    return True


def record_checked(storage, job_id, kind, **kw):
    """costs.record that cannot fail silently: no cost row written = tracking_failed halt."""
    from . import costs
    path = costs.record(storage, job_id, kind, **kw)
    if not path:
        raise_halt("tracking_failed", f"{job_id} {kind}: cost row not written", storage)
    return path


def halt_for_failed_job(job_id, stage, storage=None):
    """A job reached FAILED: the lesson must be written before new work starts."""
    return raise_halt("learning_needed", f"{job_id} failed at {stage}: run ./run learn", storage)


def check_halt_bash(cmd):
    h = current_halt()
    if not h or HALT_OK.match(cmd or ""):
        return None
    return (f"HALT ({h['reason']}): {h.get('detail', '')}. Fix it first: `./run learn \"M: .. | C: .. | R: ..\"` for learning_needed; "
            "repair the tracking and `./run halt clear` for tracking_failed. No new work until then.")


def check_halt_write(path):
    h = current_halt()
    if not h:
        return None
    p = str(path or "").replace(str(ROOT) + "/", "")
    return None if p.startswith(HALT_WRITE_OK) else f"HALT ({h['reason']}): only system/lesson files may change until the halt is cleared."


# ---------------------------------------------------------------- scope
def set_scope(paths, hours=6):
    CACHE.mkdir(parents=True, exist_ok=True)
    SCOPE.write_text(json.dumps({"paths": [str(p) for p in paths], "until": time.time() + hours * 3600}), encoding="utf-8")


def clear_scope():
    if SCOPE.exists():
        SCOPE.replace(SCOPE.with_suffix(".cleared"))


def check_scope(path):
    try:
        s = json.loads(SCOPE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if time.time() > s.get("until", 0) or not path:
        return None
    p = str(path).replace(str(ROOT) + "/", "")
    if any(p.startswith(a.rstrip("*")) for a in s["paths"]):
        return None
    return f"SCOPE: {p} is outside this task's paths ({', '.join(s['paths'])}). Wrong track. Ask Faiz or `./run scope clear`."


# ---------------------------------------------------------------- registry + learning
def load_rules():
    try:
        return json.loads(RULES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def verify_registry(root=ROOT):
    """-> list of problems: enforcer text missing in the repo, or rules with no enforcer at all."""
    out, files = [], None
    for r in load_rules():
        kind, ref = (r.get("enforcer") or "none:").split(":", 1) if ":" in (r.get("enforcer") or "") else ("none", "")
        if kind not in KINDS:
            out.append(f"rule {r.get('id')}: unknown enforcer kind '{kind}'")
        elif kind == "none":
            out.append(f"rule {r.get('id')}: written but NOT enforced yet")
        else:
            if files is None:
                files = [p for p in list((root / "scripts").glob("*.py")) + list((root / "tests").glob("*.py"))]
            if not any(ref in p.read_text(encoding="utf-8", errors="ignore") for p in files):
                out.append(f"rule {r.get('id')}: enforcer '{ref}' not found in code")
    return out


def add_lesson(text, rule_id=None, enforcer="none:", root=ROOT):
    """Feed one lesson (M | C | R) into lessons/core.md and, when a rule id is given, into the registry. Clears learning halt."""
    if text.count("|") < 2:
        raise ValueError("lesson must be 'M: mistake | C: cause | R: rule'")
    f = root / "lessons" / "core.md"
    f.write_text(f.read_text(encoding="utf-8").rstrip("\n") + "\n" + text.strip() + "\n", encoding="utf-8")
    if rule_id:
        rules = [r for r in load_rules() if r.get("id") != rule_id]
        rules.append({"id": rule_id, "rule": text.split("R:", 1)[-1].strip(), "enforcer": enforcer, "added": _now()[:10]})
        RULES.write_text(json.dumps(rules, indent=1, ensure_ascii=False), encoding="utf-8")
    clear_halt(reason="learning_needed")
    return str(f)
