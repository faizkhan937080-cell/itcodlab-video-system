# state (rewrite this file when state changes; history lives in memory/log)
keys: state now pending next jobs
updated: 2026-11-07 00:50 IST
## Jobs (Drive jobs/state JSONs = ledger + daily cap; never delete)
- reel-DeoxIgMPlS-g (sahilverma.ai EP-01): DNA saved, DONE (recipe.json/RECIPE.md). Junk measured-*.json in its dna folder still to trash (approved scrap).
- reel-DfWAlgTxEkL-a (general, SFX reel): gate 3 Y given; sound + scripting DNA saved (dna/general/..).
- reel-DfMQ7zqkuxO-b (neuraltech.ai, both): analysis done, gate 2 Y given. DNA candidates v1 editing/scripting/sound pass dna-check, uploaded to Drive creators/neuraltech.ai/videos/DfMQ7zqkuxO/dna/. WAITING gate 3 Y/N from Faiz (asked in chat). Worker then re-checks (recomputes script numbers from transcript.json, b420a84) and saves dna-v1 + recipe card. elements.json not yet written. VM runner itcod-vm online; WORKER_RUNS_ON set.
- Old DeoxIgMPlS, -b, -c, -d, -e, -f: superseded/failed, folders trashed. Cap 5/UTC day (resets 05:30 IST); 6 used 2026-11-06 -> daily_job_cap=6 for TODAY only (revert to 5 after 05:30 IST Nov 7; reminder 05:45 IST).
## Built (all in GitHub main, tests green)
- Scene library + captions + stop-motion + SFX (Openverse); creator layout creators/<h>/{videos,dna,style,ideas,scripts,made}.
- 2026-11-06 17:00-18:00: reel ID = shortcode, link cleaning, _unassigned, clients/ + made_from + licence gate, audit-links, snapshot,
  asset library (4-tier dedupe by content), listen.py (music id + CLAP sound events), resolve, ext-index (company Drive), glossary, backup+manifest.
- 2026-11-06 18:10: colour grade (auto/natural/off, ref look in grade.json) + effects (speed ramp, stabilise, zoom, tracking overlays, reframe, cut-out, voice clean+duck, safe zones, grain/vignette) built; rules 13-grade.md, 14-effects.md. Untested on worker yet: first real render must show grade+effects reports.
- Job reel-DeoxIgMPlS--r2 MEASURED (v2 files OK: transcript, audio, scenes, listen.json). CLAP failed (16 kHz) -> fixed to 48 kHz, pushed. grade.json not seen: check next run. Junk to trash (approved dev scrap): measured-*.json in -g dna folder, style/_batches/pipeline-check; keep state file.
- 2026-11-06 18:20 IST: security/ban-safety system (15-security.md, netguard/security.py, ClamAV, tripwire) + pro-editing QA gate (16-pro-editing.md: qa.py, plan_edit beat snap + J/L, cover.py, CFR/denoise) + Remotion lottie/audio_bars/fit text/new transitions built, 181 tests green, pushed.
- 2026-11-06 18:40 IST: voice micro-analysis (voice.json), word timestamps, parallel ears, rulebook 17-speed.md pushed; 190 tests green. First real run with voice.json still to verify on worker.
- 2026-11-06 19:30 IST: alert-only copyright gate (rulebook 18, Faiz decides) + meme kit (fx, meme_text, sticker; rulebook 14) pushed, 193 tests green. Not yet seen on a real worker run: voice.json, grade.json, listen CLAP events.
## Waiting on Faiz (human only)
- Optional Y/N: import Remotion repos (Remocn/Curvable; reactvideoeditor skipped = paid); LottieFiles in library; Kaggle free GPU worker.
- Keys DONE (GitHub secrets): GEMINI_API_KEY, ACOUSTID_KEY, PIXABAY_KEY (no code uses Pixabay yet). Company Drive link when he has it.
- Optional: Openverse key; Reels benchmark rule Y/N.
- YouTube/Studio connected 19:30 IST (new empty channel); see mem decisions.
- 20:10 IST: sfx --meme-fx built; junk trashed; 194 tests green. New worker code still unverified on a real reel (voice.json, grade.json, listen CLAP).
## Next
- Verify new worker code on a real run (listen CLAP, grade.json, Gemini describe, AcoustID; voice.json worked 22:3x). Remotion first real end-to-end render.
- OWN SERVER: Faiz pastes Cloud Shell block (VM itcod-worker, e2-standard-4, asia-south1-b, scripts/vm/startup.sh; runner token expires ~23:33 IST). Then runner 'itcod-vm' must show Idle; then repo var WORKER_RUNS_ON=["self-hosted","itcod"] (Faiz/Gemini only), wake, test run; add GCP budget alert + auto-stop.
- Rules: rulebooks/12-structure.md. Storage clean-up only on Faiz's command.
- 2026-11-07: layout simplified (reel-<code>/ flat, 7e12622). Gate 3 for -b still pending (Faiz Y/N). Trash batch pending Y/N: 9 junk files, _stale-INDEX-delete.md, empty dna/videos folders. Gemini key 401 -> Faiz must update GEMINI_API_KEY secret.
- 2026-11-08 LTX: pipeline error FIXED (prompt_enhancer null in local model_index; run 22 built LTX2Pipeline). Generate still fails on T4 memory (see lessons). Test spec: trigger/videogen/probe-ltx-gguf.json ("test":true = never saved to Drive).
- 2026-11-08 MiniMax H3: plan in memory/decisions.md. Kernel scripts/videogen_h3.py exists locally, NOT pushed/wired: needs Faiz Y (rulebook 21 gate). After Y: ./run approve-engine, wire mode h3 (diff saved by Claude), run probe.
