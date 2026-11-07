# Compute prices (checked 2026-11-07). Numbers also in config/pricing.json

## GitHub Actions (our free worker)
- Private repo included usage is MONEY: Free $12, Pro/Team $18 per month. Linux 2-core = $0.006/min -> $12 = 2000 min.
- Billed in whole minutes per job. Cache 10 GB/repo, artifacts 500 MB (Free).
- Source: docs.github.com billing page for Actions (read 2026-11-07).

## Kaggle (free GPU, being added)
- GPU T4 x2 or P100, session max 12 h. Weekly GPU quota NOT published by Kaggle; ~30 h/week is user-reported and matches Faiz's notebook.
- Internet in notebooks needs a phone-verified account (done). Price $0. Source: gpuperhour.com 2026-09-21 (third party, verify).
- Our cost: dataset upload + kernel start adds ~1-3 min per run -> short reels may be SLOWER than CPU. Decide from ./run kaggle-compare.

## Google Cloud (credit left Rs 28,569)
- T4 VM n1 8 vCPU 30 GB, asia-south1: on-demand $0.866/h, Spot $0.332/h (devzero.io, verify).
- L4 g2-standard-4, asia-south1: on-demand $0.7357/h, Spot $0.6606/h (holori.com, verify).
- T4 quota in asia-south1 = 0 and cannot be raised on a new account ("Not enough usage history"). GPU VM itcod-gpu not created yet.
- Extras not in these prices: disk, network, idle time. itcod-gpu auto-stops after 10 idle min.

## Colab
- Free: limited T4, no published quota, 12 h max. Pro $9.99/mo = 100 units; Pro+ $49.99/mo = 600 units.
- T4 burns ~1.19 units/h -> ~$0.12/h on Pro (article estimate). Source: gpuperhour.com (verify).

## Other cheap GPU (reference only)
- L4 ~$0.59/GPU-h cheapest listed (RunPod), RTX 4090 $0.89, A100 $0.67 (Vast.ai), H100 $2.59. Live market, changes daily.

## USD -> INR
- 95.24 (Wise page, 2026-11-07, no timestamp). Keep in pricing.json; update when quoting rupees.
