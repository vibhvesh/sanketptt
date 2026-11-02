#!/usr/bin/env bash
# SuperPTT control room installer — Raspberry Pi 5 (Raspberry Pi OS Bookworm 64-bit).
#   curl -fsSL https://vibhvesh.github.io/sanketptt/superptt/pi/install.sh | bash
# Options (env): SUPERPTT_TUNNEL=quick|named|none  CF_TUNNEL_TOKEN=..  PUBLIC_URL=https://..
#                SUPERPTT_DIR=/opt/superptt  SUPERPTT_BASE=<download base url>  DRY_RUN=1
set -euo pipefail
BASE=${SUPERPTT_BASE:-https://vibhvesh.github.io/sanketptt/superptt/pi}
DIR=${SUPERPTT_DIR:-/opt/superptt}
TUN=${SUPERPTT_TUNNEL:-quick}
FILES="requirements.txt worker.py superptt/__init__.py superptt/__main__.py superptt/app.py superptt/config.py
superptt/ingest.py superptt/store.py superptt/stt.py superptt/cloud.py superptt/mixer.py superptt/retention.py
superptt/web.py superptt/console.html"
run() { if [ -n "${DRY_RUN:-}" ]; then echo "+ $*"; else eval "$@"; fi; }
SUDO=sudo; [ "$(id -u)" = 0 ] && SUDO=
USR=${SUDO_USER:-$(id -un)}
echo "== SuperPTT control room -> $DIR (user $USR, tunnel: $TUN)"

# 1. system packages
run "$SUDO apt-get update -qq"
run "$SUDO apt-get install -y -qq python3-venv python3-pip libportaudio2 alsa-utils curl ca-certificates"

# 2. fetch code (from this checkout if run locally, else from GitHub Pages)
SRC=""; [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "$(dirname "${BASH_SOURCE[0]}")/superptt/app.py" ] && SRC=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
run "$SUDO mkdir -p '$DIR/superptt' '$DIR/data' && $SUDO chown -R '$USR' '$DIR'"
for f in $FILES; do
  if [ -n "$SRC" ]; then run "cp '$SRC/$f' '$DIR/$f'"; else run "curl -fsSL '$BASE/$f' -o '$DIR/$f'"; fi
done

# 3. python venv + speech models (multilingual only)
run "python3 -m venv '$DIR/venv'"
run "'$DIR/venv/bin/pip' install -q -U pip"
run "'$DIR/venv/bin/pip' install -q -r '$DIR/requirements.txt'"
[ -f "$DIR/config.json" ] || run "printf '%s\n' '{\"data_dir\": \"$DIR/data\", \"whisper_model\": \"base\", \"quality_model\": \"small\", \"stt_workers\": 2, \"whisper_threads\": 2}' > '$DIR/config.json'"
echo "== downloading Whisper models (tiny/base/small, ~800 MB, one time)"
run "'$DIR/venv/bin/python' -c \"from faster_whisper import WhisperModel; [WhisperModel(m, compute_type='int8') for m in ('tiny','base','small')]\""

# 4. secrets template (never in git): cloud STT key
if [ ! -f /etc/superptt.env ]; then
  run "printf '%s\n' '# SuperPTT secrets. Uncomment and set, then: sudo systemctl restart superptt' '# ELEVENLABS_API_KEY=' '# OPENAI_API_KEY=' '# GOOGLE_API_KEY=' | $SUDO tee /etc/superptt.env >/dev/null"
  run "$SUDO chmod 600 /etc/superptt.env"
fi

# 5. control-room service
run "$SUDO tee /etc/systemd/system/superptt.service >/dev/null <<UNIT
[Unit]
Description=SuperPTT Control Room
After=network-online.target sound.target
Wants=network-online.target
[Service]
User=$USR
SupplementaryGroups=audio
WorkingDirectory=$DIR
EnvironmentFile=-/etc/superptt.env
ExecStart=$DIR/venv/bin/python -m superptt -c $DIR/config.json
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
UNIT"

# 6. Cloudflare Tunnel (outside access)
if [ "$TUN" != none ]; then
  ARCH=$(dpkg --print-architecture 2>/dev/null || echo arm64)
  run "curl -fsSL -o /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$ARCH.deb"
  run "$SUDO dpkg -i /tmp/cloudflared.deb"
  if [ "$TUN" = named ]; then
    : "${CF_TUNNEL_TOKEN:?set CF_TUNNEL_TOKEN for a named tunnel}"; : "${PUBLIC_URL:?set PUBLIC_URL}"
    run "printf 'CF_TUNNEL_TOKEN=%s\n' '$CF_TUNNEL_TOKEN' | $SUDO tee /etc/superptt-tunnel.env >/dev/null && $SUDO chmod 600 /etc/superptt-tunnel.env"
    run "'$DIR/venv/bin/python' -c \"import json;p='$DIR/config.json';c=json.load(open(p));c['public_url']='$PUBLIC_URL';json.dump(c,open(p,'w'),indent=2)\""
    EXEC='/usr/bin/cloudflared tunnel --no-autoupdate --metrics 127.0.0.1:20241 run --token ${CF_TUNNEL_TOKEN}'; ENVF='EnvironmentFile=/etc/superptt-tunnel.env'
  else
    EXEC='/usr/bin/cloudflared tunnel --no-autoupdate --metrics 127.0.0.1:20241 --url http://127.0.0.1:8090'; ENVF=''
  fi
  run "$SUDO tee /etc/systemd/system/superptt-tunnel.service >/dev/null <<UNIT
[Unit]
Description=SuperPTT Cloudflare Tunnel
After=network-online.target superptt.service
Wants=network-online.target
[Service]
$ENVF
ExecStart=$EXEC
Restart=always
RestartSec=5
DynamicUser=yes
[Install]
WantedBy=multi-user.target
UNIT"
fi

# 7. start
run "$SUDO systemctl daemon-reload"
run "$SUDO systemctl enable --now superptt"
[ "$TUN" != none ] && run "$SUDO systemctl enable --now superptt-tunnel"
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
cat <<MSG

== SuperPTT control room installed.
 1. On the Pi (or same Wi-Fi):  http://$(hostname).local:8090   (or http://$IP:8090)
    First open: set the admin PIN (6+ digits). Save the worker + directory tokens shown.
 2. Cloud STT key:  sudo nano /etc/superptt.env   (ELEVENLABS_API_KEY=...)  then  sudo systemctl restart superptt
 3. Outside access: the https://...trycloudflare.com URL appears in the console header
    (or: journalctl -u superptt | grep "public console")
 Logs: journalctl -u superptt -f    Update: re-run this command (config, data and PIN are kept).
MSG
