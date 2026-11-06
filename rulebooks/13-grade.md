# 13 - Colour grade (worker does it, Claude only sets the mode)

Code: `scripts/grade.py` (maths), `scripts/grade_video.py` (files/ffmpeg). Numbers: `config/limits.json` -> `grade`.

## Modes (plan.grade.mode)
- `auto` = DEFAULT when plan.grade is absent. Fix the footage AND match the reference reel's look (`plan.grade.ref` = that reel's `grade.json`).
  No ref given -> behaves as `natural` (the report says so).
- `natural` = fix only (white balance, exposure, hazy blacks, over-saturation, skin hue). Ignores the reference.
- `off` = Faiz/brief says "no colour grading". Footage untouched. Only a necessary HDR -> SDR conversion happens (iPhone HLG/PQ).
Writing the plan: if the request says no grading -> `{"grade": {"mode": "off"}}`. Never ask Faiz about it again.

## What is graded
Only `video` and `image` scenes (raw footage / pictures). Text, graphics, paper cut-outs, brand colours are never graded.
The stored plan is not changed; graded copies go to `public/graded/` and the render plan points at them. Originals untouched.
SDR clips whose grade is "nothing visible" are not re-encoded (no generation loss).

## Standard (measured, bounded, never taste)
- Delivery = SDR Rec.709, 8-bit 4:2:0, tagged bt709. HDR is tone-mapped by us (Hable), because Instagram's own mapping looks washed out.
- Median luma ~0.45 (dead band 0.05: low-key looks stay), max +-1 stop. Black point ~0.02, white ~0.95, levels stretch max x1.5.
- White balance: Shades-of-Gray (p=6) + White-Patch, max +-15% per channel. Skin hue pulled toward ~20 deg (YCbCr locus), max 8 deg turn.
- Colourfulness (Hasler-Suesstrunk) acted on only outside 25..95. Reference match: strength 0.85, contrast x0.85..1.25, saturation x0.7..1.4.
- Tone maths in linear light. Median over 12 sampled frames. Brightness varying inside a clip -> warning in the report.
- Closed loop: grade -> measure again (`verify`) -> report in `<final>_clone_report.json` under `grade`.

## Reference look
`grade.json` is written for every analysed reel (`analysis.grade_look`). "Make it like THIS reel" uses only that reel's file.
Footage and reference are both measured AFTER conversion to SDR, so HDR vs SDR never gets compared raw.

## Limits and honesty
One global grade per clip. No secondary masks, no relighting. If a clip is too flat/mixed, the report says so; do not promise more.
