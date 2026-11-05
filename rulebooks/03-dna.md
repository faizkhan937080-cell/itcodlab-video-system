# 03 DNA rules

## What DNA is
A compact description of a reference's style, built from script metrics + collages. Not the video itself.
Types: editing, scripting, sound. Mode from the command: video / audio / both.

## Input to Claude (nothing else)
- Collages (max 10), metrics summary, transcript summary, cluster map summary.

## Collages (limits in `config/limits.json`)
- Long edge at most 1568 px. 9:16 -> 4x2 tiles (392x697). 16:9 -> 3x3 tiles (522x294).
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
