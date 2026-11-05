# memory-rules
keys: memory forget summary long form toolbook recurring problems ai pitfalls tokens
- 2026-11-05 20:48Z 2026-11-06 Faiz: AI tools work from summaries and forget earlier talk and their own output. He wants everything stored in long form, never summarised, from the start of the work until now, updated from time to time.
- 2026-11-05 20:48Z Reading must cost almost no tokens: small sharded files (< 60 lines each), an auto-built index, grep via ./run mem find. If something grows to 8-10 pages it goes into code/files in a form that reads fast.
- 2026-11-05 20:48Z Development problems go into lessons. Problems that come back go into the toolbook (lessons/toolbook.md) with a fix recipe and a seen-counter. Likely future AI problems are listed in lessons/ai-pitfalls.md.
- 2026-11-05 20:48Z Storage: GitHub memory/ is the main place. If outside storage is a problem, keep it in code in the repo. Drive mirror only if Faiz asks.
- 2026-11-05 20:48Z Mechanism: CLAUDE.md router tells every session to run ./run mem brief first; .claude/settings.json SessionStart hook prints the brief (also after compaction); every decision/finding is added with ./run mem add.
