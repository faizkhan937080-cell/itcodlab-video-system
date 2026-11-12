#!/usr/bin/env bash
# Background machine setup (2026-11-12 speed-up): system tools, then the virus scanner, while Python/Node
# packages install in the foreground. apt allows one install at a time, so both run here in order.
# Flags: /tmp/itcod/tools.done (ok|fail), /tmp/itcod/clam.installing removed when the scanner is ready (or given up).
mkdir -p /tmp/itcod work
touch /tmp/itcod/clam.installing
_t=$(date +%s)
APT="-o Acquire::Retries=3 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20"
PKGS="ffmpeg tesseract-ocr rclone libnss3 libatk-bridge2.0-0 libcups2 libgbm1 libxkbcommon0 libasound2t64 libchromaprint-tools"
for i in 1 2 3; do
  timeout 180 sudo apt-get -qq $APT install -y $PKGS > /dev/null && break
  timeout 240 sudo apt-get -qq $APT update || true
  timeout 240 sudo apt-get -qq $APT install -y $PKGS > /dev/null && break || echo "apt try $i failed"
done
if ! command -v rclone >/dev/null; then
  curl -fsSL -o /tmp/rclone.zip https://downloads.rclone.org/rclone-current-linux-amd64.zip
  unzip -q -o /tmp/rclone.zip -d /tmp/rclone-dl && sudo install -m 0755 /tmp/rclone-dl/rclone-*-linux-amd64/rclone /usr/local/bin/rclone || true
fi
ok=ok; for t in ffmpeg rclone tesseract; do command -v $t >/dev/null || { echo "MISSING TOOL: $t"; ok=fail; }; done
echo "system_tools $(( $(date +%s) - _t ))" >> work/setup_times.txt
echo $ok > /tmp/itcod/tools.done
_t=$(date +%s)
timeout 300 sudo apt-get -qq install -y clamav > /dev/null && {
  sudo systemctl stop clamav-freshclam || true
  timeout 300 sudo freshclam --quiet || echo "virus database not updated; scans use the packaged one"
}
echo "virus_scanner $(( $(date +%s) - _t ))" >> work/setup_times.txt
rm -f /tmp/itcod/clam.installing
