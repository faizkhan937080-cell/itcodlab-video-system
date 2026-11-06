# 16 Pro editing - what the industry does, and what our system checks (scripts/qa.py)
Source: research of short-form (Reels/Shorts/TikTok) and pro post-production practice, Nov 2026. Numbers are defaults; DNA of the reference reel wins.

## Structure
- Hook inside the first 3 s (QA warns > 3.5 s without text/face/motion). Say the payoff or show the result first.
- Something changes at least every 5 s: new shot, zoom, text, B-roll, graphic (QA cadence check). Talking head: punch-in zoom every 3-6 s.
- B-roll must have a job (show what is said). Never filler. Library clips first, download only by name (15-security).
- End with one clear action (CTA / end card). No dead tail: last frame <= 0.5 s after the last word.
- Cover frame: auto-picked sharp, bright, face/text frame (scripts/cover.py), saved next to the final as `<name>_cover.jpg`.

## Cutting
- Cut on action or on a beat: `plan_edit.snap_to_beats` moves cuts <= 0.12 s to the music beat. Never shift speech.
- J/L cuts for talking scenes (audio leads/lags picture by ~0.25 s): scene props `audio_lead_s` (J) / `audio_tail_s` (L), applied by fx before render (not with speed change or muted clip).
- Dead air > 0.8 s inside speech = cut it (QA flags). Breaths and "um" go with it.
- 1-5 transitions per 30-60 s. Hard cut is the default; cross-transition only to mark a topic change.

## Picture
- Constant frame rate (VFR phone clips converted automatically by fx; output VFR = QA warning), 30 fps minimum; keep the source fps if higher.
- Output size = raw source size (4K in, 4K out). 9:16 min 1080x1920. H.264 + AAC, yuv420p, bt709 tags.
- No chained exports: always re-render from masters. Our intermediates (grade/fx) use crf 12.
- Grade per 13-grade.md; light denoise only for high-ISO clips (fx `denoise`).

## Text
- Captions on for speech: they must survive mute. Coverage >= 85% of speech (QA). Highlight the key word, 3-4 words per line.
- Stay in the safe zone (strict 14% top / 35% bottom / 6% sides). Never cover the face. Text auto-fits (lib/fit.ts).
- One idea per text card, readable >= 1 s per 3 words.

## Sound
- Loudness -14 LUFS +-1.5, true peak <= -1 dBTP (finish.py + QA). Voice clean chain on noisy voice. Music ducks under voice by ~10 dB.
- SFX on every hard transition / text pop, short, never louder than voice. Music beat drives cut grid when music is present.
- QA never hides a problem: it is listed even when the render succeeded.

## QA gate (every final render, report in job note)
black frames, frozen frames, dead air, cadence, hook time, caption coverage, loudness, true peak, CFR, safe-zone lint, effects/grade report.
Findings go in the report (`qa`) and the job note shows the warning count; Faiz is told only the count. QA never changes the video; hints say which plan number to change, then re-render (max 2 rounds).
