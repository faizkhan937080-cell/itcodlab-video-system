# itcodlab video system - router

Claude = brain (coding + creative decisions). Worker (free Colab now, Google Cloud VM later) = muscle.
Do NOT guess. Read only the files your task needs. Keep every rule, lesson and memory file under 60 lines (code is exempt: split by module).

## Before ANY task
-1. New container/session? `./run guard-install` once (hooks must fire from any folder). `./run check` is automatic; fix what it prints.
0. Run `./run mem brief` (state + index). Before asking Faiz anything: `./run mem find <word>`.
1. Read `rulebooks/00-core.md` and `lessons/core.md`. Problem that comes back? `lessons/toolbook.md`.
2. Then read ONLY the rulebook + lessons for your task type:
   - chat commands, jobs, Drive queue, collages -> `05-commands.md`
   - video / motion / Remotion code -> `01-video.md`, `lessons/video.md`
   - scripting (general or creator)  -> `02-scripting.md`, `lessons/scripting.md`
   - DNA building / merging          -> `03-dna.md`, `lessons/dna.md`, and the standard of its type:
     `07-standards-editing.md` | `08-standards-scripting.md` | `09-standards-sound.md`
   - choosing a tool / render quality -> `10-tools.md`; output size = raw source size (`01-video.md`)
   - folders, reel IDs, clients/, assets/library, licences, audit -> `12-structure.md`
   - network, downloads, bans, virus/secret checks, workflows -> `15-security.md`
   - colour grade / look / HDR, editing effects (speed, zoom, track, voice) -> `13-grade.md`, `14-effects.md`
   - pro-editing standards, QA gate, cover, beats, J/L cuts -> `16-pro-editing.md`
   - making analysis/render faster (and proving no quality loss) -> `17-speed.md`
   - time, cost, price per video, free quotas, plan comparison -> `19-costs.md`, `costs/README.md` (`./run cost ...`)
   - copyright / licence alerts, YouTube + Reels policies, memes, trending audio -> `18-platform-copyright.md`
3. Every step that saves, adds or renders needs approval: `rulebooks/04-approvals.md`.
3a. After writing any job, approval or candidate: `./run wake` (starts the no-PC worker). Hosting: `rulebooks/11-hosting.md`.
3b. Lanes, barriers, alerts, token economy: `rulebooks/06-fence.md` (hook `scripts/guard.py` blocks wrong-lane commands).
4. Limits live in `config/limits.json`. Never override them.

## Hard rules (short)
- Claude never runs ffmpeg, yt-dlp, whisper, rclone, curl, remotion render. Scripts do. Use `./run <command>` only.
- Claude never reads raw video, audio or frames. Only collages (max 10) + metrics summary.
- Claude deletes only approved dev scrap, via Drive trash (see 00-core). Versions are added (dna-v1, dna-v2), never overwritten.
- No Meta Ads work. No numerology. No auto-publishing anywhere.
- Max 2 Claude calls per stage. After 2 failed retries: status FAILED and stop.
- Every job step is measured (`stage()` + cost row). New step or new service = add its measurement + `config/pricing.json` rate. Quote time/cost from `./run cost estimate`, never guess (`19-costs.md`).
- Error logs: read only the last 20 lines.
- Outputs go to Drive via scripts. Rules and lessons go to GitHub only.
- Lessons: Claude saves them itself (compact). Decisions/findings: `./run mem add <shard> <text>` at once, long form, never summarised.
- Faiz approvals: ALWAYS in chat (short Hinglish, Y/N). Never a page, doc or tab. He listens, he does not read.
- Faiz downloads and attaches nothing. Collages come via GitHub branch `review` (`./run review-fetch <job> --out <dir>`).

## Story (kahani update) - memory discipline
- Faiz says "kahani update" (or "story update"), or a work chat just ended: run `./run story` after adding anything durable
  (`./run mem add <shard> <text>` decisions/context, lessons/ for mistakes, `memory/state.md` rewritten). Do it on your own, unasked.
- Durable = context reused later, learnings, Faiz's rules/preferences, state changes. Not chatter, never secrets of others.
- Before starting ANY development: read `./run mem brief` (state+index), then `./run mem find <word>` for the topic.

## Where things live
- GitHub: rules, lessons, config, scripts, Remotion code.
- Drive (`config/drive.json`): input, assets, analysis, dna, output.
- Sheet `ITCODLAB-VIDEO-CONTROL`: Jobs, DNA_Index, Creators, Approvals.
