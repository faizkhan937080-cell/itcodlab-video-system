# One-time setup so everything runs without your PC (about 10 minutes, on a Windows PC, once)

Secrets never go in chat. You paste them only into GitHub.

1. On the PC open rclone.org/downloads, click "Windows Intel/AMD - 64 Bit", unzip the file.
2. Open the unzipped folder, click its address bar, type `cmd`, press Enter (a black window opens).
3. Type `rclone authorize "drive"` and press Enter. A browser opens: log in with your Google account, click Allow.
   Back in the black window, copy everything between `Paste the following into your remote machine --->` and `<---End paste`.
4. GitHub: repo itcodlab-video-system > Settings > Secrets and variables > Actions > New repository secret.
   Name: `RCLONE_TOKEN`. Secret: paste the copied text. Click Add secret.
5. Same Settings > Actions > General > Workflow permissions > select "Read and write permissions" > Save.
6. Tell Claude "done". Claude starts a test job; you check nothing else.

Optional later: secret `INSTAGRAM_COOKIES` (cookies.txt text) if Instagram blocks the server.
Google Cloud VM (needs a card): docs in rulebooks/11-hosting.md and deploy/gcp/startup.sh.

## Backup (monthly + on demand)
- Workflow `backup`: every 1st of the month 02:23 UTC, or push `trigger/backup.txt`. Writes `backups/itcodlab-video-system-<date>.bundle` in Drive. Old ones stay.
- Restore after a disaster: download the newest .bundle from Drive, then `git clone itcodlab-video-system-<date>.bundle itcodlab-video-system`, push it to a new GitHub repo, re-add secret RCLONE_TOKEN.
- Drive files and the Sheet already live in Drive, so only the repo needs this.
