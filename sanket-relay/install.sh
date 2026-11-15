#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/sanket-relay"
CONFIG_DIR="/etc/sanket-relay"
DATA_DIR="/var/lib/sanket-relay"
SERVICE="sanket-relay"
BRANCH="${SANKET_RELAY_BRANCH:-sanket-core-v1}"
REPO="https://github.com/vibhvesh/sanketptt.git"

if [[ $EUID -ne 0 ]]; then echo "Run with: sudo bash install.sh"; exit 1; fi
if [[ "$(dpkg --print-architecture 2>/dev/null || true)" != "arm64" && "$(dpkg --print-architecture 2>/dev/null || true)" != "amd64" ]]; then
  echo "Unsupported architecture. Use 64-bit Raspberry Pi OS or Ubuntu."; exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip git ca-certificates

id sanket-relay >/dev/null 2>&1 || useradd --system --home "$DATA_DIR" --create-home --shell /usr/sbin/nologin sanket-relay
install -d -o root -g root -m 0755 "$APP_DIR" "$CONFIG_DIR"
install -d -o sanket-relay -g sanket-relay -m 0750 "$DATA_DIR"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git clone --depth 1 --branch "$BRANCH" "$REPO" "$TMP/repo"
install -m 0644 "$TMP/repo/sanket-relay/server.py" "$APP_DIR/server.py"
install -m 0644 "$TMP/repo/sanket-relay/requirements.txt" "$APP_DIR/requirements.txt"
chown -R root:root "$APP_DIR"

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [[ ! -f "$CONFIG_DIR/config.json" ]]; then
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  cat > "$CONFIG_DIR/config.json" <<EOF
{
  "host": "0.0.0.0",
  "port": 8765,
  "access_token": "$TOKEN",
  "max_clients_per_channel": 64,
  "max_message_bytes": 262144,
  "allowed_channels": []
}
EOF
  chmod 0600 "$CONFIG_DIR/config.json"
  echo
  echo "IMPORTANT: Save this Sanket Relay access token now:"
  echo "$TOKEN"
  echo "It is stored in $CONFIG_DIR/config.json (root-only)."
else
  echo "Existing relay configuration preserved."
fi

cat > "/etc/systemd/system/$SERVICE.service" <<EOF
[Unit]
Description=Sanket Relay Server
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=sanket-relay
Group=sanket-relay
WorkingDirectory=$APP_DIR
Environment=SANKET_RELAY_CONFIG=$CONFIG_DIR/config.json
Environment=PYTHONUNBUFFERED=1
ExecStart=$APP_DIR/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8765
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DATA_DIR
UMask=0077

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now "$SERVICE"
IP="$(hostname -I | awk '{print $1}')"
echo
echo "Sanket Relay installed as an independent service."
echo "Health: http://${IP:-PI-IP}:8765/health"
echo "WebSocket: ws://${IP:-PI-IP}:8765/ws?token=TOKEN&channel=CHANNEL"
echo "Status: systemctl status $SERVICE"
echo "Logs: journalctl -u $SERVICE -f"
echo "LAN pilot only: use VPN/TLS before exposing it outside your trusted network."
