#!/usr/bin/env bash
# Sanket PTT Pi listener installer (Raspberry Pi OS Bookworm 64-bit, Pi 5)
# curl -sSL https://raw.githubusercontent.com/vibhvesh/sanketptt/main/pi/install.sh | bash
set -euo pipefail
REPO_RAW="https://raw.githubusercontent.com/vibhvesh/sanketptt/main/pi"
APP_DIR="$HOME/sanket-pi"
RUN_USER="$(id -un)"
echo "==> Installing Sanket PTT Pi listener into $APP_DIR (user $RUN_USER)"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip espeak-ng libportaudio2 alsa-utils ffmpeg curl
sudo usermod -aG audio "$RUN_USER" || true
mkdir -p "$APP_DIR" "$HOME/sanket_clips"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
for f in sanket_pi.py requirements.txt config.yaml; do
  if [ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/$f" ] && [ "$SRC_DIR" != "$APP_DIR" ]; then src="$SRC_DIR/$f"; else src=""; fi
  if [ "$f" = config.yaml ] && [ -f "$APP_DIR/config.yaml" ]; then echo "    keeping existing config.yaml"; continue; fi
  if [ -n "$src" ]; then cp "$src" "$APP_DIR/$f"; else curl -fsSL "$REPO_RAW/$f" -o "$APP_DIR/$f"; fi
done
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip wheel
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
echo "==> Pre-downloading Whisper model (first run otherwise downloads it)"
MODEL=$(grep -E '^whisper_model:' "$APP_DIR/config.yaml" | awk '{print $2}'); MODEL=${MODEL:-base}
"$APP_DIR/venv/bin/python" -c "from faster_whisper import WhisperModel; WhisperModel('$MODEL', device='cpu', compute_type='int8')" || echo "    (model download failed; will retry at start)"
sudo tee /etc/systemd/system/sanket-pi.service >/dev/null <<UNIT
[Unit]
Description=Sanket PTT Pi listen-only client
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
Group=audio
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
Environment=XDG_RUNTIME_DIR=/run/user/$(id -u)
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/sanket_pi.py -c $APP_DIR/config.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now sanket-pi.service
sleep 3
systemctl --no-pager status sanket-pi.service | head -15 || true
echo
echo "Done. Edit $APP_DIR/config.yaml (channel, callsign...) then: sudo systemctl restart sanket-pi"
echo "Logs: journalctl -u sanket-pi -f    Clips: ~/sanket_clips"
