# Claude Blender Skills

Free Claude skills that make **realistic Blender animations**. Each one is the complete workflow behind one of my YouTube videos,
with the real scripts that made the shot. Install a skill, tell Claude your idea, and it plans, builds, lights, animates and
renders the scene in your Blender. You don't need to watch the videos first.

![Clay vs final render of the night FPV drone shot](docs/img/thumbnail.jpg)

| Skill | What it makes | Video |
|---|---|---|
| [`blender-film`](skills/blender-film/SKILL.md) | 10 s night FPV drone shot through a city: storyboard, real physics path, night lighting, sound designed from the 3D motion, overnight render, white clay build-up reveal | [How I Built This Insane Realistic Animation Using Claude in Blender](https://www.youtube.com/watch?v=ZN-Ugd-4HDM) |
| [`blender-forest`](skills/blender-forest/SKILL.md) | Ultra-realistic forest with a car driving through it, built by following a long tutorial: own scatter system, own car rig, render benchmark | [How to Make an Ultra-Realistic 3D Environment Using Claude](https://www.youtube.com/watch?v=Udahf4a0UwQ) |
| [`blender-car-film`](skills/blender-car-film/SKILL.md) | 20 s cinematic story film on a snowy night: real car model, set built in Python, snow particles, 6 hand-held cameras, render from 5-8 h down to 1 h | [How I Built This 3D Short Film With Claude in Blender](https://www.youtube.com/watch?v=BagZ55ac4xs) |

<p>
<img src="docs/img/night_final.jpg" width="32%" alt="Night city drone shot">
<img src="docs/img/forest_car.jpg" width="32%" alt="Car in a sunlit forest">
<img src="docs/img/car_film.jpg" width="32%" alt="Snowy night car film">
</p>

## Contents

- [What you need](#what-you-need)
- [Install](#install)
- [Quick start: your first shot](#quick-start-your-first-shot)
- [How Claude controls Blender](#how-claude-controls-blender)
- [The skills in detail](#the-skills-in-detail)
- [Rules that make it look real](#rules-that-make-it-look-real)
- [Render without losing a night](#render-without-losing-a-night)
- [Safety](#safety)
- [FAQ](#faq)
- [Credits](#credits)

## What you need

- **Claude**. Claude Code works best, because Claude can run the scripts and look at the renders itself.
  The workflows also work in a normal Claude chat: Claude writes the scripts, you run them.
- **Blender 4.4 or newer** (everything was made on Blender 5.2), free from blender.org.
- **A GPU** for Cycles. All three films were rendered on one NVIDIA RTX 5070 (12 GB). Smaller GPUs work, renders just take longer.
- **Python 3** and **ffmpeg** on your PATH. `numpy` and `scipy` for the physics and sound steps of `blender-film`.
- **Your own assets**: a city or environment pack you own, or free CC0 assets from Poly Haven. No paid add-ons are needed.

## Install

### Claude Code (recommended)

Windows (PowerShell):

```powershell
git clone https://github.com/mromidev/claude-blender-skills.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force claude-blender-skills\skills\* "$HOME\.claude\skills\"
```

macOS / Linux:

```bash
git clone https://github.com/mromidev/claude-blender-skills.git
mkdir -p ~/.claude/skills
cp -r claude-blender-skills/skills/* ~/.claude/skills/
```

Restart Claude Code. The skills load by themselves when you ask for "a cinematic Blender shot", "a realistic forest in Blender",
"a short film in Blender", or any single step ("night lighting for my city", "a clay build-up reveal").

### Claude app (claude.ai / desktop)

If your Claude app lets you add custom skills, zip one skill folder (for example `skills/blender-film`) and upload it there.

### Any chat, no install

Open a skill's `SKILL.md`, copy all of it into a new Claude chat, then describe your idea. Add the scripts you need from that skill's
`scripts/` folder when Claude asks for them.

## Quick start: your first shot

1. Install the skills (above).
2. Make a project folder, for example `~/blender-film`, and open Claude Code in it.
3. Open Blender. In the **Scripting** tab, open `tools/bridge.py` from the `blender-film` skill and press **Run Script**.
   Blender now listens on `127.0.0.1:9876` (only your own PC can reach it).
4. Paste this into Claude Code:

   ```
   Use the blender-film skill. My idea: [a drone flying through a canyon at sunset / a car chase at night / ...].
   My assets: [what you have, or "free Poly Haven assets"]. Start with step 1: write the storyboard and wait for my approval.
   ```

5. Approve the storyboard, then let Claude go step by step. After each step it renders a small test still so you can check it.
   It asks before any long render.

## How Claude controls Blender

```
Claude Code  --python tools/send.py script.py-->  bridge.py inside your open Blender (127.0.0.1:9876)
     ^                                                         |
     +---------------- output, errors, test renders <----------+
```

- `tools/bridge.py` runs inside Blender and executes the Python it receives on Blender's main thread.
- `tools/send.py` sends a script file (`python tools/send.py scripts/06_night.py`) or one line
  (`python tools/send.py -c "print(bpy.data.filepath)"`) and prints what came back.
- You watch every change happen in your own Blender window. Long renders run in background Blender (`blender -b`) from a saved file.

## The skills in detail

### `blender-film`: night FPV drone shot

![Drone on the night avenue](docs/img/shot2.jpg)

1. **Storyboard first.** A 10-second shot list with timings, camera per shot, where the hero is. Turned into one image sheet.
2. **City.** 5 buildings from an asset pack copied, stretched and recoloured into 173 instances. Cars, lamps, trees, hydrants.
3. **Motion from physics.** A point-mass simulation (24 fps, 1/480 s steps, gravity, quadratic air drag, ropes that can't stretch)
   searches the anchor timings until the path threads the street. Path curve + empty on Follow Path, offset keyed every frame.
4. **Hero and the pivot.** The first hero was a rigged Spider-Man with Mixamo motion capture. It looked stiff, because mocap is
   recorded on the ground. Swapped for an FPV drone on the same path: thrust axis = acceleration + gravity, nose along the velocity,
   throttle cuts where the path is ballistic, power flip, barrel roll, back flip, braking flare into a hover.
5. **Realism pass.** AgX exposure, thin haze, asphalt wear, oil drip line, repair patches, dirt at the foot of every wall.
6. **Night.** Practical lights only. Windows found from the facade roughness map (glass is smooth): `roughness < 0.3` = glass,
   then a random subset lit warm, cool or off. LED street lamps at 3200 K, car lights, red signals, blue fog, wet asphalt.
7. **Camera.** Camera Shakify (real recorded shake) on every camera, a street-level lens 0.45 m above the wet road, bloom and slight
   barrel distortion, no colour grade.
8. **Sound from the motion.** The animation is read every frame (distance, radial speed, side, throttle). Throttle drives motor pitch,
   radial speed drives Doppler, side drives the pan, cars pass at their closest approach, street-canyon reverb. -14 LUFS.
9. **Render.** Tree LODs and hidden duplicates removed, six final-quality test stills first, only the frames of the edit rendered,
   resumable, with a progress panel. About 3.5 hours overnight. Then every frame is checked.
10. **Clay build-up.** The whole city in white clay drops from the sky piece by piece (507 pieces, 7 s), then one wipe to night.

![Clay build-up](docs/img/clay_drop2.jpg)

Full step list and all 20 scripts: [`skills/blender-film`](skills/blender-film/SKILL.md).

### `blender-forest`: realistic environment from a tutorial

![Forest car shot](docs/img/forest_car.jpg)

1. Give Claude a long tutorial (1 h+, free assets) instead of a prompt: "We are going to recreate his scene exactly."
2. Claude reads the transcript, captures the reference frames, writes `PLAN.md` with every shot and stage.
3. Every downloaded asset is checked: virus scan, archive listing, `.blend` files opened with `--disable-autoexec` and audited.
4. The world is built in stages: terrain + HDRI world, our own Geometry Nodes scatter (560k-730k instances, replaces a paid add-on),
   gravel path, then a test still next to the reference after every stage.
5. Our own car rig (wheels spin with distance, front wheels steer, body bounce) instead of a rig add-on.
6. A sub-agent measures each reference shot (height, lens, fisheye, speed, cuts); cameras are built from those numbers.
7. Render benchmark: 128 samples + denoise = same look as 256 samples, 51 s -> 28 s a frame. 390 frames at 2560x1440 in about 3 hours.

Full steps and scripts: [`skills/blender-forest`](skills/blender-forest/SKILL.md).

### `blender-car-film`: 20-second story film

![Snowy night car film](docs/img/car_film.jpg)

1. Storyboard: 6 shots, no people, every shot with camera move, timing and key sound.
2. Real car model (CC BY), Poly Haven trees and props; road, snow banks, school, hospital and house built by Claude in Python.
3. 17 numbered scripts sent live into Blender through the bridge: world, car, rig, set, house, animation, snow and fog,
   cameras, fixes, render settings, grade, 30 fps.
4. Render from a 5-8 hour estimate to about 1 hour: adaptive sampling + OptiX denoise, fewer bounces, snow particles baked to disk
   (158 s -> 6 s a frame), culling. A resumable render queue with a progress window.

Full steps and scripts: [`skills/blender-car-film`](skills/blender-car-film/SKILL.md).

## Rules that make it look real

- **Storyboard before Blender.** Every later decision gets checked against it.
- **Real assets, not generated ones.** Claude is great at code, cameras, physics and render settings. Let downloaded models and
  real recorded sounds do the rest.
- **Motion from physics, not hand-keyed curves.** Real speed, real gravity, real braking.
- **At night, practical lights light the scene, not the sky.**
- **Tiny imperfections**: dirt at wall bases, worn road paint, oil lines, haze, real camera shake.
- **No colour grade by default.** The look comes from the lighting. Grade only a shot that needs it.
- **If the hero looks wrong, change the hero.** Keep the city, path and cameras.
- **Test small, render big.** Low-quality stills after every step, final quality only at the end.

## Render without losing a night

- Render only the frames the edit uses, as a PNG sequence, so a crash or power cut loses one frame at most.
- Every render script is resumable: run it again and it continues where it stopped.
- Benchmark first. Denoising often lets you halve the samples with no visible difference.
- Bake particle and physics caches to disk before the final render.
- Persistent data keeps a heavy scene in GPU memory between frames.
- A progress window shows frames done and time left; the stay-awake scripts keep Windows awake without changing any settings.
- After the render, check that every frame exists and none is black or broken before you encode.

## Safety

- The scripts here are plain Python, PowerShell and shell scripts. Read them before you run them, or ask Claude to explain them.
- The bridge only listens on `127.0.0.1` (your own PC). Stop it by closing Blender.
- Open any `.blend` you download with `--disable-autoexec` first, and check it for embedded scripts.
- Scripts that call ElevenLabs read your key from the `ELEVENLABS_API_KEY` environment variable. No keys are stored in this repo.

## FAQ

**Do I need the same assets?** No. Object and material names in the scripts come from the original scenes. Tell Claude what you
have and it adapts the scripts.

**Mac or Linux?** The Blender and Python parts work everywhere. The `.ps1` and `.cmd` helpers are Windows-only. Ask Claude for the
shell version.

**No NVIDIA GPU?** Use Cycles with your GPU's backend (Metal, HIP) or EEVEE for previews. Renders take longer.

**How much Claude usage does it take?** The 20-second car film used about 20% of a weekly Claude limit.

**Can I use this for my own videos?** Yes, MIT license. A credit or a link back is appreciated.

## Credits

Assets and references used in the original films (not included in this repo):

- City and Spider-Man asset pack: Peter France
- Clay build-up idea: Abrar Ahmed ("CINEMATIC CITY")
- Realism and night lighting references: Extra 3d, Enhanced Sight
- Forest tutorial and assets: roe.num77 ("Blender Hyper-Realistic Forest Tutorial")
- Animations: Mixamo (Adobe)
- Models: BlendKit, Poly Haven (CC0), "Peugeot 504" by 3d_engineer (Sketchfab, CC BY 4.0)
- Sound: BigSoundBank.com (CC0), ElevenLabs
- Camera shake: Camera Shakify add-on

Spider-Man is a Marvel character. The Spider-Man part was non-commercial fan art; no Marvel assets are in this repo.

## Author

Made by **Mr omi** with Claude.
YouTube: [Mr omi](https://www.youtube.com/@mr_omix) · Instagram: [@mromi.ai](https://www.instagram.com/mromi.ai/) ·
Business: contact@mromi.dev

License: [MIT](LICENSE)
