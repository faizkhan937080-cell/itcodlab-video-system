"""Let Claude SEE the collages without Faiz downloading anything.

Worker side: publish() copies the pack (collages + metrics + index) to GitHub branch `review`, folder review/<job>/.
Claude side: fetch() reads that branch and writes the files into a local folder, so images can be viewed.
Heavy files (video, frames) stay in Drive. Nothing is ever deleted. Never raises on the worker side.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .common import ROOT, limits, log, run_cmd, tail

KEEP = ("collage_*.jpg", "metrics_summary.json", "manifest.json", "descriptions.json", "video.mp4")


def _scrub(text, url):
    host = url.split("@")[-1] if "@" in url else url
    return text.replace(url, host)


def _git(args, cwd, url="", timeout=180):
    rc, out, err = run_cmd(["git", *args], cwd=str(cwd), timeout=timeout)
    return rc, _scrub(out + err, url)


def publish(pack_dir, job_id, collage_index=None):
    """Copy the pack to branch `review`. The branch always holds ONLY the newest job (force push), so it can
    never grow. Each job has its own scratch repo under work/, reused on retries (nothing is removed)."""
    cfg = limits().get("review", {})
    if not cfg.get("enabled") or os.environ.get("ITCOD_NO_REVIEW"):
        return {"status": "skipped", "reason": "disabled"}
    try:
        rc, url, _ = run_cmd(["git", "-C", str(ROOT), "remote", "get-url", "origin"])
        url = url.strip()
        if rc != 0 or not url:
            return {"status": "skipped", "reason": "no git remote"}
        branch = cfg.get("branch", "review")
        tmp = ROOT / "work" / f"_review_{job_id}"
        tmp.mkdir(parents=True, exist_ok=True)
        if not (tmp / ".git").exists():
            _git(["init", "-q"], tmp)
            _git(["checkout", "-q", "--orphan", branch], tmp)
            _git(["remote", "add", "origin", url], tmp)
        else:
            _git(["remote", "set-url", "origin", url], tmp)
        dest = tmp / "review" / job_id
        dest.mkdir(parents=True, exist_ok=True)
        pack = Path(pack_dir)
        n = 0
        for pat in KEEP:
            for f in sorted(pack.glob(pat)):
                shutil.copy2(f, dest / f.name)
                n += 1
        if collage_index is not None:
            import json
            (dest / "collage_index.json").write_text(json.dumps(collage_index, ensure_ascii=False), encoding="utf-8")
        _git(["add", "-A"], tmp)
        rc, out = _git(["-c", "user.name=itcodlab-worker", "-c", "user.email=worker@itcodlab.local",
                        "commit", "-q", "--allow-empty", "-m", f"review pack {job_id}"], tmp)
        if rc != 0:
            return {"status": "failed", "error": tail(out, 3)}
        rc, out = _git(["push", "-q", "--force", "origin", f"HEAD:{branch}"], tmp, url)
        if rc != 0:
            return {"status": "failed", "error": tail(out, 3), "tries": 1}
        log(f"review pack published: {n} file(s) to branch {branch}")
        return {"status": "ok", "branch": branch, "path": f"review/{job_id}", "files": n}
    except Exception as e:  # noqa: BLE001
        return {"status": "failed", "error": tail(f"{type(e).__name__}: {e}", 3), "tries": 1}


def fetch(job_id, dest, repo=None):
    """Claude side: pull review/<job_id>/ from the review branch into `dest`. Returns list of local files."""
    repo = Path(repo or ROOT)
    branch = limits().get("review", {}).get("branch", "review")
    rc, out, err = run_cmd(["git", "-C", str(repo), "fetch", "-q", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}"], timeout=180)
    if rc != 0:
        raise RuntimeError("fetch failed: " + tail(err, 3))
    rc, listing, err = run_cmd(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", f"origin/{branch}",
                                f"review/{job_id}/"])
    names = [n for n in listing.splitlines() if n.strip()]
    if not names:
        raise RuntimeError(f"nothing on branch {branch} for {job_id}")
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    out_files = []
    for n in names:
        blob = subprocess.run(["git", "-C", str(repo), "show", f"origin/{branch}:{n}"], capture_output=True)
        if blob.returncode != 0:
            continue
        target = dest / Path(n).name
        target.write_bytes(blob.stdout)
        out_files.append(str(target))
    return out_files


if __name__ == "__main__":
    for f in fetch(sys.argv[1], sys.argv[2]):
        print(f)
