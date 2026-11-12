# 23 - Permanent work protocol (Faiz approved 2026-11-11)
Born from: Pankaj Sir reel. Faded video shipped unseen; animation reference analysed from 3 stills.
Applies to EVERY video job, even when Faiz says "jaldi banao". Speed = smaller first sample, never skipped checks.

## 1. Look before sending
- Before any preview/final goes to Faiz: pull frames at start, middle, end + every big change (about every 6 s).
- Look at them myself (collage). Subject faint/cut, green left, empty area, text overlap = fix first, do not send.
- Numbers-only QA (cadence, caption %) is not enough. Build this frame check into the system (`./run` step), not memory.

## 2. Understand the reference fully before building
- Cut-less animation reel (one scene, near-white page): sample by content change (OCR/element diff), not whole-frame similarity.
- Write per element: when it enters, how (ease), how long it stays, position, caption style, footer/handles.
- Style record (DNA) must exist before the edit is planned. Never plan from 2-3 stills.

## 3. Test new tools on the REAL clip
- Any new effect (key, track, grade) is tried on 3-4 real frames first and looked at. Synthetic tests are extra, not proof.
- Check subject on the target background (white table on white page = disappears).

## 4. Small sample, then full
- Render a 5-6 s sample first. Faiz says Y, only then the full render.

## 5. Speed never skips checks
- "Jaldi" = start with the sample at once. Rules 1-4 still run.

## 6. Clone of a reference (Faiz 2026-11-12: "99% like the reference")
- Plan carries protocol.clone (reel, ref_video, shot map out->ref for EVERY second). Worker refuses Claude's own
  templates/text animations: only outside add-ons (remocn, ./run addon) + replicas of THIS reel + Google fonts.
- Script, caption language/case and screen structure follow the reference too, not only the look.
- After each render every shot is scored vs its reference moment; under limits clone.min_score it never reaches Faiz.
  Claude looks at collage_match.jpg (ref | ours) before anything is sent.

## Done check (before every send)
frames looked at? reference record complete? tool tested on real clip? sample approved? clone: match collage seen, all shots above the floor?
