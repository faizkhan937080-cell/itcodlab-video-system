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
- Faiz never downloads or attaches anything. Worker copies the pack (collages, metrics, index) to GitHub
  branch `review`, folder `review/<job>/` (branch keeps ONLY the newest job). Only exception to "outputs go to Drive": it is small (~1-2 MB/job).
  Claude runs `python3 -m scripts.review <job> <dir>` then views the jpgs with Read. State key: `review`.
- If `review.status` is failed: read `review.error`, fix, never ask Faiz to download.
- Text route (no card): worker asks a free Gemini API key (env GEMINI_API_KEY) to describe every tile.
  Result: `analysis/<id>/pack/descriptions.json`. Claude reads it as text, plus `metrics_summary.json`.
  It is facts from a vision model, may miss detail: say so. Without it, never invent what a frame shows.

## Candidates
- Claude writes `analysis/<id>/dna/candidate-<type>-v<K>.json` (types per mode: video=editing,
  audio=sound, both=editing+scripting+sound). `source.job_id` must equal the job id.
- Invalid candidate -> worker asks for v<K+1>. Never overwrite a version.

## Local commands (`./run`, only these)
doctor, selftest, analyze-local, validate, render-local, worker, status, new-job, approve.
