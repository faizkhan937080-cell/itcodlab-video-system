# 03 DNA rules

## What DNA is
A compact description of a reference's style, built from script metrics + collages. Not the video itself.
Types: editing, scripting, sound. Mode from the command: video / audio / both.

## Input to Claude (nothing else)
- Collages (max 10), metrics summary, transcript summary, cluster map summary.

## Collages (limits in `config/limits.json`)
- Long edge at most 1568 px. Biggest tiles that fit all scenes (`detail_layouts`): 16:9 -> 2x3 of 784x441,
  9:16 -> 2x1 of 784x1394 or 3x1 of 522x929, else dense 4x2 (392x697) / 3x3 (522x294). Never stretched.
- Each tile shows timestamp + frame number. Max 10 collages per video, never more.
- Similar scenes are deduped (pHash + SSIM). Only one representative goes in a collage.
  Removed scenes stay in metrics as "pattern X, n times, total duration".

## DNA candidate contents
- Editing: cut rhythm, transitions, camera/element motion, text style + position, color grade, layout.
- Sound: BPM, beat-cut sync, voice/music balance, silence.
- Scripting: hook, structure, pacing, tone, language.
- Mark each item as measured or estimated. Fonts and easing are always estimated.

## Saving
- Candidate -> user approval (gate 3) -> `dna-vN.json` in Drive `dna/<general|creators/<name>>/` -> row in DNA_Index.
- Never overwrite an older version. Never delete.
- Mistake in DNA? Draft a lesson in `lessons/dna.md`, ask approval, then save.

## Creator folders (one name everywhere)
- Creator name = Instagram handle, lowercase, read from the link by the worker (target `creator:auto`).
- Same name in: `dna/creators/<h>/{editing,scripting,sound}/dna-vN.json`, `dna/creators/<h>/sources/<job>.json`,
  `analysis/creators/<h>/<job>.json` (pointer to the full analysis), Sheet DNA_Index.
- "Make it in <name>'s style": list `dna/creators/`, match the handle (fuzzy), read the latest dna-vN
  of each needed type (script -> scripting, video -> editing, both -> all three + sound), then plan.
- Merge or compare creators only with approval. Old versions stay.
