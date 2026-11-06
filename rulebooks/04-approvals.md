# 04 approval gates

Nothing moves to the next gate without a clear Y from the user in the Approvals tab or chat.
Never assume. Never auto-approve. Claude cannot approve for the user.

| Gate | What the user approves | Then |
|------|------------------------|------|
| 1 | Reference accepted: which video, mode (video/audio/both), folder (general or creator X) | Analysis runs |
| 2 | Analysis ready: collages + metrics look right | Claude may build DNA |
| 3 | DNA candidate | Saved as dna-vN and added to DNA_Index |
| 4 | Script or scene plan | Preview render |
| 5 | Preview render | 4K final render |
| 6 | 4K final | Saved to Drive `output/final-4k` |

## Rules
- On N: status REVISE, feedback in Notes, redo only the changed part.
- After 2 failed retries at any gate: FAILED, stop, tell the user.
- Lessons and creator-DNA merges also need approval before saving.
- Approvals are logged in the Approvals tab. Logs are never deleted.
- No publishing anywhere. Final files stay in Drive for the user to use.

## Batch approvals (Faiz rule, 2026-11-06)
- Similar actions = ONE ask. Several deletes, moves, uploads or renames of the same kind: list every item once
  (name + where), ask ONE Y/N. Never ask per item, never repeat the same kind of question.
- Different kinds of action (e.g. delete AND publish) = one ask per kind. Gates 1-6 stay separate asks.
- After a Y for a batch, do exactly that list. Anything extra = a new ask.
- Dev-phase scrap delete (00-core) already has a standing Y: do it, then report the list in one line.

## Rule proposals (who decides what) - IN CHAT, never a page
- Faiz listens to chat; he does not read pages or docs. Every approval question is asked IN CHAT, short Hinglish,
  one item per line, answer = Y or N. Never build an approval page/doc/tab.
- Coding / technical rules: Claude decides, writes them, tells Faiz in one line.
- Any other rule (money, publishing, folders, approvals, creators, what Claude may touch): ask in chat first
  (rule text + why, 2 lines). Write to a rulebook only after Y. After N: record the no in memory.
- Gate 2 is split per DNA type (approved 2026-11-06): scripting and sound may go to gate 3 once their data
  (transcript with coverage_ratio >= 0.9, OCR, audio metrics) is complete and checked. Editing waits until
  Claude has SEEN the collages.
- Audio mode (2026-11-06): no collages to judge, so gate 2 is skipped when transcript coverage >= 0.9, loudness is measured and the audit passes.
  Worker goes straight to AWAIT_CANDIDATE. Gate 3 (DNA candidate) stays Faiz's Y.
