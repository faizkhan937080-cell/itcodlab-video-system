# 02 scripting rules

## Two kinds of scripting DNA
- General: `dna/general/scripting/` for everyone.
- Creator: `creators/<creator-name>/dna/<job>__scripting__vN.json` for one creator only.
The user says which one to use. If not said, ask. Never mix them silently.

## How a script is made
1. Load ONE relevant DNA file from DNA_Index (never scan the whole folder).
2. Take the brief from the Jobs row.
3. Write the script in the DNA's structure: hook, flow, pacing, tone, language, CTA style.
4. Show it. Wait for approval (gate 4). Only then it goes to the scene plan.

## Creator DNA
- Built from the creator's videos (target: about 10).
- One DNA per video first. After enough videos a merged creator DNA is drafted, summarized once,
  and approved by the user before it is added to DNA_Index.

## Audio / scripting source
- Transcript and voice/music split come from scripts. Claude reads only the transcript summary.
- Hashtags lowercase. Brand rules: `config/brand.json`.

## Never
- Copy a creator's exact lines. Learn structure and style, write fresh text.
- Save a script to Drive or Sheet without approval.
