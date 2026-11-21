# Plan: recreate first 16 s of "Blender Hyper-Realistic Forest" (roe.num77) on RTX 5070

Reference: research/frames/f0000-f0900.jpg (30 fps, 1080p), research/a0.jpg a1.jpg b.jpg, research/frames/transcript.txt
Project file from him: NONE. Only assets (376-384). Final forest .blend and the cabin are not given. Cabin is "tell me in the comments" in the video.

## Shots (cuts at 3.53 / 7.23 / 11.27 / 14.77 / 17.63 s) = 480 frames for 0-16 s @30
1. 0.0-3.5   low cam over floor, tilted down: fallen log, ferns, orange leaf litter. Slide + tilt up.
2. 3.5-7.2   eye level ~0.5 m, ferns in front, rocks, gravel path far, dark trunk left. Slow glide sideways.
3. 7.2-11.3  low beside path, gravel curves right, birches, dappled sun. Slow forward glide.
4. 11.3-14.8 two black A-frame cabins, wood deck, gravel path, blue sky + clouds. Slow push-in.
5. 14.8-17.6 close on cabin glass (warm lights), firewood rack, deck edge. (we stop at 16.0)

## Stages (one script each in scripts/, resumable, save .blend after each)
A. Unpack + audit. DONE except textures (379).
B. build_world.py  Terrain (his Remeshed Terrain) + leaf-soil material (map 50, disp 0.2, hue/sat 1.2, rough 1). HDRI strength 2.25, ground hidden (z 0.25), Filmic/High Contrast (fall back to AgX look if 5.2 lacks Filmic), exposure 1.5, gamma 0.9. Light-path trick (camera ray -> sky strength 1, lighting 2.25). Sun power 10, warm, rot 24/-53/148.
C. scatter.py  OUR OWN scatter (Geometry Nodes built by script, no Geo-Scatter). Layers with his numbers: birch x11 (dens .06, vert 0.85, scale 1.6), young trees x2 (.05), large shrubs (.5), small shrubs (hand-placed ring around cabin), ferns (5, scale 1.3-1.87), branches (1.85), debris (3), leaves (200, 70% cull), ground plants (50% cull), rocks, fallen logs. Masks: vertex group "center" (cabin+path cleared), bezier-area, color attribute for leaves. Seeded so renders are repeatable.
D. build_path.py  Bezier -> mesh -> boolean with duplicate terrain -> gravel material (2 gravel textures mixed by 'middle' vertex mask, bump 0.1, disp 0.05).
E. build_cabins.py  OUR OWN cabins from frame references: two black charred-wood A-frames, slate roof, big glass front with warm interior (stove, furniture, lamps from plant library), wood deck (planks, bevel .003, array), rusty firewood rack, chimney pipe.
F. camera.py  5 cameras/shots keyframed to match timings and moves, subtle handheld noise, shallow DOF, motion blur on.
G. Look-dev stills (low res), compare side by side with reference frames, tune until it matches. Loop here.
H. Render + export.

## Render budget (RTX 5070 12 GB, Cycles OptiX, denoise)
- Look-dev stills: 960x540, 32 samples, ~10-30 s each.
- Test frame: 1080p, ~128 samples, estimate 30-90 s/frame (dense foliage). 480 frames = ~4-12 h. Will measure on 1 frame per shot first and report real number before any full render.
- Per-shot frame ranges, PNG sequence (power-cut safe, resume), then ffmpeg mp4. 1080p for scenes, 2K only for final stitched video.
- Will ask before starting any long render.

## Safety / rules
- Blender always headless with --disable-autoexec on his files. Nothing of his run except as data.
- Defender clean, no scripts inside (see SECURITY.md). Rig-a-Car and Porsches untouched until needed.
- Own code only: scatter, cabins, camera, rig (later) are written by us.

## Open items
- textures.rar (379) not downloaded yet.
- Decide 1080p vs lower for the full 16 s after the timing test.
