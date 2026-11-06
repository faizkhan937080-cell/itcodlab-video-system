# state (rewrite this file when state changes; history lives in memory/log)
keys: state now pending next jobs
updated: 2026-11-06 07:28 IST
## Jobs (Drive jobs/state JSONs are the ledger; scrap packs were trashed)
- test-render-001 DONE (outputs trashed). reel-DeoxIgMPlS FAILED, -b, -c superseded (folders trashed).
- reel-DeoxIgMPlS-g AWAIT_GATE2 (01:04Z): analysis OK (audit pass, LUFS -17.3, transcript full, review branch push OK, collages seen = good). It is sahilverma.ai 'Edit with Claude' EP-01 (paper-cutout/collage style).
- reel-DfWAlgTxEkL-a AWAIT_GATE2 (01:19Z): analysed, transcript matches Faiz's SFX summary, research done, scripts/sfx.py implemented. Cap 4 of 5 used today (UTC).
- reel-DeoxIgMPlS-d AWAIT_GATE2 (old, Colab). Folder MOVED to analysis/creators/sahilverma.ai/reel-DeoxIgMPlS-d (worker follows). Has source.mp4, audio.wav, keyframes/, pack/, dna/ (empty: old v1 drafts trashed, schema is v2 now).
## Gate status
- Gate 1 Y given. Gate 2 NOT answered. Claude has NOT seen any correct collage yet (editing DNA blocked).
## Blocked on (human step)
- Hosting DONE 05:19 IST: RCLONE_TOKEN secret added, workflow perms read+write saved, first Actions run green (7 min). Colab worker still running in Faiz's tab (403 on review push): Faiz asked to Disconnect+delete runtime. Real proof = reel -e job.
- Scheduled task 05:32 IST: queue reel -e (mode audio first) + ./run wake. Then ./run review-fetch <job> --out <dir>.
## Next
- Re-run reel as -e after cap reset 05:30 IST (needs Faiz Y in chat): new code gives full transcript, script_metrics, LUFS. Then ./run dna-draft + judged parts + dna-check.
- Approvals ONLY in chat. Approved: batch asks, creator folders, Gate-2 split (mode audio = sound+scripting), Remotion headcount check.
- Gaps list: memory/decisions/roadmap-gaps.md. After collages seen: gate 2 Y/N -> editing candidate -> gate 3.
## Open
- Remotion license: free up to 3 people; ask headcount. Whisper Devanagari is gist only.
- Sheet keeps history rows of trashed jobs (harmless). GCP VM after card. Gemini key optional. Regenerate old pasted GitHub token.
- 2026-11-05 22:48Z bulk-lite mode implemented and tested (72 tests green); pending: Faiz one-time RCLONE_TOKEN secret, Y/N re-run reel as -e after 05:30 IST, mode audio first
- 06:17 IST: reel jobs -e (audio-only file picked), -f (no ffmpeg on runner, streams not merged) FAILED/NEEDS_INPUT; fixed (pick_source, merge_streams, ffmpeg apt). -g running on Actions. Daily cap UTC: 3 of 5 used (-e -f -g).
- 06:40 IST: Faiz awake (sent new reel). Remotion library done: counter, bar_chart, checklist, split_compare, quote, stroke, paper_cutout + plan.captions + plan.step_fps. Batch rclone upload + whisper loop fix pushed. 88 tests green. Stop heavy work before 06:59 IST (session reset 07:00). Colab runtime deleted (Faiz via Gemini). Gemini in Chrome = how Faiz does web steps.
- Pending (needs Faiz): Y/N Reels benchmark rule; Gemini API key (AI Studio) for text collage descriptions; scene-template library (task 4) next session; Remotion <Video>/GPU-effect/concurrency work only after first real render.
