Paste everything below into ChatGPT, and attach 3-8 screenshots of the Spider-Man scene you like.

---

You are a previs storyboard artist for a short 3D animation that will be rebuilt shot by shot in Blender.
The attached screenshots are from a Spider-Man scene I like. Use them only as INSPIRATION for the energy, camera feel and moves —
design a NEW scene, do not copy it frame for frame.

GOAL
A 20-second Spider-Man web-swinging scene through a New York street in daylight. 24 fps = 480 frames.
It must feel physically real: every change of direction or spin is caused by a web pull, a kick off a wall, or gravity.
Momentum carries through; nothing floats or stops dead in the air.

WHAT I HAVE TO BUILD IT (do not design anything outside this list)
- One Spider-Man character (classic red/blue suit, fully rigged). Body moves come from motion-capture clips
  (swinging/hanging with one arm up, falling, front flip, back flip, tuck/cannonball, spread-eagle dive, jump, superhero landing),
  so every pose must be something a real athlete could do.
- Webs = thin white lines from his wrist to a building wall. He holds one web at a time (two only for a slingshot moment).
- City = 5 kinds of old New York apartment/office blocks (brick and stone facades with windows, flat roofs, 22-37 m tall).
  I can copy them, stretch them taller and line them up into streets 15-20 m wide. One street intersection is possible.
- Street level: road with lane markings and crosswalks, yellow taxis, cars, one box truck, a few moving cars, trees,
  tiny far-away pedestrians (never close to camera).
- Sky: clear or light clouds, afternoon sun. A city skyline far in the distance.
- Camera: a real-feeling chase camera (18-35 mm lens), handheld shake, motion blur, shallow depth of field on Spider-Man.
NOT possible: other characters interacting with him, dialogue or face close-ups, interiors, night, rain, explosions,
breaking things, crowds near camera, helicopters, trains, water.

SCENE LENGTH AND CUTS
Total exactly 20 s. Between 1 and 4 shots (one continuous long take is fine). Each shot at least 3 s.

DELIVER, IN THIS ORDER
1. A one-paragraph scene idea (the "story" of the 20 seconds: where he starts, the big moment, where he exits).
2. A TOP-DOWN MAP image: simple diagram of the street blocks (boxes), Spider-Man's path as a line with arrows and
   time marks every 2 s, each web anchor point as a dot, and the camera path as a dashed line.
3. STORYBOARD images: 8-12 panels, 16:9, rough black-and-white pencil storyboard style (NOT photoreal), each panel with
   its timecode (e.g. 0:00-0:02.5), an arrow for Spider-Man's motion and an arrow for the camera move.
   Put several panels on one sheet if that is easier.
4. A SHOT TABLE: shot #, start-end seconds, lens mm, camera position relative to Spider-Man (behind/below/side/above),
   camera move, Spider-Man action, which web is attached (which building, which side of the street, about what height),
   and the moment he lets go.
5. The same data as JSON, exactly in this shape:
{
  "scene_idea": "",
  "fps": 24,
  "duration_s": 20,
  "street_layout": "describe the blocks, street directions and the intersection in metres",
  "shots": [
    {
      "id": 1, "start_s": 0, "end_s": 0, "lens_mm": 24,
      "camera": "position + move", "camera_shake": "low|medium|high",
      "beats": [
        {"t_s": 0.0, "spidey_action": "", "pose_keyword": "swing|hang|fall|front flip|back flip|tuck|dive|jump|land",
         "web": {"attached": true, "anchor": "building + side + height_m", "hand": "left|right"},
         "momentum_note": "what force causes this"}
      ]
    }
  ],
  "web_anchors": [{"id": "A", "building": "", "side": "", "height_m": 0}],
  "notes_for_3d_artist": ""
}

Keep everything buildable with the list above. If an idea from the screenshots is impossible with it, change it and say what you changed.
