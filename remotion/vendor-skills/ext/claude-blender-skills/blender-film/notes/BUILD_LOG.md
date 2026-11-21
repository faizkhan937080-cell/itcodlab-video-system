# Spidey build log (2026-10-24) — for the 15-min video

Scene: `scene/spidey.blend` (Blender 5.2). Live control: `tools/start_blender.ps1` (Blender + bridge on 127.0.0.1:9876), `tools/send.py`.
Every step is a script in `scripts/` run in that order. Screenshots of each step: `shots/`. OBS takes: `recordings/`.

| # | Step (his chapter) | What Claude did | Script | Shots / clips |
|---|---|---|---|---|
| 1 | Open the rig (P1 0:33-1:23) | Opened Spider-Man.blend trusted, IK_FK = 1 on arms + legs, hid IK/tweak bone layers | s01_open_rig.py | s01_open, s01_fk · rec 01 |
| 2 | Import + arrange buildings (P2 0:00-2:00) | New 24 fps / 480-frame scene, appended the 5 buildings + Spidey+Rig, deleted the junk | s02_new_scene.py | rec 01b |
| 3 | City layout from the storyboard map | 173 instances: avenue (faces at y=±10), cross street at the 0:12 mark, back rows, far blocks | s03_city.py, s03b_fill_gaps.py | s03_city_top |
| 4 | Plan the swing (P2 2:44 "physics!") | Physics sim of the whole swing: real pendulum webs, gravity, drag, slingshot, landing time | swing_sim.py, tune.py, shift_sim.py | sim_plot |
| 5 | Path + empty + offset (P2 2:44-8:49) | "Spider-Man Path" curve from the sim, "Spider-Man Empty" on Follow Path, offset keyed from the sim (real speed), rig parented at the centre of gravity | s04_path_empty.py | s04_grid · rec 02 |
| 6 | Momentum rotation (P2 8:49-14:16) | Empty rotation: hangs along the web, keeps turning in free flight, front flip after A, tucked back flip at the top, dive, feet-down for the landing | s04_path_empty.py | |
| 7 | Camera (P3 16:31) | Camera Path + Follow Path, angles from the 10 storyboard panels, 24-30 mm, offsets smoothed, steers clear of webs | s05_camera.py | preview_wb_v1/v2 |
| 8 | Body animation (P2 14:16-P3 7:30) | 12 Mixamo clips downloaded (+2 mirrored), OWN retarget to his Rigify FK controls, NLA strips on the beats, hip-lean variants for crouch + landing, feet contact pass | s06_retarget.py, s06b_hips_variants.py, s07_nla.py, s08_grounding.py | poses.jpg · rec 03 |
| 9 | Webs (P3 8:00-16:31) | His method per web A-E: vertex line, 2 hooks, cloth pinned, Child Of hand bone, shrink/influence keys, thwip, visibility; tube via geometry nodes | s09_webs.py | webs, webs2 |
| 10 | Noise (P3 20:23-24:57) | Camera: slow sway + micro shake (2 noise layers per axis). Spidey empty: subtle wobble | s05b_noise.py | |
| 11 | HDRI + look (P3 24:57, 35:45) | Poly Haven sky (CC0) rotated so the sun rakes down the avenue, AgX, painted asphalt (double yellow, dashed lanes, zebra crossings), concrete sidewalks, tint variation per building | s10_look.py | stills_a |
| 12 | Populate the city (P3 25:22-35:45) | BlendKit cars (taxi, Audi Q3 x2, GR GT, Lada, van), parked rows, 13 moving cars (linear, like his truck), stopped cars at the landing, trees/hydrants/trash/lamps/traffic lights; props kept clear of Spidey + camera | s11_props_lib.py, s12_dressing.py | stills_b, cars_top2 |
| 13 | Landing impact (storyboard panel 9) | Asphalt chunks (particles bouncing on the road) + crack decal under the fist | s13_landing_fx.py | stills_c |
| 14 | Camera settings (P3 35:59) | DOF focused on the empty, f/2.8, motion blur 0.5 | s10_look.py / s05b | |
| 15 | Render | Cycles OptiX 2560x1440, 64 spp + OIDN, ~13 s/frame, resume-safe | tools/render_final.cmd | render/final, Spidey_swing_1440p.mp4 |

## Changes from the ChatGPT storyboard (physics)
- He crouches on the roof edge for 0.4 s first, then leaps (storyboard panel 1 starts mid-jump).
- Web A fires at 1.6 s (storyboard 2.5 s): 2.5 s of free fall from a 24 m roof is 30 m -> he would hit the street.
- Every web is fired while he drifts AWAY from that wall: a pendulum's lowest point is right under its anchor, so a web to a
  wall pulls you into that wall. This is why the path weaves left-right (same as the storyboard map).
- Slingshot D+E at 12.6-14.0 s, he tops out at ~35 m (roof height), back flip, dive, touch-down at 18.7 s, fist hits at 19.0 s.
- Anchor heights are real roof heights of his buildings (28-36 m).

## Bugs met (good video beats)
- Mixamo: the page cannot hand files over (CSP), Chrome blocks repeated automatic downloads -> one click per file in a fresh tab.
- Rig came in 4x too big when I reset its transform (his rig has object scale 0.2653).
- First sim: swings went straight into the wall (pendulum physics) -> "flight line" + fire-away rule.
- First camera: Spidey tiny (spring lag = 2v/omega metres behind at 20 m/s) -> smooth the offset, not the position.
- Landing frame: aim spring lagged 4 m behind a 22 m/s fall -> centred average aim.
- Street lamps glowed in daylight (white streaks in motion blur) -> emission off.
- His roof textures are atlases (zig-zag when re-projected) -> tileable Poly Haven concrete + roof asphalt.
- Recording helper moved other projects' OBS files -> fixed and restored.

## Credits (description)
Assets: Peter France "Creating a Spider-Man Scene in Blender" asset pack (rig, suit, buildings) · Mixamo (Adobe) animations ·
Poly Haven (CC0): kloofendal_48d_partly_cloudy_puresky, asphalt_02, concrete_pavement, worn_asphalt, fire_hydrant, metal_trash_can, tree_small_02 ·
BlendKit (royalty free): Taxi, 2019 Audi RS Q3 Sportback, 2020 Audi Q3 Sportback, Toyota GR GT, VAZ 2107 lada, Van Patriot USA, Modern Street Lamp (tall) #02, Traffic Light.
Spider-Man is a Marvel character (fan art, non-commercial).
