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

## DNA candidate contents (v2 = international-standard, precise; details in 07, 08, 09)
- Editing: 07-standards-editing.md. Scripting: 08-standards-scripting.md. Sound: 09-standards-sound.md.
- Every section: confidence tag measured / judged / estimated / unknown, plus evidence (scenes, times, quotes).
- Numbers come from the pack (`metrics_summary.json`, incl. `script_metrics`, `audio.ebu_r128`). Never retype by memory.
- ACCURACY GATE: `./run dna-check --type T --file F --summary S` must PASS before upload. The worker runs it again and
  refuses a candidate whose measured numbers differ from the pack (asks for the next version).
- Job modes: video = editing; audio = sound + scripting (voice and sound, no collages needed); both = all three.

## Many videos of one creator (clone a whole creator)
- One analyze job per video (mode both). Per video, one DNA of each type. Then
  `./run corpus --type T --creator <h> --files <dna1> <dna2> ... --out corpus.json` -> signature (clone), situational
  (follows the topic), targets (value to aim at). Under 10 videos = provisional. Saved with approval as
  `dna/creators/<h>/<type>/corpus-vN.json`. "Make it in <h>'s style": read corpus targets first, newest dna-vN second.

## Saving
- Candidate -> user approval (gate 3) -> `dna-vN.json` in Drive `dna/<general|creators/<name>>/` -> row in DNA_Index.
- Never overwrite an older version. Never delete.
- Mistake in DNA? Draft a lesson in `lessons/dna.md`, ask approval, then save.

## Creator folders (one name everywhere)
- Creator name = Instagram handle, lowercase, read from the link by the worker (target `creator:auto`).
- Everything of a creator sits under that name. Worker creates the folders as soon as the handle is known:
  `analysis/creators/<h>/<job>/` (source, pack, candidates), `dna/creators/<h>/{editing,scripting,sound,sources}/`,
  pointer `analysis/creators/<h>/<job>.json`, Sheet DNA_Index. General jobs: `analysis/general/<job>/`.
- Saved DNA: `dna/creators/<h>/<type>/dna-vN.json`. Only the 100% correct, approved version is kept in dev phase.
- "Make it in <name>'s style": list `dna/creators/`, match the handle (fuzzy), read the latest dna-vN
  of each needed type (script -> scripting, video -> editing, both -> all three + sound), then plan.
- Merge or compare creators only with approval. Old versions stay.
