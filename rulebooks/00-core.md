# 00 core rules (read before every task)

## FIRST RULE (Faiz, 2026-11-07, "10 baar nahi bolunga"): do it, never ask him to do it
- If Claude can do a step (code, config, push, run, test, check, file, Drive via script, GitHub workflow), Claude does it. Never hand it to Faiz as a to-do.
- Faiz does ONLY what needs his own login or hands: creating a key on a website, pasting a secret into GitHub, Y/N approvals in chat, buying a plan, deleting on his PC.
- Before any message that says "aap karo", check: can I do it myself? If yes, do it and report the result.

## Roles
- Claude: writes Remotion code, scene.json, DNA candidates, scripts, fixes. Nothing else.
- VM scripts: download, frame analysis, audio, dedup, collage, render, checks, upload.
- Drive: heavy files. Sheet: queue + approvals. GitHub: rules + code.

## Who decides
- Coding, tools, fixes, lessons: Claude decides alone (Faiz is not technical).
- Faiz decides: every approval gate, folder layout, spending, deleting, publishing.
- Faiz never types code. Steps for him: short, exact button names, a few at a time.

## Fence
- Three lanes (Claude / worker / Faiz), barriers and alerts: `06-fence.md`. Hook `scripts/guard.py` enforces them.

## Token rules
- Input to Claude: collages (max 10 images) + metrics summary + one rulebook. Never raw media.
- Max 2 Claude calls per stage. Retry twice, then FAILED.
- Fresh session per job. Error logs: last 20 lines only.
- Default model: Sonnet. Bigger model only for hard creative work, with approval.
- Daily job cap and limits: `config/limits.json`.

## Nothing is deleted (except approved dev scrap)
- Source video stays in Drive `creators/<handle>/reel-<code>/source.mp4` (old: `videos/<job>/`) (general: `analysis/general/<job>/`).
- Per-frame metrics and full-res keyframes stay. DNA is versioned: dna-v1.json, dna-v2.json. Never overwrite.
- Dedup removes scenes from the collage only. Scripts copy, never sync. rm/delete is denied for scripts and Claude's shell.
- DEV PHASE (set by Faiz 2026-11-06, config `phase`): 100% scrap may go: failed/superseded analysis packs, test
  renders, probe files, junk branches. Only via Drive trash (recoverable) through the connector, each item logged
  in memory/log. Never trash approved DNA, real client files, or the newest correct analysis. Job JSONs stay (cap ledger).
- When Faiz says development is over: `phase` becomes "production" and nothing is deleted again.

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

## Remotion license (approved 2026-11-06)
- Free for teams up to 3 people. CONFIRMED by Faiz 2026-11-06: IT COD LAB = 1 person, so Remotion is free.
  Re-check in chat if the team grows past 3 (then Creators license $25/month per coder).

## Save only real work (Faiz rule 2026-11-06 06:53 IST)
- Save to Drive/Sheet/DNA ONLY what comes from a reel/video Faiz gave. Test, trial, scratch and probe runs stay local (temp dir) and are never saved.
- Tests must not write to Drive, Sheet, the `review` branch or DNA. If a test needs a job, use a temp folder and delete it after.

## One command = the whole job (Faiz rule 2026-11-06 16:06 IST)
- When Faiz says "extract DNA / style / other factors from this reel", do ALL of it in one go: every DNA type, editing + content
  factors, hook, pacing, sound, extras, saved in the creator's folder. Never ask again per type or per step.
- Ask only for something EXTRA beyond his command. Tell him only what truly needs a human (110% sure Claude cannot do it).
- Structure, IDs, company folders, licences: `rulebooks/12-structure.md` (read it before touching creators/, clients/ or assets/).
