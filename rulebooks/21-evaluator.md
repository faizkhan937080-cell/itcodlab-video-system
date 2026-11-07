# 21 expectation evaluator + footage engines (Faiz 2026-11-07)
Code: scripts/evaluator.py, scripts/videogen.py. Commands: `./run evaluate`, `./run approve-engine`, `./run videogen-run`.
## Goal
- Every output must match the reference DNA (editing, scripting, sound) and the quality goal: same look, pace, loudness, realism as the reference.
- Remotion/plan/finish make what code can make. Realistic footage code cannot make comes from a footage engine.
## Protocol: runs after EVERY generation (render, voice, footage), no exceptions
1. Analyse OUR output with the same scripts as the reference (metrics_summary.json) + `qa.run` findings.
2. Claude views the output collage next to the reference collage and writes `footage_needs`: shots code cannot reproduce (realistic scene, real texture, dense graphic). Judge by looking, never invent.
3. `./run evaluate --type <t> --target <dna|corpus.json> --summary <out summary> [--qa qa.json] [--needs needs.json] --state <job>/eval.json`
4. Verdict:
   - PASS: nothing differs. Deliver.
   - FIX plan: numbers differ or a QA fail. Change the plan/scene/finish, re-render (max 2).
   - FIX ltx: shot still missing. Generate it with LTX (free, Kaggle GPU), re-render (max 2).
   - ASK: LTX failed. Ask Faiz in chat, very short, easy Hinglish: "MiniMax H3 use karun? Y/N". Only his Y runs `./run approve-engine minimax --state ...`.
   - FAILED: retries used up. Status FAILED, one line to Faiz, stop.
## Engines (config/pricing.json has rates)
- ltx: LTX-2.5 (22B, Community Licence: free under $10M yearly revenue). Runs on Modal L40S (free $30/month credit; Kaggle T4 14.6 GB and 38 GB model did not fit). No approval.
- wan: Wan 2.2 TI2V-5B (Apache-2.0) on free Kaggle GPU. Light shots, no approval.
- minimax: MiniMax H3 on Modal A100-80GB (credit) after its repo is probed. Needs the licence (UI credit "MiniMax H3", US/EU/UK/Korea excluded, over $20M needs written OK). Only after Faiz's Y per job.
- veo: Google Veo 3.1 (Vertex AI, paid, credit). Only when Faiz commands, script carries "allow_paid": true.
- Never use a paid engine or a free trial of one on my own. Quote cost from `./run cost estimate`.
## Rules
- Reference = style only. Never copy a reference's footage, music or text; generate our own.
- AI footage in client work: keep provenance marks, offer the AI-content label (India IT Rules 2026, EU Art. 50).
- Every engine call is measured (stage + cost row) and logged in the job's eval.json.
- Max 2 Claude calls per stage; 2 failed retries = FAILED.
## Status 2026-11-07
- Evaluator built and tested. Kaggle probe: LTX 22B did not load on 2x T4 (14.6 GB). Modal runner scripts/modal_app.py built; needs Faiz's MODAL_TOKEN_ID + MODAL_TOKEN_SECRET secrets, then probe specs go in trigger/videogen/.
