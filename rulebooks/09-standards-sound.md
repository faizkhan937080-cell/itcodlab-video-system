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

## SFX layer (reel 2026-11-06, `scripts/sfx.py`)
- Flow: plan_cues(plan) from exact scene times -> Openverse search (category sound_effect, license_type commercial, <=4 s) -> pick() -> audio_defs() into plan.audio.
- Only CC0 / PDM / CC BY (credit line saved). Never by-nc, by-sa, nd. No file for a cue kind = no sound, never invent one.
- whoosh leads the cut by 0.12 s, hit on the title frame, pop +3 frames, tick per checklist item; volume 0.35 under voice.
- Claude never listens: checks are numbers (duration, peak, LUFS) by scripts. Earshot (github Leonxlnx/earshot, CPU, sfx/forge/match) = candidate for fallback synthesis; licence not stated -> check before adopting.
- Run: `./run sfx --plan <plan.json> --assets-dir <dir>` (worker/network). Env OPENVERSE_TOKEN optional. Number gate: peak -35..-0.5 dB, <=4 s. Writes plan.audio + sfx_credits.json. `--dry-run` changes nothing.
## Ears: naming what is heard (`scripts/listen.py`, worker writes `<reel>/listen.json`)
- Music name: Instagram metadata -> AcoustID fingerprint (env ACOUSTID_KEY, free). Not found = `title: null` + note, never a guess; then pick the closest licensed track.
- Sound events: CLAP zero-shot labels (whoosh, pop, click ...) per 1 s window -> {label, t, end, score}; neighbours merged. Names map to library items by name/alias/tag.
- Demucs music stem is bad quality: used for measuring only, never as an asset. Real music/SFX come from `assets/library` (`./run resolve <reel>`, `./run library fetch`).
## Voice micro-level (`scripts/voice_dna.py`, worker writes `<reel>/voice.json`; summary key `voice`)
- Praat pitch (else librosa pyin), 10 ms steps. Units: semitones around the speaker's OWN median (no gender guess), dB energy.
- voice.json holds: global (pitch median/p10/p90 Hz, spread, expressiveness label, jitter/shimmer/HNR), every sentence (wpm, articulation wpm,
  pitch median/range, energy, ending rising|falling|flat, pause before/after), emphasised words (pitch+energy+length agree), gap bins,
  5 s timeline (60 s if >2 min) and per-minute rows.
- Labels (monotone <2 st, lively <4, very expressive; slow <110 wpm, medium <160, fast <200) are fixed thresholds on numbers, NEVER emotion guesses. Hindi/Hinglish: judge by the reel's own numbers.
- Sound/scripting DNA must quote: pitch spread, tempo (mean, min, max, CV), sentence-ending mix, gap bins, top emphasised words, hook-sentence delivery (first sentence rows).
- Cloning: our voice-over gets the same tempo and pause bins; check with the same script (`clone-report`).
