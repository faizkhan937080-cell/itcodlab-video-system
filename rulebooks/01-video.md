# 01 video rules (motion graphics + Remotion)

## What Claude does
- Read the approved editing DNA + scene plan, then write Remotion components/templates and scene.json.
- Fix render errors from the last 20 lines of the log. Nothing else.

## What scripts do (Claude never does these)
- Cuts, scenedetect, optical flow, OCR, colors, audio beats, transcript.
- Collage building, dedup, preview render, 4K render, ffprobe checks, upload.

## Render targets (values in `config/limits.json`)
- OUTPUT QUALITY = SOURCE QUALITY (Faiz rule 2026-11-06): raw clips 4K -> final 4K; 1080p raw -> 1080p (never fake-upscale);
  portrait phone 4K (rotation tag) -> 2160x3840. Biggest raw clip decides. `plan.output` overrides. No raw clip -> 4K master.
- Raw footage goes in the plan as scene template `video` (props.src = Drive `input/...` or `assets/...` path,
  optional trim_start_s, trim_end_s, fit, muted). Never re-encode raw before Remotion; Remotion reads exact frames.
- Preview first (scale 0.5 of the output size, low quality is fine). Final only after preview approval (gate 5).
- Final master: h264, bt709, crf from limits.json (16). No downscaling of the master.
- Delivery files for other platforms are made by scripts from the master.

## Quality rules
- Use the premium component library: kinetic text, 3D banners, spring/easing presets, grain, shadows.
- Reference match is an estimate. Exact fonts, easing and code are not recoverable: give best candidates.
- Brand colors and hashtag style: `config/brand.json` (hashtags lowercase).
- Complex 3D / particle motion will be approximate. Say so in the scene plan.

## Revisions
- Rejected video: feedback goes in the Sheet, status REVISE, re-render only the changed scene.
- Mistake fixed? Draft a lesson in `lessons/video.md`, ask approval, then save.

## Finishing (automatic at render stages)
- Final render is loudness-normalised to target LUFS (plan.audio_target_lufs or sound DNA), -1 dBTP limiter (`scripts/finish.py`).
- Clone check: our output is measured by the same scripts and compared to the DNA/corpus (10% / 0.5); differences go in the job note. Never skip.
- Tune hints (`scripts/tune.py`): after the clone check each failing DNA type carries `hints` = which plan number to change (output size, fps, scene durations x factor, beat grid, audio_target_lufs). Apply them in the next plan version; max 2 rounds. No automatic re-render yet (needs a first real render to validate).

## Scene templates (remotion/src/components, schema enum in schemas/scene.schema.json)
- title, kinetic_text, banner, image, lower_third, video + counter (value/prefix/suffix/decimals/label), bar_chart (title, items[{label,value}], suffix),
  checklist (title, items[]), split_compare (left/right {title, points[]}), quote (text, author),
  stroke (text, shape underline|circle|arrow|scribble, color: hand-drawn stroke that draws itself),
  paper_cutout (src, caption, rotate_deg, size 0.4-1, seed: torn-paper photo with white border, stop-motion wobble),
  lottie (src = assets/library/motion/*.json, size 0.1-1, x, y, loop, speed), audio_bars (src audio, bars 8-64, color, y, height: music-reactive bars).
  Title / kinetic_text size themselves to fit (lib/fit.ts, real text measurement): long text shrinks, never overflows.
- New template = component + types.ts union + Main.tsx case + schema enum (tests/test_scene_templates.py checks all four match).
- No blur / boxShadow / SVG filters in templates: cloud renders have no GPU. Exception: `med` (depth blur is its look; 65 s preview 540x960 = 4.8 min on 2 vCPU).
- `med` template (MedScene.tsx): drawn medical explainer shots (kidney, tract, scope, laser, stent, stones, factors, staged, end card) in the warm 3D-anatomy look of ref reel-DZR1CyRvYh1.
- Voiceover: `./run tts <script.json>` (Kokoro, free); segment times drive cuts + text (cut = middle of the pause). `lexicon` {word: IPA} fixes names. QA: `./run qa-sheet`.
- Captions: `plan.captions` = [{text,start_s,end_s,words?[{text,start_s,end_s}]}], `plan.caption_style` = {position bottom|center|top, max_words 1-8 (default 4),
  highlight brand-colour key, size}. Spoken word is highlighted (Remotion TikTok-caption pattern). No word times -> words spread evenly in the segment.
- Reels: captions on by default for speech videos; keep max_words 3-4; position bottom (above the 220 px UI safe zone).
- Paper-cutout / stop-motion look: `plan.step_fps` 4-24 (8-12 typical) freezes scene content on every Nth frame; raw `video` scenes stay smooth.
- Texture: `plan.texture` {src (assets/ image), opacity 0-1 (0.35), blend multiply|overlay|soft-light} over all scenes. Check the texture licence before commercial use.
- Transitions (`transition_in`): cut|fade|slide|slide_up|zoom|wipe|flip|iris|clock_wipe|whip + duration_s (<=2). `overlap: true` keeps the previous scene underneath (real cross-transition, total length and audio sync unchanged). Preferred over TransitionSeries (that shortens the timeline).
