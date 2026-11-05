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

## Rule proposals (who decides what)
- Coding / technical rules (code style, tests, script structure, tool choice): Claude decides, writes it in the
  rulebook and lessons, tells Faiz in one line.
- Any other rule (money, publishing, folder layout, approvals, creators, what Claude may touch): Claude PROPOSES it on
  the "Rule Approvals" page (Approve / Not approve buttons). Written into a rulebook only after Approve.
- Proposal text: title, why (one line), exact rule text. Not approve = never written; record the no in memory.
