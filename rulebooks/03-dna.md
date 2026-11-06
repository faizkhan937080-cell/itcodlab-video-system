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
  `creators/<h>/style/<type>/corpus-vN.json`. "Make it in <h>'s style": read corpus targets first, newest dna-vN second.

## Saving
- Candidate -> user approval (gate 3) -> `dna-vN.json` in Drive `dna/<general|creators/<name>>/` -> row in DNA_Index.
- Never overwrite an older version. Never delete.
- Mistake in DNA? Draft a lesson in `lessons/dna.md`, ask approval, then save.

## Creator folders (one name everywhere)
- Creator name = Instagram handle, lowercase, read from the link by the worker (target `creator:auto`).
- Everything of a creator sits in ONE folder `creators/<h>/` (Faiz 2026-11-06). Worker creates it as soon as the handle is known:
  `reel-<code>/` (one flat folder per reel: source, pack/, candidates, reel.json; old `videos/<job>/`), `dna/` (approved DNA, file = `<job>__<type>__vN.json` so the reel is in the name),
  `style/<type>/` (corpus = whole-creator clone), `ideas/`, `scripts/`, `made/` (videos made in this style), `INDEX.md` (reel -> DNA, auto).
- General jobs: `analysis/general/<job>/`, DNA `dna/general/<type>/dna-vN.json`.
- Only the 100% correct, approved version is kept in dev phase. Never overwrite, never delete older versions.
- "Make it in <name>'s style": list `creators/`, match the handle (fuzzy), read INDEX.md, then corpus targets, then newest DNA files.

## Recipe card per reel (Faiz 2026-11-06 16:39)
- Each reel folder holds: `transcript.txt` (timed, readable), `elements.json` (Claude judges: fonts, music, sfx, motion, textures,
  tools_named, layout, captions, assets_needed - names + times), `recipe.json` + `RECIPE.md` (auto at SAVING_DNA: reel link -> DNA files -> elements).
- "Make it like THIS reel": read only that reel's RECIPE.md, its DNA files and elements. Never learn the whole creator for it.
- Music: demucs music stem is bad quality, NEVER reused. Save only measured numbers + mood/bpm + a search hint; take real music/SFX/fonts
  from `assets/library` (`./run library find <word>`).
- Dev phase: repeated same-name folders/files = scrap. Trash the superseded ones (Faiz approved this batch rule); keep job state JSONs (cap ledger).

