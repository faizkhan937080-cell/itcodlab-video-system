# state (rewrite this file when state changes; history lives in memory/log)
keys: state now pending next jobs
updated: 2026-11-06 03:30 IST
## Jobs (Drive jobs/state JSONs are the ledger; scrap packs were trashed)
- test-render-001 DONE (outputs trashed). reel-DeoxIgMPlS FAILED, -b, -c superseded (folders trashed).
- reel-DeoxIgMPlS-d analyze AWAIT_GATE2, folder analysis/reel-DeoxIgMPlS-d (old layout), color-fixed, 7 collages. review push 403.
## Gate status
- Gate 1 Y given. Gate 2 NOT answered. Claude has NOT seen any correct collage yet.
## Blocked on (human step)
- Faiz: GitHub fine-grained token needs Contents: Read and write (value unchanged). Worker retries with backoff, then ./run review-fetch <job> --out <dir>.
## Next
- Daily cap (5) is used up until 00:00 UTC (05:30 IST). Then send reel-DeoxIgMPlS-e (same link, mode both, target creator:auto) so the pack lands in analysis/creators/sahilverma.ai/<job>/ ; then trash -d (scrap). Skip -e if token fix already let Claude review -d AND Faiz prefers to keep -d.
- After collages seen: gate 2 Y/N -> candidates editing+scripting+sound -> gate 3 -> dna/creators/sahilverma.ai/...
## Open
- Whisper small text is Devanagari phonetic; ok as gist only.
- Sheet keeps history rows of trashed jobs (harmless). GCP VM after card. Gemini key optional.
- Regenerate the old pasted GitHub token after setup.
