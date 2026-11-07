# costs/ : time + money data for every video job

What is here
- `research/` : price papers (sources + dates). Update when a rate changes. Rates the code uses: `config/pricing.json`.
- `local/` : fallback rows if Drive was down (gitignored). Real rows live in Drive `costs/jobs/<job>__<kind>__<time>.json`.

One row = one job step (analysis, render_preview, render_final, claude). It holds
- seconds per stage (frames, transcribe, listen, voice, collages, describe, render...), machine (GitHub 2-core / GPU VM / Kaggle), CPUs
- media: length, resolution, fps; source/output size
- Gemini calls + tokens; Claude tokens (own estimate, logged with `./run cost claude`)
- usd_equivalent: the same measured seconds priced on every plan (GitHub free, GCP T4 on-demand/spot, Kaggle free, Colab Pro, Gemini, Claude API)

Commands (scripts only)
- `./run cost report` : totals, GitHub minutes this month vs the $12 included, Kaggle GPU hours, seconds per media-minute by stage
- `./run cost estimate --seconds 60 [--kind analysis|render_final] [--machine ...]` : predicted time + cost from measured rows
- `./run cost claude --job J --model sonnet-5.5 --tin N --tout N` : log Claude tokens for a job (estimate, marked so)
- `./run kaggle-compare <wav>` : CPU vs free Kaggle GPU seconds + identical-output check

Honesty rules
- Estimates use only measured rows; no rows = "no data yet". Other-plan prices reuse the same seconds until measured there (field `basis`).
- Claude Pro is flat monthly: the Claude USD column is API-equivalent, for comparing plans only.
- Faiz asks "how long / how much for this reel?" -> run `cost estimate`, then add the Claude-token estimate by hand.
