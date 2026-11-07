# AI prices (checked 2026-11-07). USD per 1M tokens. Numbers also in config/pricing.json

## Gemini (describes collages)
- Our key is free tier: limits lower than paid, content may be used by Google to improve products.
- gemini-2.5-flash in 0.30 / out 2.50 | 2.5-flash-lite 0.10 / 0.40 | 3.6 and 3.8 flash 0.75 / 3.75 | 3.1 pro 2.00 / 12.00.
- Flash 3.6 / 3.8 DOUBLE on 2027-01-01 (1.50 / 7.50). `gemini-flash-latest` is priced as 3.8-flash in our ledger.
- Source: morphllm.com article (third party, it checked Google's page 2026-10-25). Verify on ai.google.dev before budgeting.
- Per-call tokens are recorded from the API's usageMetadata (image + text in, text + thinking out).

## Claude
- Haiku 5.5: in 0.10 / out 0.50 (prompt <=100K); in 0.50 / out 2.50 above 100K; cached read 0.01; batch half price (verified 2026-11-06, aipricing.guru).
- Sonnet 5.5: in 2 / out 10; cache read 0.20 (cache figure is Sonnet 5's, check). Context 1M.
- Opus 5.5: 4 / 20. Fable 5.1: 10 / 50. Source: platform.claude.com model page.
- Faiz is on Claude Pro = flat monthly, limits are usage not tokens. The ledger shows API-equivalent $ only to compare plans.
- Claude cannot read its own exact token count in a session: log an estimate with `./run cost claude` and it is marked estimated.

## What to ask next (open data we still need)
- Real seconds per stage on GitHub 2-core for 3 reels (ledger fills by itself).
- Kaggle compare numbers (cpu_s vs gpu_s, identical true/false).
- Remotion render seconds per output minute at 1080p and 4K (first real render).
