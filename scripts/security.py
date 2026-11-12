"""Security system (rules: rulebooks/15-security.md). It checks the repo, the workflows, the guard files themselves and every file we
bring in. Pure checks + optional ClamAV. `./run security` prints one short verdict; CI runs it weekly and on every push.
Nothing here deletes anything."""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from .common import ROOT, limits
from .mem import has_secret
from .netguard import sniff

INTEGRITY = ROOT / "config" / "integrity.json"
# the files that keep us safe: a silent change to any of them is a finding until the baseline is renewed on purpose
CRITICAL = ["scripts/guard.py", "scripts/netguard.py", "scripts/security.py", "scripts/mem.py", "config/network.json",
            ".github/workflows/worker.yml", ".github/workflows/backup.yml", ".github/workflows/security.yml", ".claude/settings.json"]
TEXT_EXT = (".py", ".md", ".json", ".yml", ".yaml", ".ts", ".tsx", ".txt", ".sh", ".toml", ".cfg", ".html", ".css")
USES = re.compile(r"uses:\s*([\w./-]+)@(\S+)")
INJECT = re.compile(r"\$\{\{\s*github\.(event\.(issue|pull_request|comment|review|head_commit|commits)[\w.\[\]*]*|head_ref)\s*\}\}")
PIPE_SH = re.compile(r"(curl|wget)[^\n|]*\|\s*(sudo\s+)?(ba)?sh")


def tracked_files(root=ROOT):
    r = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True)
    return [root / p for p in r.stdout.split("\n") if p]


def scan_secrets(root=ROOT, files=None):
    """-> [file:line] where a token/key/card pattern sits. Never returns the secret itself."""
    out = []
    for f in files or tracked_files(root):
        if f.suffix.lower() not in TEXT_EXT or not f.exists() or f.stat().st_size > 2_000_000:
            continue
        if f.name == "mem.py" or f.name == "test_guard.py" or "tests" in f.parts:
            continue                     # the detector's own patterns / test fixtures
        try:
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").split("\n"), 1):
                if has_secret(line):
                    out.append(f"{f.relative_to(root)}:{i}")
        except OSError:
            pass
    return out


def audit_workflows(root=ROOT):
    """GitHub Actions hygiene: pinned actions, least permissions, no injection, no pipe-to-shell, no pull_request_target."""
    out = []
    for f in sorted((Path(root) / ".github" / "workflows").glob("*.y*ml")):
        txt = f.read_text(encoding="utf-8")
        name = f.name
        for m in USES.finditer(txt):
            first_party = m.group(1).startswith(("actions/", "github/"))      # GitHub's own actions: a major tag is accepted
            if not first_party and not re.fullmatch(r"[0-9a-f]{40}", m.group(2)):
                out.append({"level": "warn", "file": name, "msg": f"action {m.group(1)}@{m.group(2)} is not pinned to a commit"})
        if "permissions:" not in txt:
            out.append({"level": "warn", "file": name, "msg": "no explicit permissions block"})
        if "pull_request_target" in txt:
            out.append({"level": "fail", "file": name, "msg": "pull_request_target is not allowed"})
        if INJECT.search(txt):
            out.append({"level": "fail", "file": name, "msg": "untrusted GitHub event text used inside a run step"})
        if PIPE_SH.search(txt):
            out.append({"level": "fail", "file": name, "msg": "downloads and runs a script in one step"})
    return out


def file_hash(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def integrity(root=ROOT, baseline_path=INTEGRITY):
    """Compare the critical files with config/integrity.json. -> [{file, msg}]"""
    base = json.loads(Path(baseline_path).read_text(encoding="utf-8")) if Path(baseline_path).exists() else {}
    out = []
    for rel in CRITICAL:
        p = Path(root) / rel
        if not p.exists():
            if rel in base:
                out.append({"file": rel, "msg": "critical file is missing"})
            continue
        if rel not in base:
            out.append({"file": rel, "msg": "not in the baseline"})
        elif base[rel] != file_hash(p):
            out.append({"file": rel, "msg": "changed since the baseline (run `./run security --baseline` after you checked the change)"})
    return out


def write_baseline(root=ROOT, baseline_path=INTEGRITY):
    data = {rel: file_hash(Path(root) / rel) for rel in CRITICAL if (Path(root) / rel).exists()}
    Path(baseline_path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


# ------------------------------------------------------------------ files we bring in
class SecurityError(RuntimeError):
    pass


def clam_scan(path):
    """ClamAV if installed on this machine. -> {'status': 'clean'|'infected'|'unavailable', 'detail': str}"""
    import time
    flag = Path("/tmp/itcod/clam.installing")   # the worker installs the scanner in the background (worker.yml)
    t0 = time.time()
    while flag.exists() and time.time() - t0 < 600:
        time.sleep(3)
    exe = shutil.which("clamscan")
    if not exe:
        return {"status": "unavailable", "detail": "clamscan not installed here"}
    r = subprocess.run([exe, "--no-summary", "-i", str(path)], capture_output=True, text=True, timeout=1800)
    if r.returncode == 0:
        return {"status": "clean", "detail": ""}
    if r.returncode == 1:
        return {"status": "infected", "detail": (r.stdout or "").strip()[:300]}
    return {"status": "unavailable", "detail": (r.stderr or "scan error")[:200]}


def vet_file(path, kind, lim=None, scanner=None):
    """Check one incoming file BEFORE anything uses it. kind: video|audio|image|font|pdf|model.
    -> {'ok': bool, 'problems': [...], 'clam': status}. Executables, archives, wrong type, too big, or infected = not ok."""
    lim = lim or limits()
    from .common import load_json
    cap = load_json(ROOT / "config" / "network.json")["download"]["max_mb"].get(kind, 50) * 1024 * 1024
    p = Path(path)
    problems = []
    if not p.exists() or p.stat().st_size == 0:
        return {"ok": False, "problems": ["file missing or empty"], "clam": "n/a"}
    if p.stat().st_size > cap:
        problems.append(f"{p.stat().st_size // 1048576} MB is over the {cap // 1048576} MB limit for {kind}")
    with open(p, "rb") as f:
        got, danger = sniff(f.read(512))
    if danger:
        problems.append(f"file is a {danger}")
    elif kind not in ("model", "other") and got not in (kind, "unknown") and not (kind == "video" and got == "audio"):
        problems.append(f"expected {kind} but it looks like {got}")
    cl = (scanner or clam_scan)(p)
    if cl["status"] == "infected":
        problems.append("virus scanner: " + cl["detail"])
    return {"ok": not problems, "problems": problems, "clam": cl["status"]}


def require_safe(path, kind, **kw):
    v = vet_file(path, kind, **kw)
    if not v["ok"]:
        raise SecurityError(f"{Path(path).name} refused: " + "; ".join(v["problems"]))
    return v


# ------------------------------------------------------------------ everything
def report(root=ROOT):
    """-> {'verdict': 'OK'|'WARN'|'FAIL', 'secrets': [...], 'workflows': [...], 'integrity': [...], 'net': {...}}"""
    sec = scan_secrets(root)
    wf = audit_workflows(root)
    integ = integrity(root)
    fail = bool(sec) or any(w["level"] == "fail" for w in wf) or bool(integ)
    warn = any(w["level"] == "warn" for w in wf)
    return {"verdict": "FAIL" if fail else ("WARN" if warn else "OK"), "secrets": sec, "workflows": wf, "integrity": integ}
