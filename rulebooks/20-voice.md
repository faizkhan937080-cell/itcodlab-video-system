# 20 voice: realistic + cloned, English + Hindi (read with 00-core, 09-standards-sound)
Code: scripts/voice_providers.py, `./run tts` (local), `./run voice-run` (worker), workflow .github/workflows/voice.yml.
## Defaults (Faiz 2026-11-07): FREE realistic only. Kokoro is NOT used unless the script says provider "kokoro".
- google: Cloud TTS Chirp 3 HD. English `en-IN-Chirp3-HD-Charon|Aoede`, Hindi `hi-IN-Chirp3-HD-<voice>` (30 voices, speaking_rate 0.25-2).
  Secret GOOGLE_TTS_KEY. Free 1M chars/month; past that it costs $30/1M -> blocked unless allow_paid.
- chatterbox: open MIT, 23 languages incl. Hindi (language_id "hi"), zero-shot clone from a 10-30 s clip. pip chatterbox-tts, GPU advised.
  Clip must be in the same language as the output; cfg_weight 0 for Hindi clones (less accent carry-over).
- auto order: google -> chatterbox. If neither can start, the error says exactly what is missing. No silent Kokoro fallback.
## Paid = only on Faiz's command
- elevenlabs (best clone, paid plan; free plan is non-commercial) and any use past a free quota: script must carry "allow_paid": true.
- Free trials of paid tools are also paid-on-command. Never switch to them on my own.
## Clone rules (hard)
- No clone without a signed release (person, AI synthesis, commercial, medium, territory, duration, revocation); Drive path in consent.doc.
- `./run voice register <id> --kind clone --consent-doc <path> ...` starts LOCKED; `./run voice verify <id>` only after Faiz says Y in chat.
- Scope needs ai_synthesis + commercial; expired consent refused (ConsentError). Never clone celebrities/politicians/anyone without own release.
- Deliver with an AI-voice disclosure option (India IT Rules 2026, EU Art. 50). Never strip provenance marks.
## Flow (no secrets in chat, ever)
- Keys live only in GitHub Secrets (GOOGLE_TTS_KEY, ELEVENLABS_API_KEY). Claude pushes trigger/voice/<name>.json; the workflow runs it, wav+json land in Drive output/voice/<name>/.
## Quality
- Speed 1.0-1.05, pauses 0.25-0.4 s, -14 LUFS after mixing (finish.normalize_loudness). Spell hard names phonetically for Google/Chatterbox.
## Status 2026-11-07
- Built + unit-tested with fake HTTP. NOT run live yet: needs GOOGLE_TTS_KEY secret; chatterbox first run on the worker. Hindi quality unjudged.
