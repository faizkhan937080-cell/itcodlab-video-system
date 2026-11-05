# Commands Faiz can type in chat

| Say | Claude does |
|-----|-------------|
| analyze <link> video/audio/both, general or creator <name> | asks gate 1 Y/N, then writes the job to Drive |
| status | reads `jobs/state/*.json`, 1 line per job |
| approve / reject gate N (+ reason) | writes the approval file |
| (attach collages) | Claude reads them, writes DNA candidate files |
| render <idea> | writes scene plan, asks gate 4, then preview, 4K |

Flow: analyze -> gate 2 (collages ok?) -> DNA candidate -> gate 3 -> saved dna-vN.
Render: plan -> gate 4 -> preview -> gate 5 -> 4K -> gate 6 -> output/final-4k.
Worker must be running (Colab open). Nothing is deleted. No auto-publish.
