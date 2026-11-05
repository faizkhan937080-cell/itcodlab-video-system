# state (rewrite this file when state changes; history lives in memory/log)
keys: state now pending next jobs
updated: 2026-11-06 04:40 IST
## Jobs (Drive jobs/state JSONs are the ledger; scrap packs were trashed)
- test-render-001 DONE (outputs trashed). reel-DeoxIgMPlS FAILED, -b, -c superseded (folders trashed).
- reel-DeoxIgMPlS-d AWAIT_GATE2. Folder MOVED to analysis/creators/sahilverma.ai/reel-DeoxIgMPlS-d (worker follows). Has source.mp4, audio.wav, keyframes/, pack/, dna/ (empty: old v1 drafts trashed, schema is v2 now).
## Gate status
- Gate 1 Y given. Gate 2 NOT answered. Claude has NOT seen any correct collage yet (editing DNA blocked).
## Blocked on (human step)
- Faiz: GitHub fine-grained token needs Contents: Read and write (value unchanged). Then ./run review-fetch <job> --out <dir>.
## Next
- Re-run reel as -e after cap reset 05:30 IST (needs Faiz Y in chat): new code gives full transcript, script_metrics, LUFS. Then ./run dna-draft + judged parts + dna-check.
- Approvals ONLY in chat. Approved: batch asks, creator folders, Gate-2 split (mode audio = sound+scripting), Remotion headcount check.
- Gaps list: memory/decisions/roadmap-gaps.md. After collages seen: gate 2 Y/N -> editing candidate -> gate 3.
## Open
- Remotion license: free up to 3 people; ask headcount. Whisper Devanagari is gist only.
- Sheet keeps history rows of trashed jobs (harmless). GCP VM after card. Gemini key optional. Regenerate old pasted GitHub token.
