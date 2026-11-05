# 06 fence, barriers, alerts (read with 00-core before any task)

Faiz does not want Claude's tokens spent on work that scripts or Colab can do. Three lanes, no crossing.

## Lanes
- CLAUDE (brain): writes/fixes code, scene plans, DNA candidates, job + approval files, reads collages
  and `metrics_summary.json`, decides coding questions, keeps memory/lessons.
- WORKER (Colab now, VM later): download, frame analysis, dedup, collages, audio, whisper, OCR, render,
  upload, review publish, retries, self-update, Sheet mirror. It reports back in `jobs/state/<id>.json`.
- FAIZ: Y/N at gates, folder layout, spending, deleting, human-only clicks (popups, token permissions).
- Wrong lane = stop. Claude never runs ffmpeg, yt-dlp, whisper, rclone, curl, remotion. Hook blocks it (scripts/guard.py).

## Token economy (Claude)
- Waiting for the worker: ONE sleep (max ~9 min) then ONE state read. Never loop reads. Never poll logs.
- Read state (1 KB) first. Open `metrics_summary.json` (10 KB) only at gate 2/3. Never read full per-frame files.
- Failed job: read `error_tail` once (20 lines). Fix the cause or alert Faiz. Never re-run to "see".
- Colab does its jobs and reports; Claude does not redo them in the sandbox.

## Barriers (STOP = do nothing more, tell Faiz in 1-3 lines)
- STOP: a human-only step is needed (popup, token permission, card) -> give ONE step, exact button names.
- STOP: job FAILED after 2 retries; daily cap reached; `jobs/state/_worker_alert.json` exists.
- STOP: Claude has not seen the collages (review branch) -> no gate 2 question, no DNA candidate.
- STOP: tests fail -> no push. Secret in a command/file -> blocked, warn Faiz to regenerate it.
- STOP: any delete not on Faiz's approved list (see 00-core "Nothing is deleted").
- No success claims without proof: read the state file, run the test, view the image.

## Alerts (what Faiz hears)
- Format: `ALERT <what> | need: <one step>`; plain Hinglish, no code. Only when Claude cannot fix it itself.
- INFO (no alert): retries, self-update, review retry, cap not yet reached.
- Worker raises alerts by writing state notes (`NEEDS_INPUT`, `FAILED`, `_worker_alert`). Claude relays one line.

## Loopholes already closed (do not reopen)
- Bad code push: worker import-checks after pull and rolls back (`_self_update`).
- Review branch holds only the newest job (force push); retries stop after 4.
- Finished jobs are not re-read each poll. Deleting state files would reset the daily cap: keep job JSONs.
