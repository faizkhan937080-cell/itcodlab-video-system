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
