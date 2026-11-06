# 17 Speed without losing precision
Rule 1: a speed-up is allowed only if the result is IDENTICAL (or better) on the same input. Prove it with a test that compares both paths.
Rule 2: final render and analysis keep full quality. Only the waiting is cut, never the measuring.

## Done (in code)
- Ears (wav, transcript, music name, sound events, voice) run in a second thread while the picture is analysed (`analysis.parallel`, `pack.run_pipeline`).
  Test: tests/test_parallel_pipeline.py (parallel pack == serial pack). Found and fixed on the way: dominant colours changed run to run (k-means seed).
- Models cached between runs (actions/cache in worker.yml); one model load per run, never per reel.
- Frame analysis: every frame up to 6000 frames (200 s at 30 fps); longer files are sampled and the step is written in video_info.

## Next, in order of gain (each needs its own equality test)
1. Own GPU VM (rulebook 11): whisper, CLAP, tracking, rembg 5-10x. Biggest gain. Set ITCOD_RENDER_CONCURRENCY = cores/2 for Remotion.
2. Cache by content hash (sha1 of source): same file again = reuse transcript/voice/listen from Drive, skip models.
3. Batch many reels in one worker run (one model load); `bulk` jobs already do this.
4. Remotion: render in parallel chunks (concurrency flag), draft at 1/2 size, final at raw size.
5. faster-whisper batched pipeline (GPU only): faster, output can differ slightly -> use only after a 20-reel comparison shows word error equal.

## Never (quality cost)
- Smaller whisper model, fewer frames, lower final crf, hardware encoders (NVENC/QSV) for the final file, skipping QA or the clone check.
- Hardware encoders are fine for drafts only.

## How to measure
- Compare before/after on the same reel (workflow run time); a speed claim = seconds saved at equal output. Stage timers in the job note: not built yet.
