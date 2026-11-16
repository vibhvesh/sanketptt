#!/usr/bin/env bash
set -euo pipefail
# Sanket PTT browser-only receiver for Raspberry Pi 3 (Raspberry Pi OS Desktop).
# Usage: curl -fsSL https://vibhvesh.github.io/sanketptt/pi-webclient/install.sh | bash
PI_USER="${SUDO_USER:-${USER}}"
PI_HOME="$(getent passwd "$PI_USER" | cut -d: -f6)"
[ -n "$PI_HOME" ] || { echo "Cannot determine home for $PI_USER"; exit 1; }
BASE_URL="${SANKET_PTT_URL:-https://vibhvesh.github.io/sanketptt/}"
CHANNEL="${SANKET_PTT_CHANNEL:-virtual}"
sudo apt-get update
sudo apt-get install -y alsa-utils curl
if ! command -v chromium-browser >/dev/null 2>&1 && ! command -v chromium >/dev/null 2>&1; then
  sudo apt-get install -y chromium || sudo apt-get install -y chromium-browser
fi
sudo install -d -m 0755 /opt/sanket-webptt
sudo tee /opt/sanket-webptt/start.sh >/dev/null <<'LAUNCH'
#!/usr/bin/env bash
set -euo pipefail
CFG=/etc/default/sanket-webptt
[ -r "$CFG" ] && . "$CFG"
MAC=""
for f in /sys/class/net/*/address; do
  iface="$(basename "$(dirname "$f")")"
  [ "$iface" = lo ] && continue
  candidate="$(cat "$f" 2>/dev/null || true)"
  case "$candidate" in ""|00:00:00:00:00:00) continue;; esac
  MAC="$candidate"; break
done
MAC="${MAC//:/}"
MAC="PI-${MAC^^}"
URL="${SANKET_PTT_URL:-https://vibhvesh.github.io/sanketptt/}"
CH="${SANKET_PTT_CHANNEL:-virtual}"
SEP='?'; [[ "$URL" == *\?* ]] && SEP='&'
TARGET="${URL}${SEP}ch=${CH}&listen=1&name=${MAC}"
# Raspberry Pi 3 analogue 3.5 mm output (legacy ALSA routing).
amixer cset numid=3 1 >/dev/null 2>&1 || true
BROWSER="$(command -v chromium-browser || command -v chromium || true)"
[ -n "$BROWSER" ] || { echo "Chromium not installed"; exit 1; }
PROFILE="$HOME/.config/sanket-webptt"; mkdir -p "$PROFILE"
while true; do
  "$BROWSER" --kiosk --app="$TARGET" --noerrdialogs --disable-infobars \
    --no-first-run --disable-session-crashed-bubble \
    --autoplay-policy=no-user-gesture-required \
    --disable-features=Translate --disable-translate \
    --user-data-dir="$PROFILE" --disk-cache-size=20000000 \
    --disable-pinch --overscroll-history-navigation=0
  sleep 3
done
LAUNCH
sudo chmod 0755 /opt/sanket-webptt/start.sh
sudo tee /etc/default/sanket-webptt >/dev/null <<EOF
SANKET_PTT_URL="$BASE_URL"
SANKET_PTT_CHANNEL="$CHANNEL"
EOF
sudo chmod 0644 /etc/default/sanket-webptt
mkdir -p "$PI_HOME/.config/autostart"
cat > "$PI_HOME/.config/autostart/sanket-webptt.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Sanket PTT Listen-only Receiver
Comment=Open Sanket PTT and play incoming audio
Exec=/opt/sanket-webptt/start.sh
X-GNOME-Autostart-enabled=true
EOF
sudo chown -R "$PI_USER":"$(id -gn "$PI_USER")" "$PI_HOME/.config/autostart"
echo
echo "Installed. Reboot into the Raspberry Pi desktop to start listening."
echo "PTT URL: $BASE_URL"
echo "Channel: $CHANNEL"
echo "Device name: PI-<hardware-MAC>"
echo "Change channel: sudo nano /etc/default/sanket-webptt"
