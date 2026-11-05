# NEW: no-PC setup is in docs/HOSTING.md (GitHub Actions). The Colab steps below are only a backup.

# Setup (free path: Colab, no card)

One-time, by Faiz himself (secrets never go in chat):
1. GitHub: Settings > Developer settings > Fine-grained tokens > new token.
   Only repo `itcodlab-video-system`, permission Contents = Read-only. Copy it.
2. Open `colab/itcodlab_worker.ipynb` from GitHub in Colab (File > Open > GitHub tab).
3. Left side key icon (Secrets): add `GITHUB_PAT` = the token, Notebook access ON.
4. Drive: folder ITCODLAB-VIDEO must be in My Drive (shared folder: Add shortcut to My Drive).
5. Runtime > Run all. Allow Drive and Google login popups.
6. Leave the tab open while jobs run. Free Colab stops after ~12 h or when idle; just Run all again.

Later (needs a card): GCP VM e2-standard-8, Ubuntu 22.04, asia-south1, 200 GB.
Same code: set `ITCOD_RCLONE_REMOTE`, clone repo, `./run worker --loop`.
Cookies for private Instagram links: put cookies.txt on the worker, set `ITCOD_COOKIES`.
