#!/usr/bin/env bash
# Sanket PTT - Raspberry Pi listener, one-touch installer (safe to run again any time).
#   curl -fsSL https://vibhvesh.github.io/sanketptt/pi/install.sh | bash
# Installs: offline TTS (espeak-ng + piper voice), offline Whisper (faster-whisper),
# the receive-only listener + web management page, and a systemd service that starts on boot.
set -euo pipefail
BASE="${SANKET_BASE:-https://vibhvesh.github.io/sanketptt/pi}"
APP_DIR="$HOME/sanket-pi"
RUN_USER="$(id -un)"
PORT=8080
say(){ printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }
say "Sanket PTT Pi listener -> $APP_DIR (user $RUN_USER)"

say "System packages"
sudo apt-get update -y -qq
sudo apt-get install -y -qq python3-venv python3-pip espeak-ng alsa-utils ffmpeg curl avahi-daemon network-manager wireless-tools >/dev/null
sudo usermod -aG audio "$RUN_USER" || true
sudo systemctl enable --now avahi-daemon >/dev/null 2>&1 || true

say "App files"
mkdir -p "$APP_DIR/web" "$APP_DIR/voices" "$HOME/sanket_clips"
for f in sanket_pi.py web/index.html requirements.txt install.sh; do
  curl -fsSL "$BASE/$f?t=$(date +%s)" -o "$APP_DIR/$f.new" && mv "$APP_DIR/$f.new" "$APP_DIR/$f"
done
chmod +x "$APP_DIR/install.sh"

say "Python environment (faster-whisper, MQTT)"
[ -x "$APP_DIR/venv/bin/python" ] || python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -q --upgrade pip wheel
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
"$APP_DIR/venv/bin/pip" install -q piper-tts || echo "    (piper not available on this OS - espeak-ng will be used)"

say "Offline voice + Whisper model"
V="$APP_DIR/voices/en_US-lessac-medium.onnx"
if [ ! -s "$V" ]; then
  HF=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium
  curl -fsSL "$HF/en_US-lessac-medium.onnx" -o "$V" && curl -fsSL "$HF/en_US-lessac-medium.onnx.json" -o "$V.json" || { rm -f "$V"; echo "    (piper voice download skipped)"; }
fi
"$APP_DIR/venv/bin/python" -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')" >/dev/null 2>&1 \
  || echo "    (Whisper model will download on first start)"

say "Settings (all Sanket PTT channels added; existing settings kept)"
OLDCH=""; [ -f "$APP_DIR/config.yaml" ] && OLDCH=$(sed -n 's/^channel:[[:space:]]*\([A-Za-z0-9_-]*\).*/\1/p' "$APP_DIR/config.yaml")
SANKET_CONFIG="$APP_DIR/config.json" OLDCH="$OLDCH" VOICE="$V" "$APP_DIR/venv/bin/python" - <<'PY'
import os, sys, json; sys.path.insert(0, os.path.expanduser("~/sanket-pi"))
import sanket_pi as s
c = s.Config(os.environ["SANKET_CONFIG"])
ch = [x["name"] for x in c["channels"]]; o = s.clean_ch(os.environ.get("OLDCH"))
upd = {}
if o and o not in ch: upd["channels"] = c["channels"] + [{"name": o, "enabled": True}]
if os.path.exists(os.environ["VOICE"]) and not c["piper_model"]: upd["piper_model"] = os.environ["VOICE"]
if upd: c.update(upd)
print("    channels:", ", ".join(x["name"] for x in c["channels"]))
PY
PORT=$(python3 -c "import json;print(json.load(open('$APP_DIR/config.json')).get('web_port',8080))")

say "Allow the web page to join Wi-Fi networks"
echo "$RUN_USER ALL=(root) NOPASSWD: /usr/bin/nmcli" | sudo tee /etc/sudoers.d/sanket-pi >/dev/null
sudo chmod 440 /etc/sudoers.d/sanket-pi

say "Service (starts on boot)"
sudo tee /etc/systemd/system/sanket-pi.service >/dev/null <<UNIT
[Unit]
Description=Sanket PTT Pi listener (receive-only) + web management
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
Group=audio
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
Environment=PATH=$APP_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/sanket_pi.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable sanket-pi.service >/dev/null 2>&1
sudo systemctl restart sanket-pi.service
sleep 4
systemctl is-active --quiet sanket-pi && echo "    service running" || { echo "    service failed:"; sudo journalctl -u sanket-pi -n 20 --no-pager; }

H=$(hostname); IP=$(hostname -I 2>/dev/null | awk '{print $1}')
printf '\n\033[1;32m✔ Sanket PTT listener installed.\033[0m\n'
printf '  Open the management page:  \033[1mhttp://%s.local:%s\033[0m\n' "$H" "$PORT"
[ -n "$IP" ] && printf '                         or  http://%s:%s\n' "$IP" "$PORT"
echo "  Everything (channels, volume, voice, Whisper, email, Wi-Fi, logs, update) is managed there."
