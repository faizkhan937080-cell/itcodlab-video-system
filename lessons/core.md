# lessons: core

Read this before every task. Faiz allowed Claude to save lessons itself (compact, machine style, few tokens).
One line per entry: mistake | cause | rule. Past 60 lines: merge old entries, lose nothing.

## Entry format
M: mistake | C: cause | R: rule

## Entries
M: job id 'r1' rejected | C: schema needs 3-60 chars | R: ids like test-render-001
M: Colab drive.mount MessageError | C: Allow popup not completed, 2 tabs open | R: one tab, force_remount, click Allow
M: Colab Gemini says "I will run" but nothing runs | C: it needs Accept and run click | R: user clicks it, or Run all
M: GitHub token pasted in chat | C: user wanted it in a prompt | R: never repeat it, keep in runtime env only, revoke after setup
M: GitHub PAT value not visible again | C: shown once | R: Regenerate token, copy at once
M: Remotion browser download blocked in sandbox | C: network allowlist | R: set ITCOD_BROWSER to installed Chromium
M: Drive connector images unreadable | C: returned as base64 text | R: user attaches collages in chat
M: browser-agent Gemini stalls on confirm | C: asks before Generate/Delete | R: say "no confirmation needed" in prompt, never delete old tokens
M: Drive sync lag after file write | C: mounted Drive delay | R: wait ~60 s before reading state
M: Colab userdata unusable inside `!` shell | C: only the notebook kernel has it | R: copy secrets into os.environ in a cell before the worker cell
M: whisper crashed whole analysis (av version clash) | C: optional step not isolated | R: every optional step must catch errors and return available:false
M: diagnosed 'weird face' without seeing the collage | C: Claude could not view Drive images | R: publish pack to review branch, view it, then judge
M: Faiz asked to download/attach images | C: no self-fetch path | R: worker publishes to review branch; Faiz does nothing
M: collages had red/blue swapped (purple skin), I blamed tile size | C: PIL RGB array pasted into BGR canvas; no color test | R: every image path gets a color regression test; look at real pixels before diagnosing
M: DNA numbers typed by hand can be wrong, transcript covered 8 of 58 s unnoticed | C: no cross-check, no coverage field | R: dna-draft pre-fills measured parts; dna-check must PASS; transcript coverage<0.9 = estimated only
M: approval page built for a user who listens, not reads | C: assumed a UI helps | R: ask Y/N in chat, short Hinglish, always
M: output size fixed at 4K master | C: ignored the raw source size | R: output = largest raw clip size; test with 4K portrait rotation tag
M: numpy int64 crashed json.dumps twice on a real reel (script_metrics.json, then the pack summary); 194 green tests missed it | C: tests used plain Python numbers; sum() of np.bool_ gives np.int64 | R: pipeline results go through common.to_native() / default=json_default; tests feed numpy values; first real run of new code = read the job state at once
M: worker run ended mid-analysis; next run would fail the last attempt (source path was on the old runner) | C: state kept a machine-local path, no resume code | R: stage that needs a local file restores it from the Drive copy first (_ensure_local_source); every new stage: ask 'what if the next run is a fresh machine?'
M: new Kaggle API token pasted into KAGGLE_USERNAME box (wrong secret) | C: two similar secret pages, user copied into the open one | R: Gemini prompt names the exact secret + URL; Kaggle KGAT_ token = KAGGLE_API_TOKEN env (kaggle_gpu._env maps it)
M: Gemini describe blocked on 3 of 6 collages (HostBlocked from GitHub worker IP) | C: cloud IP restricted by Gemini for the free key | R: describe partial is normal: Claude views collages itself via review branch; log describe.status=failed in report, never invent tile content
M: Claude ran ffprobe/ffmpeg itself, sent a 118 MB file to chat, asked for home-folder access, hooks were off (cwd was not the repo). R: guard now covers Read/SendUserFile/pytest, `./run guard-install` makes hooks global, `./run check` on every prompt.
