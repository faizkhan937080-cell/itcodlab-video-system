# 8bit_sciences new video (bruise): music + new Remotion parts
## Music spec (name NOT invented)
- Need: chiptune / lo-fi game loop, 117.5 BPM (accept 114-121), 4/4, seamless 25 s loop, no vocals, bed ~-18 LUFS, master -17 LUFS, peak <= -3 dB.
- Reference title unknown: run on worker `./run resolve reel-DgJre5hyNYW` (AcoustID + listen.json). Library is on Drive; this session has no Drive storage -> `./run library find chiptune` / `find 8bit` could not run here.
- If AcoustID finds nothing: pick closest licensed track from `assets/library/music` by tag (chiptune, 8bit, lofi, 110-125 bpm), else `./run library fetch` (CC0/CC BY only), add to library by name. Never invent a track name.
- SFX (via `./run sfx`, Openverse CC0/CC BY): tape rewind, 8-bit blip (DAY jump), thud, glass-crack/snap, soft pop. Voice: ONE voice, new vs earlier videos, hook 'Hmm?' + two short lines (voice spec in step 3 after Drive access).
## New Remotion parts needed (none exist: current components are BodyScene/BodyShots photoreal, Three3D, Counter)
1. PixelSkinSection.tsx - layered side cross-section drawn on canvas at 1/5 res (216x384 art px) scaled with image-rendering:pixelated. Props: layers[], frame -> draws epidermis bricks, dermis cells, papillary wave, capillaries, vessel band, muscle lines (palette from style card). Deformation: bulge/dent function per x.
2. PixelActors.tsx - animated sprites: blood droplets+pool fill (colour keyed by day), macrophage (white blob + dark nucleus, drift/gulp), cricket ball, boy+bat. Hand-drawn pixel arrays (our own art; reference is only STYLE; clone-mode "outside add-on" rule applies only if Faiz orders 99% clone: he ordered same STYLE, new topic).
3. ScanlineGlitch.tsx - CRT overlay (scanlines, horizontal glitch bands, RGB split, 0.3 s) triggered on beat frames; can use @remotion/effects noise.
4. DayCounter.tsx - pixel font (Google font 'Press Start 2P' or 'Silkscreen', check config/google_fonts.json), fast-forward / rewind icon, count steps with blink.
5. Callout.tsx - thin line + pixel label, draws line then types text, anchored to sprite position.
6. PixelScene.tsx - outdoor end scene + zoom-out thigh (sky, clouds, trees, ground) as a second scene via TransitionSeries.
7. EightBitShots.tsx - shot list wiring 1-6 to beats-v1.json; plan via work/8bit-sciences/make_plan.py (template name + schema entry in schemas/scene.schema.json).
Catalog: `./run catalog pixel` returns only stickman skill (explainer_shots); no real_3d fits. Pixel art 2D = hand-built Remotion (own shot set), animated every frame, not stills+zoom. Tell Faiz: this is 2D pixel (like his reference), not 3D.
