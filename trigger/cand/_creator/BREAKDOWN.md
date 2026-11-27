# sansser.ai (Sansser) - style breakdown (13 reels)
Clone rule: for screen-in-scene reels only the inner edited video is cloned, never monitor/room/desk.
Numbers = corpus targets (measured). Look/fonts/sfx = judged from collages. Music + sfx names: not identified yet.

## 1. Brand frame (every reel)
- Portrait 1080x1920 (screen reels: 4:5 / 16:9 inner crops). Wordmark "sansser /" top, footer handles heysansser / sansser / sansser.com (about 81% height).
- Captions: sans heavy font, ~3.5 words per caption, word-by-word blur-in, one key word highlighted (green box or accent colour), about 68% height.
- Format: Claude / AI tool news and tutorials, result-first. Background changes per reel (off-white dot grid, near-black green/orange HUD, cream, pastel) but layout stays clean, big type, one hero graphic per sentence.

## 2. Voice + script (targets)
- English, roman script, ~232 wpm speaking (200 overall), speech ratio 0.89, very expressive pitch, tone: punchy, confident, fast. Address: "you".
- Hook in first 0 s with an open loop: result/number/shock claim ("30 best Claude plugins", "this website cost me $1", "Holy shit, you are not ready for this").
- Body: list/countdown or problem - agitate - solve; "Then X" chain every ~2.8 s in lists; one pattern interrupt ("Take this.").
- CTA: comment-keyword ("PLUGINS", "RANK", "SEO", "SKILL", "CLAUDE", "stars", "speed") + sometimes follow. Some reels have no CTA (story/promo reels).
- Story reels (Potter, Valentina Noir): third-person storyteller, underdog -> reframe line, CTA only on screen.

## 3. Editing
- Pace: mostly ZERO or very few cuts; the action is inside one continuous canvas (cards slide, camera glides, items swap every 1-3 s). Cut reels: hard cuts + whip/dissolve, cuts follow voice phrases, not music beats (about 10% on beat).
- Motion: spring in/out (damping 16, stiffness 120), blur-to-sharp reveals, focused card sharp + neighbours blurred, progress bar/dots, counters climbing, 3D camera glide along glass bars, flip-board, typing in search bar.
- Components: kinetic text, banner, image, video clips (recipe.remotion_templates). B-roll share 0: all graphics, no stock footage.
- Colour: neutral, low saturation (median 0.15), flat UI looks, accents orange/green/pink per reel. No heavy grade.
- Safe zone: footer + banners sit low (inside strict bottom 35%), hook text sometimes in top 14%: copy as is.

## 4. Sound
- Loudness -17.2 LUFS, short-term max about -15.5, true peak about -0.5 dBTP. Voice dominant; music 15-37 LU below voice (nearly inaudible) in most reels, audible in story reels (3.7 LU).
- Tempo about 92-143 bpm (target 117.5). Music track NOT identified by fingerprint (no match: likely a licensed/library instrumental); mood = quiet modern electronic bed, mixed far below the voice.
- Sound events heard (CLAP listen, 7 reels; the 6 screen reels were not listened, score >= 0.4): glitch/digital stutter most common (51), splat/pop hits on card or item landing (15), bass drop at section starts (11), tick on counters (4), swoosh on whips (2), tape rewind (1). Rule: one soft digital glitch or splat on each new card/graphic, bass drop on the hook and big reveals, tick while numbers count, swoosh on whip cuts. Keep sfx short and under the voice.
- Frame note: DgLclCABIa3's bottom "Comment CLAUDE For The Full Guide" banner is part of the creator's frame (keep it).

## 5. Per-reel recipes (one line each, full DNA in dna/<reel>__<type>__v1.json)
- DfBQ1AgOC1S 58 s: "30 best Claude plugins" icon grid + star counter, card carousel, typed CTA.
- DfkbSDuB04k 33 s: one 3D scene, glowing emerald glass bars ranked +40.4K..+22.5K, camera glide, "Comment RANK".
- DfuYIvZA4Cd 34 s: Wi-Fi robbing you, one hero UI illustration per sentence, green karaoke captions.
- DgNJdLjB5Mq 52 s: nine fastest growing repos, white cards, sparklines, progress dots.
- DfzNJuKB5PA 39 s: free Claude SEO skill, mock-ups (search box, phone, VS Code), $2,500 invoice card.
- Dfi6kGuOemV 71 s: Claude Fable 5.2 explainer, four tabbed chapters, dissolves, no captions.
- DfMDZKfNER2 37 s: $1 website, kinetic headline, browser mock-up, green gradient key words, "Comment SKILL".
- Screen reels (inner video only): DgLclCABIa3 (3D stone busts, Potter story), DgNYH7ThrWb (dark green to cream, typed search captions), Df97YXth1Y6 (luxury editorial B&W + red), DeMkkKdsO2_ (Fairwind travel app promo), DfTxHLopj5m (orange-on-black Claude Code HUD, whip cuts). DfWN_TpptL7 13.7 s: silent landscape Claude Code "Motion Lab" promo, 10 scenes, 39.6 cuts/min, music-only 89 bpm, no voice, HUD frame with orange accent.

## 6. How to use
Give a topic -> pick the closest reel type above, copy brand frame + voice targets + hook/CTA pattern, build with Remotion (own components from library, no generic templates), voice at ~230 wpm, music low. Always run gate-check before "ready".
