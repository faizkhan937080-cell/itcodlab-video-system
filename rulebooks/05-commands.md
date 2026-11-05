# 05 commands and channels

Faiz types a command in chat. Claude does the rest. The worker (Colab now, VM later) only runs scripts.

## Command channel (Drive, no extra tools)
- Claude writes `jobs/inbox/<id>.json` (job id = 3-60 chars, letters/digits/_/-).
- Worker writes `jobs/state/<id>.json`. Claude reads it and tells Faiz the status in 1 line.
- Approval file `jobs/approvals/<id>__gate<N>__r<rev>.json` is written ONLY after Faiz says Y/N in chat.
- Rev: gate2 = 1, gate3 = candidate version, gates 4-6 = plan version.
- Colab cannot be started from chat. Faiz opens the notebook and presses Run all. It then polls Drive.

## Chat commands (examples)
- "analyze <link> both creator" -> target creator:auto (handle read from link). "... general" -> general
- "analyze <link> both general" -> analyze job (mode video|audio|both, target general|creator:<name>)
- "approve gate 2" / "reject gate 3, palette dull" -> approval file with feedback
- "render <idea>" -> render job, then scene plan `jobs/plans/<id>-v<N>.json`
- "status" -> read all `jobs/state/*.json`

## Collages (Claude must SEE them)
- Drive connector returns images as base64 text, so Claude cannot view them from Drive.
- Faiz attaches the collages in chat (max 10), or Claude Code reads a synced local folder.
- Without a view, Claude uses only `metrics_summary.json` and says so. Never invent what a frame shows.

## Candidates
- Claude writes `analysis/<id>/dna/candidate-<type>-v<K>.json` (types per mode: video=editing,
  audio=sound, both=editing+scripting+sound). `source.job_id` must equal the job id.
- Invalid candidate -> worker asks for v<K+1>. Never overwrite a version.

## Local commands (`./run`, only these)
doctor, selftest, analyze-local, validate, render-local, worker, status, new-job, approve.
