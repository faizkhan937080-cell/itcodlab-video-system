# lessons: video

Read before video / motion / Remotion work. Add only after user approval. 3 lines per entry.

## Entry format
- Mistake:
- Cause:
- New rule:

## Entries
(none yet)
M: final mp4 voice came out 5.5 LU quieter than the -15 LUFS wav (Remotion mix) | C: Remotion audio path lowers level | R: after every render run finish.normalize_loudness (-14 LUFS); measure the mp4, never trust the input wav
R: render-local skipped loudness (mix -20.7 LUFS). Fixed: every render-local final runs finish.normalize_loudness -14. Check: ffprobe/ebur128 after render.
R: SVG path strings like '470 600 530 640' match the card-number regex (Luhn) -> security FAIL. Use commas in SVG paths.
M: first 'realistic voice' was Kokoro at speed 1.28 = robotic | C: free CPU model pushed fast, no cloud/clone path | R: voice_providers.py (kokoro/google/elevenlabs/chatterbox), speed 1.0-1.05, clones consent-gated (20-voice.md)
