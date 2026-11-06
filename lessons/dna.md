# lessons: dna

Read before DNA building or merging. Add only after user approval. 3 lines per entry.

## Entry format
- Mistake:
- Cause:
- New rule:

## Entries
- Mistake: scripting numbers (wpm 128, 2 sentences, 30 s gaps) came from a degraded Hindi pass (loops, garbage after 80 s).
- Cause: compute() always used the auto pass; English pass (31 timed segments) was the good one.
- New rule: best_pass() uses the English pass when auto lost words; worker re-derives numbers from saved transcript.json. Always read `script_metrics.pass_used` and sanity-check wpm vs voice tempo before drafting.
