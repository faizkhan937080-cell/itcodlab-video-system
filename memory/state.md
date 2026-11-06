# state (rewrite this file when state changes; history lives in memory/log)
keys: state now pending next jobs
updated: 2026-11-06 18:10 IST
## Jobs (Drive jobs/state JSONs = ledger + daily cap; never delete)
- reel-DeoxIgMPlS-g (sahilverma.ai EP-01, folder creators/sahilverma.ai/videos/reel-DeoxIgMPlS-g): AWAIT_GATE3 (sound+scripting candidates valid). Waiting Faiz Y/N.
- reel-DfWAlgTxEkL-a (general, SFX reel): AWAIT_GATE2. Waiting Faiz.
- Old DeoxIgMPlS, -b, -c, -d, -e, -f: superseded/failed, folders trashed. Cap 5/UTC day (resets 05:30 IST); 4 used 2026-11-06.
## Built (all in GitHub main, tests green)
- Scene library + captions + stop-motion + SFX (Openverse); creator layout creators/<h>/{videos,dna,style,ideas,scripts,made}.
- 2026-11-06 17:00-18:00: reel ID = shortcode, link cleaning, _unassigned, clients/ + made_from + licence gate, audit-links, snapshot,
  asset library (4-tier dedupe by content), listen.py (music id + CLAP sound events), resolve, ext-index (company Drive), glossary, backup+manifest.
- 2026-11-06 18:10: colour grade (auto/natural/off, ref look in grade.json) + effects (speed ramp, stabilise, zoom, tracking overlays, reframe, cut-out, voice clean+duck, safe zones, grain/vignette) built; rules 13-grade.md, 14-effects.md. Untested on worker yet: first real render must show grade+effects reports.
- Worker run 42213429391 (job reel-DeoxIgMPlS--r2, bulk pipeline-check) running since 17:25 IST: first CLAP download, slow. Check result; trash its junk (measured-*.json, style/_batches/pipeline-check), keep state file.
## Waiting on Faiz (human only)
- Gate 3 Y/N for -g; gate 2 for -a. Gemini key (AI Studio, free) and AcoustID key (free) for the ears. Company Drive link when he has it.
- Optional: Openverse key; Reels benchmark rule Y/N.
## Next
- Verify new worker code on a real run (listen.json, transcript.txt). Remotion first real end-to-end render. GCP VM later (card).
- Rules: rulebooks/12-structure.md. Storage clean-up only on Faiz's command.
