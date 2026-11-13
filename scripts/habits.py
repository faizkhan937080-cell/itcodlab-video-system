"""Tiny always-on survey for Claude's own work: mistakes + token habits. Silent when clean (costs ~0 tokens).
Entry points: `./run check [--quiet]`, `./run test [files]` (skips a full suite that already passed on this exact tree),
`./run guard-install` (makes the guard hook active whatever folder Claude starts in).
The guard (scripts/guard.py) appends one line per blocked/counted call to ~/.cache/itcod/guard.log."""
import hashlib
import json
import time
from pathlib import Path

from .common import ROOT, run_cmd

CACHE = Path.home() / ".cache" / "itcod"
LOG = CACHE / "guard.log"
STATE = CACHE / "check.json"
GREEN = CACHE / "tests_green.txt"
MAX_RULE_LINES = 60
MANY_CALLS = 120   # tool calls since the last check that suggest batching/fewer round trips


def _state():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def _log_since(ts):
    rows = {}
    try:
        for line in LOG.read_text().splitlines():
            t, _, rule = line.partition(" ")
            if float(t) >= ts:
                rows[rule] = rows.get(rule, 0) + 1
    except (OSError, ValueError):
        pass
    return rows


def _git(*args):
    rc, out, _ = run_cmd(["git", "-C", str(ROOT), *args], timeout=30)
    return out.strip() if rc == 0 else ""


def survey(root=ROOT):
    """-> list of 'what | fix' strings (empty = all fine)."""
    out = []
    long = []
    for pat in ("rulebooks/*.md", "lessons/*.md", "memory/**/*.md", "CLAUDE.md"):
        for p in root.glob(pat):
            try:
                n = len(p.read_text(encoding="utf-8").splitlines())
            except OSError:
                continue
            if n > MAX_RULE_LINES:
                long.append(f"{p.relative_to(root)}({n})")
    if long:
        out.append("rule/memory file over 60 lines: " + ", ".join(long[:4]) + " | fix: split or condense")
    from . import tripwire
    h = tripwire.current_halt()
    if h:
        out.append(f"HALT {h['reason']}: {h.get('detail', '')} | fix: ./run learn / repair tracking, then ./run halt clear")
    out += [("rule gap: " + x + " | fix: add the enforcer (guard/test/worker) or fix the reference") for x in tripwire.verify_registry()[:2]]
    dirty = _git("status", "--porcelain")
    if dirty:
        out.append(f"{len(dirty.splitlines())} uncommitted file(s) | fix: commit+push after the full test, then ./run story")
    ahead = _git("rev-list", "--count", "origin/main..HEAD")
    if ahead not in ("", "0"):
        out.append(f"{ahead} commit(s) not pushed | fix: git push origin HEAD:main")
    st = _state()
    rows = _log_since(st.get("ts", time.time() - 7200))
    calls = rows.pop("call", 0)
    if rows:
        out.append("guard stopped me: " + ", ".join(f"{k} x{v}" for k, v in sorted(rows.items())) +
                   " | fix: use ./run commands, not raw tools (06-fence)")
    if calls > MANY_CALLS:
        out.append(f"{calls} tool calls since last check | fix: batch commands, fewer round trips")
    CACHE.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"ts": time.time()}))
    return out[:5]


def tree_hash():
    parts = [_git("rev-parse", "HEAD"), _git("diff", "HEAD")]
    for f in sorted(_git("ls-files", "-o", "--exclude-standard").splitlines()):
        try:
            parts.append(f + hashlib.sha256((ROOT / f).read_bytes()).hexdigest())
        except OSError:
            pass
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def run_tests(files=None):
    """Targeted files always run. The full suite is skipped when it already passed on this exact tree."""
    h = tree_hash()
    if not files:
        try:
            if GREEN.read_text().strip() == h:
                print("tests: full suite already green for this exact tree (skipped, no tokens spent)")
                return 0
        except OSError:
            pass
    rc, out, err = run_cmd(["python3", "-m", "pytest", "-q", "-x", *(files or ["tests"])], timeout=900)
    tail = "\n".join((out + err).strip().splitlines()[-4:])
    print(tail)
    if rc == 0 and not files:
        CACHE.mkdir(parents=True, exist_ok=True)
        GREEN.write_text(h)
    return 0 if rc == 0 else 1


def install_global_hook(root=ROOT):
    """Merge the guard + survey hooks into ~/.claude/settings.json so they fire even when Claude starts outside the repo."""
    f = Path.home() / ".claude" / "settings.json"
    try:
        cfg = json.loads(f.read_text()) if f.exists() else {}
    except ValueError:
        cfg = {}
    hooks = cfg.setdefault("hooks", {})
    cd = f'cd "{root}" && '
    want = {
        "PreToolUse": {"matcher": "Bash|Write|Edit|Read|SendUserFile",
                       "hooks": [{"type": "command", "command": cd + "python3 -m scripts.guard"}]},
        "UserPromptSubmit": {"hooks": [{"type": "command", "command": cd + "./run check --quiet"}]},
    }
    changed = []
    for ev, entry in want.items():
        cur = hooks.setdefault(ev, [])
        if not any("scripts.guard" in json.dumps(e) or "run check" in json.dumps(e) for e in cur):
            cur.append(entry)
            changed.append(ev)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(cfg, indent=2))
    return changed
