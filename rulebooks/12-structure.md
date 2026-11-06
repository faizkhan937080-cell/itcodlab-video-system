# Structure, IDs, company folders, licences

## One reel = one ID, company videos, licences (Faiz 2026-11-06 17:13, loophole review)
- Reel ID = Instagram shortcode. Folder `creators/<h>/videos/<code>/` (`creators/_unassigned` if the creator is unknown). `new-job` cleans the link,
  refuses a second job for the same reel (use --rerun). Job ids: `reel-<code>`, retries `-r2`. Never move a folder while the worker runs (`gh run list`).
- Company work: `clients/<company>/{brand,briefs,videos/<video>/}`; each video has `made_from.json` (reel + DNA files pinned by sha256) and `credits.json`.
  `./run clients made-from|gate`. Delivery: gate ALERTS when a licence is not commercial-ok; Faiz's word (`--accept-risk`) lets it pass and is recorded (rulebook 18). Company data never enters creator DNA or another company's video.
- Reference reels: learn the STYLE; never put its footage/music in the output. A 100% clone uses the same NAMED elements from licensed sources.
- Tests/trials are never saved in Drive (names test-/tmp-/scratch- are flagged by `./run audit-links`). Run `./run audit-links` after each job.
- Storage clean-up for space: only on Faiz's command (he decides when).
