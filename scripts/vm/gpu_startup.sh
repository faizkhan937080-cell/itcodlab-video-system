#!/bin/bash
# TURBO worker: GPU VM (label itcod-gpu). Normally STOPPED = no cost. Started only when Faiz says "speed up"; stops itself after 10 idle minutes.
# Paste as Startup script. Replace __TOKEN__ (runner token, 1 hour, one use). Same code as the normal worker.
set -e
[ -f /opt/itcod-runner/.done ] && exit 0
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl jq git unzip ffmpeg tesseract-ocr rclone clamav build-essential python3-venv python3-pip \
  libnss3 libatk-bridge2.0-0 libcups2 libgbm1 libxkbcommon0 libasound2t64 libchromaprint-tools libgl1 libglib2.0-0
# NVIDIA driver + CUDA libs for faster-whisper / torch
apt-get install -y -qq ubuntu-drivers-common && ubuntu-drivers autoinstall
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
  --token __TOKEN__ --name itcod-gpu --labels itcod-gpu --replace
./svc.sh install runner
./svc.sh start
# auto-stop: no job running for 10 minutes -> power off (the cost stops, the disk stays)
cat > /usr/local/bin/idle-stop.sh <<'EOS'
#!/bin/bash
if pgrep -f "Runner.Worker" >/dev/null; then touch /var/run/itcod-busy; exit 0; fi
[ -f /var/run/itcod-busy ] || touch /var/run/itcod-busy
if [ $(( $(date +%s) - $(stat -c %Y /var/run/itcod-busy) )) -gt 600 ]; then shutdown -h now; fi
EOS
chmod +x /usr/local/bin/idle-stop.sh
echo "* * * * * root /usr/local/bin/idle-stop.sh" > /etc/cron.d/itcod-idle-stop
touch .done
