#!/usr/bin/env bash
set -euo pipefail
# Headless Sanket PTT web receiver for Raspberry Pi OS Lite (32-bit).
# Run as the logged-in Pi user, not with sudo:
# curl -fsSL https://vibhvesh.github.io/sanketptt/pi-webclient/install-lite.sh | bash

if [ "$(id -u)" -eq 0 ]; then
  echo "Run this installer as your normal Pi user, without sudo."
  exit 1
fi
PI_USER="$(id -un)"
PI_HOME="$HOME"
BASE_URL="${SANKET_PTT_URL:-https://vibhvesh.github.io/sanketptt/}"
CHANNEL="${SANKET_PTT_CHANNEL:-virtual}"

sudo apt-get update
sudo apt-get install -y xvfb xauth alsa-utils curl
if ! command -v chromium >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1; then
  sudo apt-get install -y chromium || sudo apt-get install -y chromium-browser
fi

# Enable the Pi 3 analogue audio hardware where the firmware config is present.
for cfg in /boot/firmware/config.txt /boot/config.txt; do
  if [ -f "$cfg" ] && ! grep -qE '^[[:space:]]*dtparam=audio=on' "$cfg"; then
    echo 'dtparam=audio=on' | sudo tee -a "$cfg" >/dev/null
  fi
done

sudo install -d -m 0755 /opt/sanket-webptt
curl -fsSL https://raw.githubusercontent.com/vibhvesh/sanketptt/main/pi-webclient/start-lite.sh -o /tmp/sanket-start-lite.sh
sudo install -m 0755 /tmp/sanket-start-lite.sh /opt/sanket-webptt/start-lite.sh
rm -f /tmp/sanket-start-lite.sh
sudo tee /etc/default/sanket-webptt >/dev/null <<EOF
SANKET_PTT_URL="$BASE_URL"
SANKET_PTT_CHANNEL="$CHANNEL"
EOF
sudo chmod 0644 /etc/default/sanket-webptt

sudo tee /etc/systemd/system/sanket-webptt.service >/dev/null <<EOF
[Unit]
Description=Sanket PTT headless listen-only web receiver
Wants=network-online.target
After=network-online.target sound.target

[Service]
Type=simple
User=$PI_USER
Environment=HOME=$PI_HOME
Environment=DISPLAY=:99
WorkingDirectory=$PI_HOME
ExecStart=/opt/sanket-webptt/start-lite.sh
Restart=always
RestartSec=5
TimeoutStopSec=10
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now sanket-webptt.service

echo
echo "Sanket PTT Lite receiver installed and enabled."
echo "URL: $BASE_URL"
echo "Channel: $CHANNEL"
echo "Device name: PI-<hardware-MAC>"
echo "Status: sudo systemctl status sanket-webptt"
echo "Logs:   sudo journalctl -u sanket-webptt -f"
echo "Reboot recommended if the analogue audio setting was added."
