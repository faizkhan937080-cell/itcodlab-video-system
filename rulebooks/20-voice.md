# 20 voice: realistic + cloned (read with 00-core, 09-standards-sound)
Engines (script `provider`, or `voice_id` from config/voices.json). Code: scripts/voice_providers.py, `./run tts`.
- kokoro: free, CPU, robotic at speed >1.1. Default only for drafts/previews.
- google: Cloud TTS Chirp 3 HD, natural, stock voices. Secret GOOGLE_TTS_KEY. Free 1M chars/month, then $30/1M (pricing.json).
- elevenlabs: most natural + instant clone. Secret ELEVENLABS_API_KEY. Paid plan only for client work (free = non-commercial).
- chatterbox: open MIT clone from a 10-30 s clean clip. Runs on the worker GPU (pip chatterbox-tts), free.
## Clone rules (hard)
- No clone without a signed release (person, AI synthesis, commercial, medium, territory, duration, revocation). Drive path in consent.doc.
- `./run voice register <id> --kind clone --consent-doc <Drive path> ...` starts LOCKED. `./run voice verify <id>` only after Faiz says Y in chat.
- Scope must include ai_synthesis + commercial; expired consent is refused. Code raises ConsentError; do not bypass.
- Never clone celebrities, politicians, or anyone without their own release. Client staff need their own release too.
- Deliver with AI-voice disclosure option (India IT Rules 2026, EU Art. 50). Never strip provenance marks.
## Quality targets
- Speed 1.0-1.05 for natural pace; target -14 LUFS (finish.normalize_loudness); keep segment pauses 0.25-0.4 s.
- ElevenLabs/Google ignore the Kokoro lexicon: spell hard names phonetically in the text.
## Status 2026-11-07
- Built + unit-tested with fake HTTP. NOT yet run live: needs the two secrets (GitHub) and, for chatterbox, a GPU worker run.
- Free quota counter: costs/local/voice_usage.json (per machine). Cost rows carry chars + engine.
