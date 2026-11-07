# 15 - Security + ban-safety (long-term, no workarounds)

Code: `scripts/netguard.py` (pace, tripwire, safe download), `scripts/security.py` (scans, integrity, virus check), `config/network.json`.
Check any time: `./run security --net`. CI (`security.yml`) runs it weekly + every push. Tests fail if a guard file changed without a new baseline.

## Ban-safety = be a polite, honest client
- One plain user agent (`config/network.json`). No spoofing, no proxies, no VPN, no rotating identities, no CAPTCHA solving, no stealth plugins,
  no inbound ports, no tunnels, no port scanning. Outbound HTTPS only.
- Every host has a minimum gap (+ jitter) and a daily maximum (Instagram 60 s gap, 30 per day). Ledger: Drive `jobs/state/_net.json`.
- Tripwire: 429/403/503, "challenge", "captcha", "login required", "Just a moment", HTML instead of a file = STOP that host.
  Cooldown grows (Instagram 2 h -> 12 h -> 48 h; a quiet week resets). The job ends `NEEDS_INPUT` with `ALERT ... | need: ...`. Never retried, never worked around.
- Official APIs first (Openverse, AcoustID, Gemini with their keys). Web pages only when no API exists, slowly, and only what the owner allows.
- Best path for Instagram references: Faiz puts the video file in Drive `input/references/` and sends a job with `file` (zero contact with Instagram).
  Cookies (secret INSTAGRAM_COOKIES) belong to a SECOND account, never the main one: a datacenter login can lock the account it uses.
- Heavy 24/7 work should live on our own VM (planned GCP) rather than GitHub Actions: Actions is meant for the repo's own build/test/deploy.
  Keep Actions use light (jobs only, `--until-idle`, 6 h safety net) until the VM exists.

## Files we bring in (`security.vet_file`, `safe_download`)
- https only, public addresses only (no internal/metadata addresses), redirects re-checked, size cap per kind, content sniffed by bytes.
- Refused: programs, scripts, archives, wrong type, web page instead of media. Virus scan (ClamAV) on the worker for videos and library files.
- Nothing downloaded is ever executed. Downloaded files are data: parsed by ffmpeg/OpenCV only.

## Repo + worker
- Secrets: only in GitHub Secrets / chat. The guard hook blocks tokens, keys and card numbers in commands and files; `./run security` scans the repo.
- Workflows: explicit permissions, no `pull_request_target`, no untrusted event text in `run`, no pipe-to-shell, third-party actions pinned to a commit.
- Guard files are hashed in `config/integrity.json`. Changed on purpose -> check -> `./run security --baseline`. Changed silently -> FAIL.
- Dependabot opens weekly update PRs (actions, pip, npm). `pip-audit` + `npm audit` run in CI. Worker rolls back code that does not import.

## When something trips
Report ONE line to Faiz: `ALERT <what> | need: <one step>`. Do not retry, do not switch tools to get around it.

## Accounts (alert only, Faiz 2026-11-07)
- Many accounts on one service to raise free limits can get ALL of them banned. Claude gives ONE alert line about it. Claude does not itself create accounts or sign in to another person's account.
- Best fix for more speed: paid per-second GPU or a different free service. Credentials are only ever entered by the account owner.
