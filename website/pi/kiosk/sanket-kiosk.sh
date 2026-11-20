#!/usr/bin/env bash
# Sanket PTT kiosk: open the dashboard full screen on an attached display.
# Started by the desktop autostart (labwc / wayfire / LXDE) or by sanket-kiosk.service on Lite images.
APP_DIR="${APP_DIR:-$HOME/sanket-pi}"
CFG="$APP_DIR/config.json"
val(){ python3 -c "import json,sys;print(json.load(open('$CFG')).get('$1','$2'))" 2>/dev/null || echo "$2"; }
[ "$(val kiosk True)" = "False" ] && exit 0
PORT=$(val web_port 8080); BROWSER=$(val kiosk_browser chromium)
[ "$BROWSER" = "none" ] && exit 0
# no display connected -> nothing to do (headless Pis still serve the page)
if ls /sys/class/drm/*/status >/dev/null 2>&1 && ! grep -qx connected /sys/class/drm/*/status; then exit 0; fi
URL="http://localhost:$PORT/kiosk?kiosk=1"
for i in $(seq 1 90); do curl -fs -o /dev/null "http://localhost:$PORT/api/status" && break; sleep 2; done
# keep the screen on
command -v xset >/dev/null && [ -n "$DISPLAY" ] && { xset s off; xset -dpms; xset s noblank; } 2>/dev/null
command -v unclutter >/dev/null && [ -n "$DISPLAY" ] && (unclutter -idle 1 &) 2>/dev/null
CHROME=$(command -v chromium-browser || command -v chromium || true)
if [ "$BROWSER" = "surf" ] && command -v surf >/dev/null && [ -n "$DISPLAY" ]; then
  exec surf -F -K "$URL"
fi
[ -z "$CHROME" ] && { echo "no browser installed"; exit 1; }
PROFILE="$HOME/.config/sanket-kiosk"; mkdir -p "$PROFILE"
sed -i 's/"exited_cleanly":false/"exited_cleanly":true/; s/"exit_type":"Crashed"/"exit_type":"Normal"/' "$PROFILE/Default/Preferences" 2>/dev/null
while true; do   # always on: reopen if the browser closes or crashes
  "$CHROME" --kiosk --noerrdialogs --disable-infobars --no-first-run --disable-session-crashed-bubble \
    --disable-features=Translate --check-for-update-interval=31536000 --user-data-dir="$PROFILE" \
    --ozone-platform-hint=auto --disk-cache-size=10000000 --renderer-process-limit=2 "$URL"
  sleep 3
done
