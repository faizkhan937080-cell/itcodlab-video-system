# 19 costs: measure everything, quote from data (Faiz 2026-11-07, "do not forget")
Why: Faiz prices, scales and plans (free tier / credit / paid plan) from this data. Claude must be able to say, before a job,
"this reel takes X min, Y of free quota, Rs Z" and be right. No data = say "no data yet", never guess.

## 1. Always measure (automatic, scripts/costs.py -> Drive costs/jobs/<job>__<kind>__<time>.json)
Row per step: analysis | render_preview | render_final | <step>_failed | claude. Fields (industry standard names):
- time: stages{} seconds (frames, transcribe, listen, voice, collages, describe, review_publish, render_*), total_s, wall_s
- rtf = total_s / media_s (real-time factor, lower = faster). Also seconds per media-minute by stage (report).
- queue_s (wait in inbox), worker_age_s (setup/cold start), attempt + failed rows (retries cost time and quota)
- resources: cpu_s, cpu_util_pct (low = a bigger machine will not help), peak_rss_mb (RAM), machine (name, cpus, kaggle_gpu)
- media: length, width x height, fps, codec; source_bytes / output_bytes (bitrate class); quality
- cache: ears_cache_hit (same file again = skipped models); gemini {calls, in_tok, out_tok, model}; claude {model, in_tok, out_tok, estimated}
- usd_equivalent: same seconds priced on GitHub free (gross), GCP T4 on-demand + spot, Kaggle free, Colab Pro, Gemini, Claude API. INR = x usd_inr.
Report adds: median + p95 time, usd per media-minute, failure count, cache hits, quota left (`./run cost report`).

## 2. Rules that keep it true
- New pipeline step: wrap it in `stage("<name>")`. New AI or paid service: add its rate to `config/pricing.json` (source URL + checked date) AND its tokens/seconds to the row. No step ships unmeasured.
- Rates are looked up live, never from memory; third-party pages are marked (verify); re-check before any spend decision.
- Never delete rows. Rows never block a job (scripts/costs.py never raises).
- Claude logs its own tokens per job: `./run cost claude --job J --model M --tin N --tout N` (estimate, marked). Claude Pro is flat: Claude $ = API-equivalent, only for comparing plans.
- Kaggle/GPU only counts as faster after `./run kaggle-compare` shows identical output AND a lower cpu_s vs gpu_s.

## 3. Before any job Faiz asks "how long / how much" (or gives a reel link)
1. `./run cost estimate --seconds <reel length> --kind analysis` (and `--kind render_final` for a build). Machine: github-ubuntu-2core by default.
2. Add: Gemini tokens (estimate output has it), Claude tokens (my own estimate), render minutes at the output size (raw size rule).
3. Say in 3 lines (Hinglish): time, free quota used, rupees if it ran on a paid plan. State "based on N measured rows"; if N < 3 say "rough".
4. After the job, compare estimate vs actual from the new row. Off by >30%: note it in lessons/core.md.

## 4. Free quotas to watch (alert once, Faiz decides)
- GitHub Actions $12/month included (= 2000 min). Alert at 80%. Kaggle GPU ~30 h/week (user-reported). Gemini free tier: any 429.
- GCP credit Rs 28,569; GPU VM only on "speed up". T4 quota in asia-south1 = 0.

## 5. Files
- `costs/README.md`, `costs/research/` (price papers, update when rates change), `config/pricing.json` (what code reads).
