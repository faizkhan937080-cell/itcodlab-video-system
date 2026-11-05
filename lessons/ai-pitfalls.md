# ai-pitfalls: how AI sessions go wrong, and the guard we use (read when planning long work)
Format: P: pitfall | G: guard.

P: summary drift (details lost after compaction) | G: ./run mem add each decision at once, full sentence; ./run mem brief at session start
P: forgets its own output (ids, file names, versions) | G: state.md holds ids/versions; log shards hold commits; never rely on chat
P: says "done" without checking | G: read the state file / run the test / view the image before reporting; no success claim on assumption
P: stale facts (job status, file lists) | G: re-read Drive state before answering "status"; never answer from memory of an old read
P: guesses what an image shows | G: view the collage itself; if unseen say so; descriptions from a model are marked estimated
P: silent scope creep | G: one task per step, tell Faiz what changed in 1-2 lines
P: context bloat (huge logs, base64) | G: tail 20 lines, never print big files, shards under 60 lines, grep not cat
P: secrets leak (tokens in chat, repo, logs) | G: mem add refuses secrets; scrub urls; tokens only in runtime env; regenerate after setup
P: overwriting or deleting good data | G: versions only, fresh dirs, no rm in scripts, deletes need Faiz OK
P: repeated retries of a broken approach | G: max 2 retries then FAILED; change the cause, not the attempt
P: wrong layer for the job (Claude doing heavy work) | G: scripts via ./run only; Claude reads collages + summary
P: unclear human steps | G: one step, exact button name, Hinglish, short
P: rate/cap surprises (daily cap 5 jobs, Colab 12 h idle) | G: check limits.json and state before queuing; tell Faiz when Colab must be restarted
P: model/tool versions drift (Python 3.13, PyAV, Whisper) | G: pin or isolate optional parts; add the symptom to toolbook
P: future: API cost or free-tier limits (Gemini key, Colab GPU) | G: cost check before enabling anything paid; Faiz approves spending
P: future: long videos or many jobs fill Drive | G: report sizes per job; ask Faiz before any cleanup; never auto-delete
