# Peter France — "Creating a Spider-Man Scene in Blender" (3 parts, 2020-03-17)

Source videos: ~/spidey-blender/src (p00001 = Part 1 6:28, p00002 = Part 2 23:45, p00003 = Part 3 38:39).
Transcripts: src/*.txt. Contact sheets: research/sheets (p1 every 5 s, p2 every 8 s, p3 every 9 s).
He uses Blender 2.81 (title bar "v2.81.16"), Cycles, 24 fps, shot = frames 1-136 (~5.7 s), later extended.

## Final shot (Part 1 intro 0:00-0:05, sped up)
1. Camera behind/below Spidey as he swings round a building corner (web to building, red-white suit, sunlit stone facades).
2. Spidey flies past camera (fast, heavy motion blur).
3. Camera tilts down over a street full of yellow taxis / cars (top-down street photo with extruded cars), Spidey dives low.
4. Bottom of swing in the intersection: very low over cars, a box truck ahead, crosswalk stripes, trees.
5. Swings up out of the street; camera looks up past building tops to blue sky with clouds.
6. Backflip / spread-eagle silhouette against sky, next web, swings off.
Look: warm afternoon sun, 24 mm, shallow DOF (f/1 focus on Spidey empty), strong motion blur, handheld noise on camera.

## Assets he gives (our zip = same)
- Spider-Man.blend: collection "Spidey+Rig" = SPIDER-MAN (Rigify armature, 365 bones, rig_id 755nmrdc40c0f1b5, rig_ui.py script)
  + "Spider-Man Body" (16.7k verts, Armature + Subsurf). Materials: Spidey Suit (10 node groups), Black Plastic (eyes), White Mesh.
  Packed maps: red-blue mask, Dots, Lines, Back/Front spider mattes, Foot, Wrinkles, halftone dot pattern, HDRI Willem_Kuyperstraat.
  Collection "Misc" = camera + ground (junk when appending).
- Buildings.blend: Building_1..5 (+ roof child each), real-world scale, 22-37 m tall, packed DIFF/NRM/ROUGH maps. Collection BUILDINGS.

## PART 1 (rig + suit tour) — chapters on screen
0:00 Intro · 0:33 Inverse kinematics · 1:23 Rig display settings · 2:00 Shader breakdown · 4:11 Displacement breakdown · 5:22 Importing Spider-Man
- Open Spider-Man.blend as TRUSTED (rig_ui.py auto-script builds the Rig Main Properties panel).
- root bone = whole rig; torso/pelvis bone = centre. Hand bone > N panel "IK_FK" slider: 1 = FK (hand follows arm). Same for feet.
- Hide IK (red) bone layers via Object Data > layers (no labels, click around). Keep only spine/arms/legs.
- Suit shader (Shading tab, split: render view top, node editor bottom):
  red fabric group (grid texture -> base colour + normal) / blue fabric / hand-painted red-blue mask mixes them /
  dots node driven by hand-painted Dots map (shiny dots) / shoe group (line pattern) / Lines map (web lines, hand-painted) /
  back spider + front spider mattes + materials, mix shaders.
- Bumps (displacement): dot bump (Dots map -> height), wrinkle bump (Wrinkles map), combined, shoe bump, line bump.
- Import into scene: File > Append > Spider-Man.blend > Collection > "Spidey+Rig". Select Spider-Man + rig, Ctrl+I, X (delete junk).
  Pose mode: set hand/feet IK_FK to FK again.

## PART 2 (layout + body animation) — chapters
0:00 Importing/arranging buildings · 2:00 Importing Spider-Man · 2:44 Animation path · 8:49 General body animation ·
14:16 Specific body part animation · 15:38 Hip · 16:56 Upper torso · 17:39 Head · 20:00 Legs · 22:09 Arms
1. Append all 5 buildings (collection). Duplicate + tweak to fake many. Edit mode, Ctrl+L section, Shift+D up = taller building.
   Layout (top view 7:44): two rows of ~4 blocks = a street running left->right, plus a column of 3 on the right = corner/intersection.
   Story in his head: swing out from behind a building, go LOW over cars in the intersection, swing up, flip, swing off.
   Rule: "If it's not physically possible in reality, it's going to look like it's not real."
2. Collections: Environment (BUILDINGS), ANIMATION (Spider-Man Empty, Spider-Man Path), Spidey+Rig. Toggle often.
3. Bezier curve traced through the street (top view), E to extend, Viewport Display > In Front. "Doesn't have to be perfect, start animating ASAP."
4. Intermediate EMPTY: pose mode select centre-of-gravity bone, Shift+S cursor to selected, add Empty, parent rig to empty (Keep Transform).
   Empty gets Follow Path constraint (target Spider-Man Path, Forward Y, Up Z), Alt+G to snap onto path.
   Animate Offset 0 -> -100 over frames 1 -> 136 (timed by hitting play and guessing). Graph editor: T > Linear (constant speed). Lock offset.
5. Empty ROTATION = whole-body momentum. Keys while thinking like Spidey: lean toward the building he's swinging from,
   Shift+E Linear Extrapolation (keeps spinning = momentum), S X to flatten curves until a new web changes momentum,
   rotation drift turned into a backflip after the intersection, then new web and swing out. "Looks janky until 90%."
6. Body (pose mode, FK, split view: left solid + rig, right Material Preview with overlays off). Order = centre of gravity outward:
   hips (R X X local) -> upper torso (turn toward what he holds, arch back in freefall, crunch in swing) ->
   head (location+rotation; look where he's going / where he'll shoot the web; head snaps down at bottom of swing then back) ->
   legs (Spidey kick-out, tuck to spin faster like a rolly chair, legs trail parent bone = overlap) ->
   arms (shoulder bone too, cannonball pose, arm out to shoot web, hold mid-swing shape until he lets go).

## PART 3 (polish, webs, camera, city, render) — chapters on screen
0:00 Animation tweaks · 1:33 Adding imperfections · 2:40 Fixing anatomical errors · 4:10 Hand animation · 7:30 Feet animation ·
8:00 Adding webs · 9:30 (webs) hooks · 13:25 (webs) geometry · 14:39 (webs) web-sling animation · 16:31 Adding the camera ·
19:51 Smoothing paths · 20:23 Randomized noise (performance) · 22:57 Randomized noise (camera) · 24:57 Lighting/HDR ·
25:22 Ground setup · 27:11 (ground) cars · 33:01 Other objects · 35:45 Rotating the HDR · 35:59 Camera settings ·
36:32 Web materials · 37:09 Background image · 38:24 final render plays
1. Tweaks: stronger leg kick into cannonball, less Y rotation at start, extra kick of turn speed. Imperfections: offset/rotate values a bit.
2. Anatomy: Material Preview to see suit stretch; shoulder lump fixed with the 2 shoulder tweak circles (rotate, key loc/rot, Alt+R/Alt+G when not needed).
3. Hands: View > Lock to active on hand bone. Rig curls a whole finger from its top bone. Fist while holding web, relax when letting go,
   web-shooting pose (thwip) when firing, reuse fist keys with Shift+D. Tiny finger moves through the shot. Feet: R X X, trail behind legs.
4. Webs (per web): cursor to wrist bone, plane -> delete all but 1 vertex, snap to wrist, E extrude to building hit point, subdivide.
   Ctrl+H Hook to new object x2 (wrist end + building end). Cloth sim; vertex group "pin" = both end verts; Shape > Pin group.
   Wrist hook empty: Child Of constraint -> SPIDER-MAN rig, bone hand_fk.R, Set Inverse. Shrinking factor 0.5-1 (taut), key -> 0 on release.
   Let go: key Child Of influence 1 -> 0, then key the empty's location so the loose web flies on. Cache bug: touch any physics value to refresh.
   Geometry: Screw modifier (angle 0.02) + Solidify + Subdivision. Bake cache. Shoot-out: key building-end empty from hand to building.
   Visibility: key collection/object hide_viewport + hide_render. End of swing: key tension 1 -> 0 so it flails.
5. Camera: duplicate Spider-Man path -> "Camera Path", trim ends, pull back. New camera + Follow Path (Alt+G), offset 0 -> -100 linear,
   key rotations to frame Spidey (camera view in one pane), 24 mm (was too telephoto), many tweak passes.
6. Smoothing: both curves -> higher Resolution + Smooth.
7. Noise: graph editor Noise modifier on Spidey empty rot X/Y/Z (strength ~0.3-0.5, different offsets), then per body part.
   Camera: TWO noise modifiers per rotation channel = slow fluid sway (big scale) + micro shake (tiny scale/strength).
8. World: Environment Texture + Mapping + Texture Coordinate (Generated). HDRI = quarry_03_8k.hdr from HDRI Haven (Poly Haven, CC0). Rotated later.
9. Ground: Import Images as Planes -> top-down NYC street photo (stock aerial with yellow taxis), knife (K) to cut out its buildings,
   crossroad shape, extra patches duplicated. Cars: wireframe car-shaped stencil planes over each car -> Knife Project (F3) ->
   extrude up + bevel (Ctrl+B) -> second material "cars" (lower roughness), smooth shading + autosmooth 60.
   Intersection cars painted out of the photo (After Effects) and replaced by a real 3D truck (Free3D, KamAZ 5511) animated linear.
   Some car blocks separated (P > loose parts, origin to geometry) and animated driving. Same knife-project trick for sidewalk boxes + "people".
   Trees: CG Geek "tree in under a minute" method. Rule: "make it as low-poly and as shitty as you can" (camera moves fast).
10. Camera settings: DOF on, focus object = Spider-Man Empty, f/1. Motion blur on. Quick renders to judge.
11. Web material: Principled (transmission up, roughness down) mixed with Translucent.
12. Background: image of NYC skyline (Google image) on a plane far behind, shader bypassed (texture -> output = emission) so HDRI hills are hidden.
13. Final: ~6 s continuous shot, Cycles.

## Licence notes for OUR version (his stock pieces can't be copied)
- HDRI: Poly Haven CC0 = fine (pick a city/clear-sky one). Truck/cars: need CC0/CC-BY models (credit) — not Free3D unknown licence.
- Aerial street photo + NYC skyline image: his were stock/Google images -> we need public-domain/CC sources or our own render.
- Spider-Man is Marvel IP: fan art, non-commercial framing; his rig/suit = his free asset pack (credit Peter France).
