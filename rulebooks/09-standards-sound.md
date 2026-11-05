# 09 sound DNA standard (read before building or using sound DNA)

Schema: `schemas/dna-sound.schema.json` (v2). Loudness follows ITU-R BS.1770 / EBU R128 (LUFS), not plain dB.

## Measured by scripts (pack `audio`)
- Integrated loudness LUFS, loudness range LRA (LU), true peak dBTP (4x oversampled), short-term max LUFS.
- BPM, beat count, share of cuts within 80 ms of a beat, median offset, silence share, speech ratio.

## Reference levels (for judging, not for copying blindly)
- Broadcast EBU R128: -23 LUFS, true peak max -1 dBTP. US ATSC A/85: -24 LKFS. Streaming and social usually ~ -14 LUFS
  (podcasts ~ -16). Copy the REFERENCE's measured level; use these only to flag extremes.

## Judged by Claude (tag `judged`, evidence required)
- Mix: voice over music, ducking behaviour, music mood and genre, energy curve, SFX density per minute and types
  (whoosh, hit, riser, click), voice character and delivery (energy, pace, emphasis).
- Voice/music split by ear is only an estimate. Stem separation (demucs) is not running yet: say so.

## Precision rules
- Copy numbers from the pack. `./run dna-check --type sound` must PASS.
- Our output: re-measure with the same script, `./run clone-report`; loudness within 1 LU, bpm within 3%.
