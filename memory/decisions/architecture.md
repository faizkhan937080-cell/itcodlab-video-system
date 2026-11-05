# architecture
keys: architecture colab gcp github drive sheet remotion 4k limits worker
- 2026-11-05 20:48Z Claude is the brain (code + creative decisions). The worker is the muscle: free Google Colab now (colab/itcodlab_worker.ipynb, polls every 20 s), Google Cloud VM later once Faiz adds a credit card (he has none now).
- 2026-11-05 20:48Z GitHub repo faizkhan937080-cell/itcodlab-video-system (private, main): rules, lessons, config, scripts, Remotion code. Drive folder ITCODLAB-VIDEO: input, assets, analysis, dna, output. Optional Sheet ITCODLAB-VIDEO-CONTROL: Jobs, DNA_Index, Creators, Approvals.
- 2026-11-05 20:48Z Faiz works only by chat commands. Claude writes jobs/inbox/<id>.json to Drive; worker writes jobs/state/<id>.json; approvals jobs/approvals/<job>__gate<N>__r<rev>.json only after his explicit Y/N.
- 2026-11-05 20:48Z Renders are 4K (3840x2160, crf 16) because his Drive footage is 4K; a 0.5-scale preview comes first. Remotion v4 is the motion engine.
- 2026-11-05 20:48Z His own Windows PC has 4 GB RAM and ~128 GB disk, so nothing heavy runs there.
- 2026-11-05 20:48Z Claude never runs ffmpeg, yt-dlp, whisper, rclone, curl or remotion directly. Scripts do, via ./run only.
- 2026-11-05 20:48Z Limits live in config/limits.json and are never overridden: 2 Claude calls per stage, 2 retries then FAILED, daily job cap 5, error logs last 20 lines, every file under 60 lines.
- 2026-11-05 20:48Z Worker self-updates: every 15 polls (~5 min) git pull --ff-only; if code changed it restarts itself. Needs the Colab clone's git remote to hold a token.
- 2026-11-05 20:48Z Colab facts: Python 3.13; drive.mount needs the Allow popup; Gemini 'Accept and run' must be clicked; 'secret access' popup -> Cancel (token is in os.environ); free Colab idles and stops after ~12 h; google.colab.userdata does not work inside the ! shell.
- 2026-11-05 21:40Z 2026-11-06 Faiz: fence the lanes. Claude does brain work only; Colab/worker does its own jobs and reports back; Faiz does not want Claude tokens spent on worker tasks. Built: rulebooks/06-fence.md, scripts/guard.py PreToolUse hook (blocks heavy tools, curl, deletes, secrets), token-economy waiting rules, STOP/ALERT barriers. Also: self-update import-check + rollback, review branch single-job force push, finished jobs not re-read, review retry cap 4.
