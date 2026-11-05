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
