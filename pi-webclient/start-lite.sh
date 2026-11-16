#!/usr/bin/env bash
set -euo pipefail
[ -r /etc/default/sanket-webptt ] && . /etc/default/sanket-webptt

URL="${SANKET_PTT_URL:-https://vibhvesh.github.io/sanketptt/}"
CHANNEL="${SANKET_PTT_CHANNEL:-virtual}"
MAC=""
for iface in wlan0 eth0; do
  file="/sys/class/net/$iface/address"
  if [ -r "$file" ]; then
    candidate="$(cat "$file")"
    case "$candidate" in ""|00:00:00:00:00:00) continue;; esac
    MAC="$candidate"
    break
  fi
done
if [ -z "$MAC" ]; then
  for file in /sys/class/net/*/address; do
    [ -r "$file" ] || continue
    iface="$(basename "$(dirname "$file")")"
    [ "$iface" = lo ] && continue
    candidate="$(cat "$file")"
    case "$candidate" in ""|00:00:00:00:00:00) continue;; esac
    MAC="$candidate"
    break
  done
fi
MAC="${MAC//:/}"
DEVICE="PI-${MAC^^}"
TARGET="${URL%/}/?listen=1&name=${DEVICE}&ch=${CHANNEL}"

# Route audio to the Raspberry Pi 3.5 mm analogue output when supported.
amixer cset numid=3 1 >/dev/null 2>&1 || true
BROWSER="$(command -v chromium || command -v chromium-browser || true)"
if [ -z "$BROWSER" ]; then
  echo "Chromium executable not found" >&2
  exit 1
fi

PROFILE="$HOME/.config/sanket-webptt"
mkdir -p "$PROFILE"
exec xvfb-run -a -s "-screen 0 800x600x16 -nolisten tcp" "$BROWSER" \
  --no-sandbox \
  --no-first-run \
  --noerrdialogs \
  --disable-infobars \
  --disable-dev-shm-usage \
  --disable-gpu \
  --disable-extensions \
  --disable-background-networking \
  --disable-sync \
  --disable-translate \
  --disable-features=Translate,MediaRouter \
  --autoplay-policy=no-user-gesture-required \
  --user-data-dir="$PROFILE" \
  --disk-cache-size=12000000 \
  --window-size=800,600 \
  --app="$TARGET"
