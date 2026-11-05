# state (rewrite this file when state changes; history lives in memory/log)
keys: state now pending next jobs
updated: 2026-11-06 (UTC 21:1x on 11-05)
## Jobs
- test-render-001 render DONE. reel-DeoxIgMPlS analyze FAILED (old whisper bug). reel-DeoxIgMPlS-b AWAIT_GATE2 (old small tiles, superseded).
- reel-DeoxIgMPlS-c: collages had red/blue swapped (DO_NOT_USE marker in Drive). reel-DeoxIgMPlS-d analyze AWAIT_GATE2: 7 color-fixed collages in Drive analysis/reel-DeoxIgMPlS-d/pack. review push FAILED 403. THIS is the job for gate 2.
## Gate status
- Gate 1 Y given. Gate 2 NOT answered. Claude has not yet SEEN the -c collages (only a phone photo of the old ones). No gate2 approval until seen + Faiz Y.
## Blocked on (human step)
- Faiz must give the Colab GitHub fine-grained token Contents: Read and write (edit permissions; value unchanged). Worker then retries by itself within ~2 min; then ./run review-fetch reel-DeoxIgMPlS-d --out <dir>.
## Open
- Daily job cap (5) probably reached today UTC; next new job after 05:30 IST.
- Whisper small + rerun untested on real audio until -c summary is read.
- Gemini key optional; GitHub token pasted earlier -> regenerate after setup; _connector_test_bands.png awaits his OK; GCP VM after card.
