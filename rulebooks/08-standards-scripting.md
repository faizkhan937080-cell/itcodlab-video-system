# 08 scripting DNA standard (read before building or using scripting DNA)

Goal: write a NEW script that a fan of the creator cannot tell apart: same hook habit, structure, voice, rhythm, words.
Schema: `schemas/dna-scripting.schema.json` (v2). Numbers come from `script_metrics` in the pack, never from guessing.

## Transcript first (barrier)
- Coverage = last segment end / audio length. Under 0.9 the transcript is INCOMPLETE: structure, voice, lexicon, retention
  and cta may only be tagged `estimated`, and `transcript_basis.complete` must be false. Better: re-run the analysis.
- Hinglish: two passes are kept (auto language, often Devanagari phonetic; English pass). Quote from the clearer one.

## Measured (script_metrics): wpm (speaking and overall), speech ratio, pauses, sentence length mean/p90, questions/min,
numbers/min, second/first person per 100 words, fillers, repeated 3-word phrases, words before 3 s and 5 s, first 12 words.

## Judged by Claude (tag `judged`, each with a verbatim quote + time in `evidence`)
- Hook (first 3 s): kind = result-first, bold claim, curiosity gap, question, pattern interrupt, problem-agitate,
  story-open, contrarian; time to first value; open loop yes/no.
- Framework: name it (Hook-Value-CTA, PAS, AIDA, Hook-Story-Offer, listicle, tutorial steps, story arc, series episode).
- Structure beats with start/end seconds and share; devices per beat (rule of three, contrast, analogy, proof, demo).
- Voice: person (you/I/we), address terms (aap, dosto, bhai), register, formality, humour, energy, tone tags.
- Language: primary, script (roman/devanagari/mixed), code-switching rule (which words stay English), jargon domains.
- Lexicon: signature phrases (exact), fillers, power words. Retention: open loops, re-hooks at seconds, payoff time.
- CTA: type (comment-keyword DM, follow, save, share, link), exact ask, placement second, repeats, incentive.

## Precision rules
- Quote, do not paraphrase, signature phrases. Minimum 3 evidence quotes per candidate.
- Style is separated from topic: record how it is said, never the reference's facts as rules.
- 50 videos of one creator: build each video's DNA, then `./run corpus --type scripting` (03-dna). `signature` fields are
  cloned; `situational` fields follow the new topic. Under 10 videos = provisional, say so.
- Done = `./run dna-check --type scripting --file F --summary S` PASS, then gate 3 in chat.
- New script check: run the same metrics on the new script text; wpm, sentence length, question rate within 10% of targets.
