# 18 Platform copyright: Claude ALERTS, Faiz DECIDES (Faiz 2026-11-06 19:14)
Facts below are from YouTube's help page and press/vendor guides read 2026-11-06 (not legal advice). Re-check before relying.

## How Claude behaves
- Faiz's command decides what goes into a video. Claude never refuses or swaps an item because of a policy; it gives ONE alert line per job
  (item, platform, risk) and carries on when Faiz says so. Words he says = stored as `risk_accepted` {by, reason, date} in credits.json / library entry.
- Tools: `./run clients gate <co> <video> [--accept-risk "his words"]`, `./run library add ... --accept-risk "his words"`. Exit 1 = alert waiting for his word, not a wall.
- Still not built, by design (also useless): hiding copyrighted audio from detection (pitch/tempo/mirror tricks). Fingerprints survive them; it only risks the account.
- Alert text is short Hinglish in chat: what, where it can hit (video / channel), what he can do. Never a lecture, never repeated for the same item.

## YouTube (long videos, Shorts)
- Content ID = automatic match. Owner chooses block, monetise or only track. A claim hits the VIDEO, not the channel; no strike by itself.
- Claimed Shorts (any length) are blocked while the claim is active, but Shorts claims do not cause strikes.
- Fix a claim: mute, trim or replace the audio, or leave it. Dispute only with real rights: a bad dispute can lead to a removal request = strike.
- Strike = valid manual takedown by the owner (separate from Content ID). Strikes hit the channel. Owners now lean on manual takedowns for short clips.
- "No claim seen" is not "cleared": the owner may be set to track only, or a claim can come later. Big channels also have licences / permissions.
- No seconds-based safe harbour (no "5 s is fine"). Fair use is a defence decided case by case, not permission.

## Instagram Reels (vendor guide + Meta rules, check Meta's help page)
- Personal/creator accounts: in-app library music is for non-commercial posts. Business accounts: restricted to the Meta Sound Collection (cleared for commercial use).
- Trending audio: add it INSIDE the app when posting (licensed for in-app use). Baking the song into the exported file is the risky way. Faiz posts by hand (no auto-publish).
- Meta Rights Manager fingerprints audio; consequences run from muted audio to removed post to account limits. Cross-posting a Reel with its audio to YouTube/TikTok is not covered.
- Sponsored/ad posts need separately licensed music on any account.

## What lowers risk without tricks (offer these in the alert)
1. Original or CC0/PDM/BY audio from `assets/library` (credit BY items). 2. Trending audio added in-app. 3. Recreate the look in Remotion (effects need no file).
4. Meme clips/images: shortest use, own commentary or edit on top, own page rather than a client's. 5. Keep proof of licence (credits.json).
Client videos: the alert is shown once more at delivery; his word still decides.
