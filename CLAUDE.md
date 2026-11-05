# itcodlab video system - router

Claude = brain (coding + creative decisions). Worker (free Colab now, Google Cloud VM later) = muscle.
Do NOT guess. Read only the files your task needs. Keep every file under 60 lines.

## Before ANY task
1. Read `rulebooks/00-core.md` and `lessons/core.md`.
2. Then read ONLY the rulebook + lessons for your task type:
   - chat commands, jobs, Drive queue, collages -> `05-commands.md`
   - video / motion / Remotion code -> `01-video.md`, `lessons/video.md`
   - scripting (general or creator)  -> `02-scripting.md`, `lessons/scripting.md`
   - DNA building / merging          -> `03-dna.md`, `lessons/dna.md`
3. Every step that saves, adds or renders needs approval: `rulebooks/04-approvals.md`.
4. Limits live in `config/limits.json`. Never override them.

## Hard rules (short)
- Claude never runs ffmpeg, yt-dlp, whisper, rclone, curl, remotion render. Scripts do. Use `./run <command>` only.
- Claude never reads raw video, audio or frames. Only collages (max 10) + metrics summary.
- Claude never deletes anything. Versions are added (dna-v1, dna-v2), never overwritten.
- No Meta Ads work. No numerology. No auto-publishing anywhere.
- Max 2 Claude calls per stage. After 2 failed retries: status FAILED and stop.
- Error logs: read only the last 20 lines.
- Outputs go to Drive via scripts. Rules and lessons go to GitHub only.
- Lesson draft after a mistake: write it, ask approval, then save.

## Where things live
- GitHub: rules, lessons, config, scripts, Remotion code.
- Drive (`config/drive.json`): input, assets, analysis, dna, output.
- Sheet `ITCODLAB-VIDEO-CONTROL`: Jobs, DNA_Index, Creators, Approvals.
