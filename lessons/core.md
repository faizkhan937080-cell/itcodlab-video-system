# lessons: core

Read this before every task. Faiz allowed Claude to save lessons itself (compact, machine style, few tokens).
One line per entry: mistake | cause | rule. Past 60 lines: merge old entries, lose nothing.

## Entry format
M: mistake | C: cause | R: rule

## Entries
M: job id 'r1' rejected | C: schema needs 3-60 chars | R: ids like test-render-001
M: Colab drive.mount MessageError | C: Allow popup not completed, 2 tabs open | R: one tab, force_remount, click Allow
M: Colab Gemini says "I will run" but nothing runs | C: it needs Accept and run click | R: user clicks it, or Run all
M: GitHub token pasted in chat | C: user wanted it in a prompt | R: never repeat it, keep in runtime env only, revoke after setup
M: GitHub PAT value not visible again | C: shown once | R: Regenerate token, copy at once
M: Remotion browser download blocked in sandbox | C: network allowlist | R: set ITCOD_BROWSER to installed Chromium
M: Drive connector images unreadable | C: returned as base64 text | R: user attaches collages in chat
M: browser-agent Gemini stalls on confirm | C: asks before Generate/Delete | R: say "no confirmation needed" in prompt, never delete old tokens
M: Drive sync lag after file write | C: mounted Drive delay | R: wait ~60 s before reading state
M: Colab userdata unusable inside `!` shell | C: only the notebook kernel has it | R: copy secrets into os.environ in a cell before the worker cell
M: whisper crashed whole analysis (av version clash) | C: optional step not isolated | R: every optional step must catch errors and return available:false
