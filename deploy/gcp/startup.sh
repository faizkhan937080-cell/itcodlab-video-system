#!/bin/bash
# Google Cloud VM startup script (Ubuntu 22.04). Paste into VM > Edit > Automation > Startup script.
# Needs two VM metadata values (VM > Edit > Custom metadata), never in chat: rclone_token, github_pat (read-only).
# After a reboot or crash the worker comes back by itself (systemd). No PC needed.
set -e
MD=http://metadata.google.internal/computeMetadata/v1/instance/attributes
H='Metadata-Flavor: Google'
RCLONE_TOKEN=$(curl -s -H "$H" $MD/rclone_token)
GITHUB_PAT=$(curl -s -H "$H" $MD/github_pat)
if ! command -v ffmpeg >/dev/null; then
  apt-get update -qq
  apt-get install -y -qq git python3-pip ffmpeg tesseract-ocr rclone curl libnss3 libatk-bridge2.0-0 libcups2 libgbm1 libxkbcommon0 libasound2
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y -qq nodejs
fi
id itcod >/dev/null 2>&1 || useradd -m itcod
sudo -u itcod bash -c "
  mkdir -p ~/.config/rclone
  printf '[gdrive]\ntype = drive\nscope = drive\ntoken = %s\n' '$RCLONE_TOKEN' > ~/.config/rclone/rclone.conf
  [ -d ~/repo/.git ] || git clone https://x-access-token:$GITHUB_PAT@github.com/faizkhan937080-cell/itcodlab-video-system.git ~/repo
  cd ~/repo && git pull -q --ff-only && pip3 install -q -r requirements.txt && pip3 install -q -U yt-dlp
  (cd remotion && npm install --silent && npx remotion browser ensure)
"
cat > /etc/systemd/system/itcod-worker.service <<UNIT
[Unit]
Description=ITCODLAB video worker
After=network-online.target
[Service]
User=itcod
WorkingDirectory=/home/itcod/repo
Environment=ITCOD_RCLONE_REMOTE=gdrive,root_folder_id=1l9hOcWgtrDiYmqLMeLw9I8HjEW_BAJ1c:
ExecStart=/home/itcod/repo/run worker --loop --no-sheet --max-minutes 100000
Restart=always
RestartSec=20
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload && systemctl enable --now itcod-worker
