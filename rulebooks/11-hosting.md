# 11 hosting: the worker runs without Faiz's PC

## Now (free, no card): GitHub Actions  (.github/workflows/worker.yml)
- Starts by itself: Claude runs `./run wake` after writing a job, approval or DNA candidate (pushes trigger/wake.txt);
  also a manual "Run workflow" click, and a safety run every 6 hours. Runs until idle 3 min, then stops.
- Drive access: repo secret `RCLONE_TOKEN` (Faiz sets it once, docs/HOSTING.md). Review pack push: built-in token
  (`contents: write`), so the old read-only Colab token problem does not exist here.
- Free quota ~2000 min/month (private repo). A normal analysis ~6-10 min, a 4K render longer. Watch the budget.
- Claude cannot read Actions logs: the worker reports through `jobs/state/<id>.json` and `_worker_alert.json`.
- Risk: Instagram may block GitHub's servers. Then NEEDS_INPUT/FAILED with the yt-dlp tail: use cookies (secret
  `INSTAGRAM_COOKIES`) or Colab for that download. Say it plainly, never retry in a loop.
- No sheet mirror on Actions (`--no-sheet`) until a Sheets credential exists. Drive state files are the truth.

## Later (needs a card): Google Cloud VM  (deploy/gcp/startup.sh)
- e2-standard-8 Ubuntu 22.04, asia-south1. Paste the script as Startup script; token values go in VM custom metadata.
- systemd keeps the worker alive after crash/reboot. Same code, `./run worker --loop`.

## Colab stays as a backup only (needs the tab open).
## After every job/approval/candidate write: `./run wake --reason "<what>"`. No wake = nothing starts until the 6 h run.

## TURBO (GPU VM `itcod-gpu`, label itcod-gpu): ONLY when Faiz says "speed up"
- Default stays the free/normal worker. Turbo = `./run wake --turbo` (commit message has [turbo] -> worker.yml uses the GPU runner).
- VM is normally STOPPED; Faiz (or Gemini) starts it: `gcloud compute instances start itcod-gpu --zone asia-south1-b`. It stops itself after 10 idle min.
- Claude: before `wake --turbo` say in chat "VM chalu karo"; after the work say it will switch itself off. Setup: scripts/vm/gpu_startup.sh.

## VM POWER SWITCH (2026-11-08): Claude starts/stops Google Cloud VMs itself
- `./run vm start|stop|status|describe [name] [--wait]` -> pushes trigger/vm.txt -> workflow vm-power (scripts/vm/power.sh). Default name itcod-gpu. Hourly watchdog stops itcod-gpu after 3 h.
- Login = Workload Identity Federation, NO key/secret: pool github-pool, provider github (only repo faizkhan937080-cell/itcodlab-video-system), acts as vm-power@itcodlab-video.iam.gserviceaccount.com. Project number 11609431528.
- Flow for turbo: `./run vm start itcod-gpu --wait` -> `./run wake --turbo` -> work -> `./run vm stop itcod-gpu` (VM also stops itself after 10 idle min). Tell Faiz in one line at each on/off.
- Pending (needs Faiz or quota): role "Compute Instance Admin (v1)" for vm-power on the project (IAM, I was blocked), L4 GPU quota asia-south1 = 0, itcod-gpu VM not created.
