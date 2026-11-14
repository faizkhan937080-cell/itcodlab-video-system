"""Token saver: wait for a GitHub Actions run INSIDE the script (no tokens while waiting) and print ONE line,
plus the last 20 log lines only when it failed. Replaces repeated `gh run list` polling and timers by Claude."""
import json
import subprocess
import time


def _gh(args):
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def latest(workflow, repo):
    rc, out = _gh(["api", f"repos/{repo}/actions/workflows/{workflow}/runs?per_page=1"])
    runs = json.loads(out).get("workflow_runs", []) if rc == 0 else []
    return runs[0] if runs else None


def brief(workflow, repo, wait_min=0, poll_s=30, tail=20, sleep=time.sleep, now=time.time):
    end = now() + wait_min * 60
    while True:
        r = latest(workflow, repo)
        if r and r["status"] == "completed":
            break
        if now() >= end:
            return f"{workflow}: still {r['status'] if r else 'none'} (run {r['id'] if r else '-'})"
        sleep(poll_s)
    line = f"{workflow}: {r['conclusion']} run {r['id']}"
    if r["conclusion"] != "success":
        rc, out = _gh(["run", "view", str(r["id"]), "--repo", repo, "--log-failed"])
        line += "\n" + "\n".join(out.splitlines()[-tail:])
    return line
