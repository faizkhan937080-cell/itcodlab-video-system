# 10 best-tool policy (Faiz: always the best tool, high accuracy)

Choose the best proven tool per job. Change a tool only with evidence (a test or a measured result), never by taste.

| Job | Tool (now) | Why |
|-----|-----------|-----|
| Motion graphics, text, banners, UI | Remotion (React, exact frames) | code-driven, 4K, versioned |
| Raw footage in the final | Remotion `OffthreadVideo` | exact frame extraction, no re-encode loss |
| Scene cuts | PySceneDetect-style histogram + flow (own) | measured on every frame pass |
| Transcript | faster-whisper `small`, two passes | Hinglish; `medium`/`large-v3` when a GPU is free |
| Loudness | pyloudnorm (BS.1770 / R128) | the broadcast standard |
| Tempo / beats | librosa | standard MIR toolkit |
| Final encode | h264 bt709 crf 16 (limits.json) | widest compatibility |
| Stem split (voice/music) | demucs, NOT installed yet | gap, see memory/decisions/roadmap |

## Rules
- Claude does not run the tools (06-fence). Scripts and the worker do.
- Remotion for client work needs the headcount check (00-core).
- A better tool appears? Test it on one reference, compare numbers, show Faiz in chat, then switch.
- No reference match claim without a measured check (`clone-report`). Say what is approximate (3D, particles, fonts).
