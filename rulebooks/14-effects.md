# 14 - Editing effects (worker prepares them, Remotion draws them)

Code: `scripts/fx.py` (orchestrator, speed, stabilise, grain, punch keys), `track.py`, `matte.py`, `voice.py`, `safezone.py`.
All run inside `render_plan` BEFORE Remotion, on copies in `public/fx/`. The stored plan never changes. An effect that fails keeps the
clip as shot and is listed in the render report (`effects.errors`). Reports go to `<final>_clone_report.json`.

## Scene props (video scenes)
- `speed` 0.1..8 | `speed_ramp` [{at_s (source seconds), speed}] | `smooth: true` (frame blending, slow motion only).
  The trim window is consumed by the retime. Set the scene `duration_s` to the retimed length (report: `out_duration_s`).
- `stabilize` "normal"|"light" (vidstab two-pass, else deshake). `clean_voice` true = speech chain on the clip's audio.
- `voice: true` = the clip has speech, music ducks under it. `remove_bg` true = cut-out (image -> PNG, clip -> WebM alpha, max 360 frames).
- `reframe: "auto"` = 9:16 window follows the face (camera-operator glide, dead zone, no snapping); set `plan.output` with
  `track.output_size(w, h)` (4K 16:9 -> 1214x2160, real pixels). No face detector = centre crop.
- `track_from: {box: [x,y,w,h] fractions | "face"}` fills `follow`. Use it with an overlay stroke. Do not combine with `reframe`.

## Scene fields
- `zoom` [{at_s, scale 1..1.6, x, y, ease}] punch-in / slow push (footage + overlays together). `fx.punch_keys(times)` for beat hits.
- `overlays` [{template, props, start_s, end_s, box | follow}]: graphics over a scene. `stroke` follows its box; others shift.

## Audio entries
`role`: voice (cleaned: 80 Hz high-pass, afftdn, -2 dB@250, +2 dB@3k, de-ess, compressor), music (gets `duck` windows, -9 dB, 0.15 s ramps),
sfx (untouched). Loudness stays `finish.normalize_loudness` (once, final mix).

## Finish
`vignette` 0..1 (radial gradient). `grain: true` = noise tile overlay, shifted per frame (no SVG filters).

## Safe zones (9:16): strict 14% top / 35% bottom / 6% sides (Meta guidance), hard 7.8/14.6/10/8.3.
Captions and lower thirds already keep inside strict. `render` result has `safe_zone` findings (hard = fix before gate 5).
Numbers: `limits.json -> safezone` = `remotion/src/lib/safe.ts` (test keeps them equal).

## Honest limits
Tracking = one subject, one box; face needs a detector (Haar if shipped, else YuNet downloaded once). rembg is CPU: images fast, clips slow.
