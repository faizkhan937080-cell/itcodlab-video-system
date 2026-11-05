# 01 video rules (motion graphics + Remotion)

## What Claude does
- Read the approved editing DNA + scene plan, then write Remotion components/templates and scene.json.
- Fix render errors from the last 20 lines of the log. Nothing else.

## What scripts do (Claude never does these)
- Cuts, scenedetect, optical flow, OCR, colors, audio beats, transcript.
- Collage building, dedup, preview render, 4K render, ffprobe checks, upload.

## Render targets (values in `config/limits.json`)
- Preview first (scale 0.5). 4K final only after preview approval.
- 4K master: 3840x2160, h264, bt709, crf from limits.json. No downscaling of the master.
- Delivery files for other platforms are made by scripts from the master.

## Quality rules
- Use the premium component library: kinetic text, 3D banners, spring/easing presets, grain, shadows.
- Reference match is an estimate. Exact fonts, easing and code are not recoverable: give best candidates.
- Brand colors and hashtag style: `config/brand.json` (hashtags lowercase).
- Complex 3D / particle motion will be approximate. Say so in the scene plan.

## Revisions
- Rejected video: feedback goes in the Sheet, status REVISE, re-render only the changed scene.
- Mistake fixed? Draft a lesson in `lessons/video.md`, ask approval, then save.
