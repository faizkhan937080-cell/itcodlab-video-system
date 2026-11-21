# Vendored: remotion-dev/skills (official), version 4.0.543
Source: https://github.com/remotion-dev/skills (MIT-style, Remotion licence applies to Remotion itself).
Copied: markdown guidance only (no scripts, no assets). Scanned: no network, exec or injection text.
Use: read the router `remotion-best-practices/SKILL.md`, then only the sub-file the task needs.
Rule: never edit these files; to update, re-vendor the whole folder and bump this version line.

# ext/claude-animated-shorts (2026-11-21)
Source: https://github.com/mromidev/claude-animated-shorts @ e3b817b, MIT. Copied: SKILL.md, STYLE_BIBLE.md, README, LICENSE and references/reports/*.md (camera, depth, grade, lighting, motion, outlines, textures, characters). NOT copied: frames/ and sheets/ (stills of another channel's videos; our repo is public) and no scripts. Scanned: no network, exec or injection text.
Use: how to build a 3D cartoon-world short with three.js inside Remotion (pipeline, camera, lighting, outlines).
Its "user rules" (no captions, English only, 2K export) are the original author's, NOT ours: our rules in CLAUDE.md win. Never copy its characters, scripts or shots.

# ext/claude-blender-skills (2026-11-21)
Source: https://github.com/mromidev/claude-blender-skills @ 567116b, MIT. Copied: README, LICENSE, SKILL.md + notes/*.md of blender-car-film, blender-film, blender-forest. NOT copied: scripts/tools (several use subprocess/network; scan did not pass for a blind copy). Use: realistic Blender shot workflows (storyboard, set built in Python, physics path, camera, realism pass).

# ext/stickman-video-director (2026-11-21)
Source: https://github.com/kaomei/stickman-video-director @ 9431d37, MIT. Copied: LICENSE, SKILL.md, references/*.md. NOT copied: assets/ (audio library, images; 800 MB), docs, translations. Use: 2D stickman / rubber-hose / pixel styles; Mode A writes prompts for AI video models (paid, not for us), Mode B = Code Engine (code-built 2D video) is the one to read. Some guidance is in Chinese. Its paid-model and paid-narration steps do not apply: free tools only.

# ext/rossark-motion-skill (2026-11-21)
Source: https://github.com/rossark0/rossark-motion-skill @ 9b20964, MIT. Copied: SKILL.md, MOTION.md, README, LICENSE, templates/ (React Native + SwiftUI motion code, reference only). NOT copied: demo gifs/mp4/swift, tools/*.sh|py. Use: believable motion for drawn things (blinks, breathing, head tilt, landing, fabric, fire, plants) -> apply the same curves in our Remotion shots.

# ext/viral-hooks-skill (2026-11-21)
Source: https://github.com/rediumvex/viral-hooks-skill @ e26b339, MIT. Copied: SKILL.md, hooks-database.md (100 hook formulas), README, LICENSE. Use: pick the hook for every script; then our script gate still decides.

# ext/claude-video-watch (2026-11-21)
Source: https://github.com/bradautomates/claude-video @ 03ceb42, MIT. Copied: SKILL.md + LICENSE only, as REFERENCE. Do NOT run it: it downloads with yt-dlp and sends video to Gemini, which breaks our hard rules. Our own analysis worker does this job.
