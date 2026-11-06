#!/bin/bash
# First-boot script of the Google Cloud VM that runs the worker as a GitHub self-hosted runner (private repo only).
# Paste into: Create instance > Advanced options > Management > Automation > Startup script. Replace __TOKEN__ (1 hour, one use).
set -e
[ -f /opt/itcod-runner/.done ] && exit 0
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl jq git unzip ffmpeg tesseract-ocr rclone clamav build-essential python3-venv python3-pip \
  libnss3 libatk-bridge2.0-0 libcups2 libgbm1 libxkbcommon0 libasound2t64 libchromaprint-tools libgl1 libglib2.0-0
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y -qq nodejs
id runner >/dev/null 2>&1 || useradd -m -s /bin/bash runner
echo "runner ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/runner
mkdir -p /opt/itcod-runner && cd /opt/itcod-runner
V=$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | jq -r .tag_name | sed 's/^v//')
curl -fsSL -o r.tgz "https://github.com/actions/runner/releases/download/v${V}/actions-runner-linux-x64-${V}.tar.gz"
tar xzf r.tgz
chown -R runner:runner /opt/itcod-runner
sudo -u runner ./config.sh --unattended --url https://github.com/faizkhan937080-cell/itcodlab-video-system \
  --token __TOKEN__ --name itcod-vm --labels itcod --replace
./svc.sh install runner
./svc.sh start
touch .done
