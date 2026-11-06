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
  checklist (title, items[]), split_compare (left/right {title, points[]}), quote (text, author).
- New template = component + types.ts union + Main.tsx case + schema enum (tests/test_scene_templates.py checks all four match).
- No blur / boxShadow / SVG filters in templates: cloud renders have no GPU.
