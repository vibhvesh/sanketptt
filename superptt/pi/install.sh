#!/usr/bin/env bash
# SuperPTT control room installer — Raspberry Pi 5 (Raspberry Pi OS Bookworm 64-bit).
#   curl -fsSL https://vibhvesh.github.io/sanketptt/superptt/pi/install.sh | bash
# Options (env): SUPERPTT_TUNNEL=quick|named|none  CF_TUNNEL_TOKEN=..  PUBLIC_URL=https://..
#                SUPERPTT_DIR=/opt/superptt  SUPERPTT_BASE=<download base url>  DRY_RUN=1
# Flags:  --private-broker   install a private Mosquitto broker on this Pi (WebSockets, per-user logins + ACLs),
#                            reachable from phones as wss:// through Cloudflare. Env: BROKER_USERS="unit1 unit2 ..."
#                            BROKER_HOSTNAME=mqtt.example.com (named tunnel; else a 2nd quick tunnel is started)
#                            BROKER_TLS_CERT=/path/fullchain.pem BROKER_TLS_KEY=/path/key.pem (optional LAN wss :8884)
#   curl -fsSL .../install.sh | bash -s -- --private-broker
set -euo pipefail
PRIV=""; for a in "$@"; do case "$a" in --private-broker) PRIV=1;; *) echo "unknown option $a"; exit 2;; esac; done
BASE=${SUPERPTT_BASE:-https://vibhvesh.github.io/sanketptt/superptt/pi}
DIR=${SUPERPTT_DIR:-/opt/superptt}
TUN=${SUPERPTT_TUNNEL:-quick}
FILES="requirements.txt worker.py superptt/__init__.py superptt/__main__.py superptt/app.py superptt/config.py
superptt/ingest.py superptt/store.py superptt/stt.py superptt/cloud.py superptt/mixer.py superptt/retention.py
superptt/web.py superptt/console.html superptt/e2e.py"
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

# 6b. private broker (optional): mosquitto, no anonymous access, per-user passwords + ACL on the SuperPTT prefix
if [ -n "$PRIV" ]; then
  echo "== private broker (mosquitto)"
  run "$SUDO apt-get install -y -qq mosquitto mosquitto-clients"
  PFX=$("$DIR/venv/bin/python" -c "import json;print(json.load(open('$DIR/config.json')).get('prefix','ptt-radio-66ab9178/'))" 2>/dev/null || echo ptt-radio-66ab9178/)
  CRED=/etc/mosquitto/superptt-credentials.txt
  if [ -z "${DRY_RUN:-}" ] && [ ! -f "$CRED" ]; then
    $SUDO touch /etc/mosquitto/superptt.passwd; $SUDO install -m 600 /dev/null "$CRED"
    for u in controlroom ${BROKER_USERS:-unit1 unit2 unit3}; do
      p=$(head -c 18 /dev/urandom | base64 | tr -d '/+=' | cut -c1-20)
      $SUDO mosquitto_passwd -b /etc/mosquitto/superptt.passwd "$u" "$p"
      echo "$u $p" | $SUDO tee -a "$CRED" >/dev/null
    done
  fi
  run "$SUDO chown mosquitto: /etc/mosquitto/superptt.passwd 2>/dev/null; $SUDO chmod 640 /etc/mosquitto/superptt.passwd"
  run "printf '%s\n' '# SuperPTT: every user may use the SuperPTT topic tree only' 'user controlroom' 'topic readwrite ${PFX}#' 'pattern readwrite ${PFX}#' | $SUDO tee /etc/mosquitto/superptt.acl >/dev/null"
  TLSL=""
  if [ -n "${BROKER_TLS_CERT:-}" ]; then TLSL="listener 8884
protocol websockets
certfile $BROKER_TLS_CERT
keyfile $BROKER_TLS_KEY"; fi
  run "$SUDO tee /etc/mosquitto/conf.d/superptt.conf >/dev/null <<CONF
per_listener_settings false
allow_anonymous false
password_file /etc/mosquitto/superptt.passwd
acl_file /etc/mosquitto/superptt.acl
# WebSockets on localhost only: Cloudflare terminates TLS (wss://) and forwards here
listener 9001 127.0.0.1
protocol websockets
$TLSL
CONF"
  run "$SUDO systemctl enable --now mosquitto && $SUDO systemctl restart mosquitto"
  if [ -z "${DRY_RUN:-}" ]; then
    CRP=$($SUDO awk '$1=="controlroom"{print $2}' "$CRED")
    "$DIR/venv/bin/python" - "$DIR/config.json" "$CRP" "${BROKER_HOSTNAME:-}" <<'PY'
import json,sys
p,pw,h=sys.argv[1:4];c=json.load(open(p))
c.update(broker_url="ws://127.0.0.1:9001/",broker_user="controlroom",broker_pass=pw,client_broker_url=("wss://"+h) if h else "")
json.dump(c,open(p,"w"),indent=2)
PY
    chmod 600 "$DIR/config.json"
  fi
  if [ -z "${BROKER_HOSTNAME:-}" ] && [ "$TUN" != none ]; then   # 2nd quick tunnel just for the broker
    run "$SUDO tee /etc/systemd/system/superptt-broker-tunnel.service >/dev/null <<UNIT
[Unit]
Description=SuperPTT private broker tunnel (wss)
After=network-online.target mosquitto.service
[Service]
ExecStart=/usr/bin/cloudflared tunnel --no-autoupdate --metrics 127.0.0.1:20242 --url http://127.0.0.1:9001
Restart=always
RestartSec=5
DynamicUser=yes
[Install]
WantedBy=multi-user.target
UNIT"
    run "$SUDO systemctl daemon-reload && $SUDO systemctl enable --now superptt-broker-tunnel"
  fi
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
 Private broker: ${PRIV:+logins in /etc/mosquitto/superptt-credentials.txt (sudo cat); phones' broker URL is shown in Console > Broker}${PRIV:-not installed (public brokers; add --private-broker)}
 Encryption: Console > Channel encryption > Add key > Invite / QR, scan with each phone.
 Logs: journalctl -u superptt -f    Update: re-run this command (config, data and PIN are kept).
MSG
