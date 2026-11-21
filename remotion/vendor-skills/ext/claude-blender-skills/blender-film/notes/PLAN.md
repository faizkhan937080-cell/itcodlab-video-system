# Spidey video — plan (draft, 2026-10-24)

Reference: Peter France, "Creating a Spider-Man Scene in Blender" Parts 1-3 (69 min total, watched fully;
notes = research/WORKFLOW_NOTES.md, frames = research/sheets, his final shot = research/final).
Assets = his free pack (Spider-Man.blend Rigify rig + suit, Buildings.blend 5 buildings), checked in Blender 5.2: rig loads,
IK_FK switches present, rig_ui.py (standard Rigify UI, read through, safe) registers fine.

## 1. What he does (one line per stage)
1. Rig: open as trusted, set arms/legs to FK, hide IK bone layers. Suit = node groups + hand-painted masks + bump maps.
2. City: append 5 buildings, duplicate/raise them into a street + intersection that fits the shot in his head.
3. Path: Bezier curve through the street -> Spider-Man Empty (Follow Path, offset 0 -> -100, LINEAR) -> rig parented to empty.
4. Momentum: rotate the EMPTY (linear extrapolation = keeps spinning; a new web is the only thing that changes the spin).
5. Body: hand keys, centre outward: hips -> torso -> head -> legs -> arms -> hands -> feet, then tweaks, noise, shoulder fixes.
6. Webs: 1-vertex line, 2 hooks, cloth pinned, Child Of hand bone, shrink/tension/influence keys, Screw+Solidify+Subsurf, bake.
7. Camera: copy of Spidey path, Follow Path, 24 mm, rotation keys, 2 layers of noise (sway + micro shake).
8. Ground: aerial street photo on a plane, cars/people = knife-projected extrusions, 1 real truck, moving cars, trees.
9. Look: HDRI, DOF f/1 on the empty, motion blur, translucent web shader, skyline image far behind. Cycles. ~6 s one-take shot.

## 2. What we do the same / differently
SAME (his method, step by step, so the video can follow his chapters):
assets, FK setup, street layout, path + empty + linear offset, empty-rotation momentum, webs (hooks + cloth),
camera path + noise, aerial-street trick for far ground, HDRI + DOF + motion blur, Cycles.

DIFFERENT (your rules):
- NO hand-keyed body animation and NO modelling -> Mixamo clips for the body:
  you sign in to Mixamo (free Adobe account, I can't log in for you), upload our Spider-Man mesh so the clips fit his proportions,
  download in-place clips (search: swing, hang, fall, flip, jump, superhero, land) as FBX.
  Our own small retarget script maps Mixamo bones -> his Rigify FK controls and bakes keys (no download needed).
  Backup if mine isn't clean: Mixaify (free open-source Mixamo -> Rigify for Blender 5) — I show it to you before installing.
  Clips are blended in the NLA; his path + empty still does the big flight; I only add small fix keys (head look-at, hands, shoulders).
  Mixamo is 30 fps, his scene 24 fps -> retime on import.
- Claude does the Blender work through Python (live bridge, like the car film); you see each step in Blender.
- Cars near camera = real free 3D models (CC0 / CC-BY with credit); far street = aerial-photo trick with a public-domain image.
- HDRI from Poly Haven (CC0). No Google images.
- Scene length = what the storyboard says (you said ~20 s; his is 6 s). 20 s = 480 frames at 24 fps.
  Render guess on the 5070: 20-40 s/frame at 1080p -> 3-5 h overnight (I ask before any render).

## 3. Storyboard step (next)
You give ChatGPT the prompt in CHATGPT_PROMPT.md + screenshots of a Spider-Man scene you like.
It returns storyboard frames + a shot table + top-down map. You send me those.
I check every shot against what the assets/physics/Mixamo can do, then we lock the board.

## 4. Build order (each step = one OBS clip of Blender + chat, saved after each step)
1. Project folder + assets + storyboard on screen (Finder)  2. Open rig, FK, suit shader tour
3. Append buildings, lay out the street from the storyboard map  4. Append Spidey, clean junk
5. Path + Spider-Man Empty + Follow Path + linear offset  6. Empty rotations (momentum, flips)
7. Mixamo clips -> retarget -> NLA blend -> small fix keys  8. Shoulders / hands / feet polish
9. Webs (hooks, cloth, Child Of, release, geometry, bake, visibility)  10. Camera path, 24 mm, framing
11. Smooth paths + noise (Spidey + 2-layer camera)  12. HDRI + aerial street + cars + truck + people + trees
13. DOF, motion blur, web material, skyline backdrop  14. Test renders -> overnight render -> final

## 5. The video (built in the fake MacBook desktop editor, approved desk-motion style)
Story: "How I made this insane Spider-Man animation in Blender using Claude".
Open on the final shot -> project folder, assets, storyboard, his tutorial (credit Peter France) -> then step by step
through the build order above -> final render full screen -> outro.
Recording: OBS (~/obs-control/obs.ps1), key moments only (new step starts, visible change, first playback, bugs + fixes,
renders) — no long waits. Clip index with clock times in NOTES.md so chat export and footage line up.
Voice: MD Voice, one section at a time, all voices first, one stitched track, then the edit.

Length: ~15 min (user confirmed 2026-10-24). Rough split:
hook + final shot 0:00-0:45 · folder/assets/storyboard/his tutorial 0:45-2:00 · rig + suit 2:00-3:00 ·
city layout 3:00-4:15 · path + empty + momentum 4:15-6:00 · Mixamo body 6:00-8:30 · polish 8:30-9:15 ·
webs 9:15-10:45 · camera + noise 10:45-12:00 · city dressing + look 12:00-13:30 · render + final 13:30-14:30 · outro 14:30-15:00.

## Open questions
- Mixamo: are you OK signing in yourself when we reach step 7?
