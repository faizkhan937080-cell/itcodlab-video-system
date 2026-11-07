# 19 costs: every job leaves time + money data (Faiz 2026-11-07)
Why: Faiz needs speed, output and price per video for free tiers, credit plans and paid plans, down to micro level, so he can scale and price work.

## Rules
- Every analysis and render writes one row to Drive `costs/jobs/` (scripts/costs.py). Rows never block a job. Never delete rows.
- Rates live in `config/pricing.json`, each block with source URL + checked date. Third-party sources are marked (verify). Re-check before a big spend decision (Claude looks them up live, never from memory).
- Before work on a reel Faiz asks "how long / how much": run `./run cost estimate --seconds <len>`. No rows = say "no data yet", never invent.
- Add Claude's own tokens per job with `./run cost claude` (estimate, marked). Plan now: Claude Pro = flat, so the Claude $ is API-equivalent only.
- Report to Faiz in short Hinglish: seconds, minutes of free quota left, rupees (use usd_inr in pricing.json).

## Free quotas to watch (alert once, Faiz decides)
- GitHub Actions: $12/month included = 2000 min. Alert at 80%.
- Kaggle GPU: ~30 h/week (user-reported). Alert at 80%.
- Gemini free tier: limits lower than paid; alert on any 429.
- GCP credit: Rs 28,569 left; GPU VM only on "speed up".

## Files
- `costs/README.md` (what is in the folder), `costs/research/` (price papers), `config/pricing.json` (rates the code reads).
