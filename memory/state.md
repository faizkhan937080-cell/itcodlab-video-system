# state (rewrite this file when state changes; history lives in memory/log)
keys: state now pending next jobs
updated: 2026-11-06 03:50 IST
## Jobs (Drive jobs/state JSONs are the ledger; scrap packs were trashed)
- test-render-001 DONE (outputs trashed). reel-DeoxIgMPlS FAILED, -b, -c superseded (folders trashed).
- reel-DeoxIgMPlS-d AWAIT_GATE2. Folder MOVED to analysis/creators/sahilverma.ai/reel-DeoxIgMPlS-d (worker follows). Has source.mp4, audio.wav, keyframes/, pack/, dna/ with candidate-scripting-v1 + candidate-sound-v1 (DRAFTS, validated).
## Gate status
- Gate 1 Y given. Gate 2 NOT answered. Claude has NOT seen any correct collage yet (editing DNA blocked).
## Blocked on (human step)
- Faiz: GitHub fine-grained token needs Contents: Read and write (value unchanged). Then ./run review-fetch <job> --out <dir>.
## Next
- Transcript of -d covers only 0-8 s of 58 s (old code). Fixed in code (dual pass + coverage_ratio, commit 96fa3ad). After cap resets (05:30 IST) re-run reel as -e (Gate 1 Y), mode both, folder creator sahilverma.ai; then refine scripting v2 with full transcript.
- Rule Approvals page (Artifact, db): proposals p03 Gate2-split, p04 Remotion headcount wait for Faiz. Read with ArtifactData; write approved ones into rulebooks.
- After collages seen: gate 2 Y/N -> editing candidate -> gate 3 -> dna/creators/sahilverma.ai/...
## Open
- Remotion license: free up to 3 people; ask headcount. Whisper Devanagari is gist only.
- Sheet keeps history rows of trashed jobs (harmless). GCP VM after card. Gemini key optional. Regenerate old pasted GitHub token.
