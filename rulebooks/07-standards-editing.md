# 07 editing DNA standard (read before building or using editing DNA)

Goal: another editor (or Remotion) can rebuild the style from the DNA alone. Schema: `schemas/dna-editing.schema.json` (v2).
Vocabulary = film/broadcast grammar. Every section carries a confidence tag; judged items cite evidence (scene ids / t).

## Measured by scripts (copy the numbers, never retype from memory; `./run dna-check` compares them)
- format (width, height, fps, duration; phone rotation applied), ASL = mean shot length, median, std, min, max.
- cuts/min, pace curve (opening / middle / closing thirds), transition mix, beat-cut sync, motion class per scene.
- palette with shares, brightness, saturation. OCR text per scene.

## Judged by Claude from collages (tag `judged`, cite scenes)
- Shot scale mix: ECU, CU, MCU, MS, WS, EWS (shares sum ~1). Angle, composition (thirds, centered, symmetry), headroom.
- Cut grammar (Murch's six: emotion, story, rhythm, eye-trace, 2D plane, 3D space): hard, jump, match, J/L, cutaway,
  smash, whip, dissolve, fade, wipe. Say what the cut does, not only its name.
- Motion: pan/tilt/push/pull/handheld/parallax; easing class (linear, ease-in/out, spring, overshoot); typical
  duration in frames; stagger; speed ramps.
- Text: role (caption/title/label/kinetic), font class, weight, case, size vs frame height, position vs platform
  safe zone (reels: strict top 14% / bottom 35% / sides 6%, hard top 7.8% / bottom 14.6%; see 14-effects), in/out animation, on-screen seconds, words per caption.
- Colour: grade look, contrast, temperature, saturation; 709 vs log look. Layout, framing, screen-recording share.

## Recipe (how to rebuild in Remotion)
- `recipe.remotion_templates` (title, kinetic_text, banner, image, lower_third, video), typical scene seconds, spring config.
- Fonts, easing and exact grade are never recoverable: give best candidates, tag `estimated`.

## Precision rules
- One video = one candidate. Never merge videos by eye: use `./run corpus` (rulebook 03) for many videos.
- A claim without scene evidence is tagged `estimated`. Minimum 3 evidence entries per candidate.
- Resolution of the output follows the raw source (01-video). The DNA stores the reference's format only as style.
- Done = `./run dna-check --type editing --file F --summary S` prints PASS, then gate 3 in chat.
- After a render: analyse our own output with the same scripts and run `./run clone-report` (tolerance 10%).
