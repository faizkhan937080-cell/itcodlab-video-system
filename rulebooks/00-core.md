# 00 core rules (read before every task)

## Roles
- Claude: writes Remotion code, scene.json, DNA candidates, scripts, fixes. Nothing else.
- VM scripts: download, frame analysis, audio, dedup, collage, render, checks, upload.
- Drive: heavy files. Sheet: queue + approvals. GitHub: rules + code.

## Who decides
- Coding, tools, fixes, lessons: Claude decides alone (Faiz is not technical).
- Faiz decides: every approval gate, folder layout, spending, deleting, publishing.
- Faiz never types code. Steps for him: short, exact button names, a few at a time.

## Token rules
- Input to Claude: collages (max 10 images) + metrics summary + one rulebook. Never raw media.
- Max 2 Claude calls per stage. Retry twice, then FAILED.
- Fresh session per job. Error logs: last 20 lines only.
- Default model: Sonnet. Bigger model only for hard creative work, with approval.
- Daily job cap and limits: `config/limits.json`.

## Nothing is deleted
- Source video stays in Drive `analysis/<job-id>/source.mp4`.
- Per-frame metrics and full-res keyframes stay.
- Dedup removes scenes from the collage only. Metrics and cluster map keep them.
- DNA is versioned: dna-v1.json, dna-v2.json. Never overwrite.
- Scripts use copy, never sync. rm/delete is denied.

## Never do
- Meta Ads upload or publishing. Numerology. Auto-publish.
- Copy a reference video's footage, music or text. Reference = style learning only.
- Store passwords, tokens or keys in the repo.

## Open items to verify before scale
- Remotion license terms for company use.
- Music, font and stock footage licenses for client work.

## Link downloads
- Instagram/YouTube may block cloud IPs. If download fails: status FAILED: download,
  user drops the file in Drive `input/references/`. Pipeline then continues as normal.
