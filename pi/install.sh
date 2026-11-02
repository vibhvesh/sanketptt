#!/usr/bin/env bash
# Sanket PTT - Raspberry Pi listener, one-touch installer / upgrader (safe to run again any time).
#   curl -fsSL https://vibhvesh.github.io/sanketptt/pi/install.sh | bash
# Options (environment):  SANKET_KIOSK=0  skip the dashboard-on-display kiosk
#                         SANKET_KIOSK=1  force it (e.g. Pi 3 on a Lite image)
#                         SANKET_HW=pi3|pi5  override board detection
# Re-running upgrades the code and keeps config.json, recordings and voices.
set -euo pipefail
BASE="${SANKET_BASE:-https://vibhvesh.github.io/sanketptt/pi}"
APP_DIR="$HOME/sanket-pi"
RUN_USER="$(id -un)"
say(){ printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }
MODEL=$( (tr -d '\0' </proc/device-tree/model) 2>/dev/null || echo "unknown")
case "${SANKET_HW:-$MODEL}" in
  *"Pi 5"*|pi5) HW=pi5;; *"Pi 4"*|pi4) HW=pi4;; *"Pi 3"*|*"Zero 2"*|pi3) HW=pi3;; *) HW=other;;
esac
NEW=1; [ -f "$APP_DIR/config.json" ] && NEW=0
KIOSK="${SANKET_KIOSK:-auto}"
say "Sanket PTT Pi listener -> $APP_DIR (user $RUN_USER) on: $MODEL [$HW] $([ $NEW = 1 ] && echo new install || echo upgrade)"

say "System packages"
PKGS="python3-venv python3-pip espeak-ng alsa-utils ffmpeg curl avahi-daemon network-manager wireless-tools iw bluez pulseaudio-utils"
sudo apt-get update -y -qq
sudo apt-get install -y -qq $PKGS >/dev/null || sudo apt-get install -y -qq python3-venv python3-pip espeak-ng alsa-utils curl >/dev/null
sudo usermod -aG audio,bluetooth "$RUN_USER" 2>/dev/null || sudo usermod -aG audio "$RUN_USER" || true
sudo systemctl enable --now avahi-daemon >/dev/null 2>&1 || true
sudo systemctl enable --now bluetooth >/dev/null 2>&1 || true

say "RTL-SDR receiver support"
# rtl-sdr gives rtl_fm/rtl_test. The DVB-T TV driver grabs the dongle first, so blacklist it; the
# udev rule lets the service user open it without root. Both files are rewritten identically on re-run.
sudo apt-get install -y -qq rtl-sdr >/dev/null 2>&1 || echo "  (rtl-sdr package not installed; RTL-SDR input disabled)"
printf 'blacklist dvb_usb_rtl28xxu\nblacklist rtl2832\nblacklist rtl2830\n' | sudo tee /etc/modprobe.d/blacklist-rtlsdr-sanket.conf >/dev/null
printf 'SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0666"\nSUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", GROUP="plugdev", MODE="0666"\n' | sudo tee /etc/udev/rules.d/20-sanket-rtlsdr.rules >/dev/null
sudo usermod -aG plugdev "$RUN_USER" 2>/dev/null || true
sudo modprobe -r dvb_usb_rtl28xxu 2>/dev/null || true
sudo udevadm control --reload-rules 2>/dev/null && sudo udevadm trigger 2>/dev/null || true

say "App files"
mkdir -p "$APP_DIR/web" "$APP_DIR/voices" "$HOME/sanket_clips"
curl -fsSL "$BASE/files.txt?t=$(date +%s)" -o "$APP_DIR/files.txt"
grep -v '^#' "$APP_DIR/files.txt" | while read -r f; do
  [ -z "$f" ] && continue
  mkdir -p "$APP_DIR/$(dirname "$f")"
  curl -fsSL "$BASE/$f?t=$(date +%s)" -o "$APP_DIR/$f.new" && mv "$APP_DIR/$f.new" "$APP_DIR/$f"
done
chmod +x "$APP_DIR/install.sh" "$APP_DIR/kiosk/sanket-kiosk.sh"

say "Python environment (faster-whisper, MQTT)"
[ -x "$APP_DIR/venv/bin/python" ] || python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -q --upgrade pip wheel
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
V="$APP_DIR/voices/en_US-lessac-medium.onnx"
if [ "$HW" != pi3 ]; then
  "$APP_DIR/venv/bin/pip" install -q piper-tts || echo "    (piper not available - espeak-ng will be used)"
  if [ ! -s "$V" ]; then
    HF=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium
    curl -fsSL "$HF/en_US-lessac-medium.onnx" -o "$V" && curl -fsSL "$HF/en_US-lessac-medium.onnx.json" -o "$V.json" || { rm -f "$V"; echo "    (piper voice download skipped)"; }
  fi
else
  echo "    Pi 3: using light espeak-ng voice (piper skipped)"
fi

say "Settings (existing settings kept; board defaults only on a new install)"
OLDCH=""; [ -f "$APP_DIR/config.yaml" ] && OLDCH=$(sed -n 's/^channel:[[:space:]]*\([A-Za-z0-9_-]*\).*/\1/p' "$APP_DIR/config.yaml")
SANKET_CONFIG="$APP_DIR/config.json" OLDCH="$OLDCH" VOICE="$V" HW="$HW" NEW="$NEW" KIOSK="$KIOSK" "$APP_DIR/venv/bin/python" - <<'PY'
import os, sys; sys.path.insert(0, os.path.expanduser("~/sanket-pi"))
from sanket.config import Config
from sanket import hw
from sanket.util import clean_ch
c = Config(os.environ["SANKET_CONFIG"]); key = os.environ["HW"]
prof = dict(hw.PROFILES.get(key, hw.PROFILES["other"]))
if os.environ["KIOSK"] == "0": prof["kiosk"] = False
if os.environ["KIOSK"] == "1": prof["kiosk"] = True
if os.environ["NEW"] == "1":
    c.apply_profile(key, prof); print("    new install: defaults for", key, prof)
elif c.apply_profile(key, prof, only_missing=True):
    print("    upgrade: existing settings kept; new settings set for", key)
upd = {}
o = clean_ch(os.environ.get("OLDCH")); ch = [x["name"] for x in c["channels"]]
if o and o not in ch: upd["channels"] = c["channels"] + [{"name": o, "enabled": True}]
if os.path.exists(os.environ["VOICE"]) and not c["piper_model"]: upd["piper_model"] = os.environ["VOICE"]
if os.environ["KIOSK"] in ("0", "1"): upd["kiosk"] = os.environ["KIOSK"] == "1"
if upd: c.update(upd)
print("    channels:", ", ".join(x["name"] for x in c["channels"]))
print("    whisper:", c["whisper_model"], "| tts:", c["tts_engine"], "| sstv:", c["sstv"], "| kiosk:", c["kiosk"], c["kiosk_browser"])
open(os.path.expanduser("~/sanket-pi/.kiosk"), "w").write(("1" if c["kiosk"] else "0") + " " + c["kiosk_browser"] + "\n")
PY
read -r KON KBROWSER < "$APP_DIR/.kiosk"
PORT=$(python3 -c "import json;print(json.load(open('$APP_DIR/config.json')).get('web_port',8080))")
WM=$(python3 -c "import json;print(json.load(open('$APP_DIR/config.json')).get('whisper_model','base'))")
"$APP_DIR/venv/bin/python" -c "from faster_whisper import WhisperModel; WhisperModel('$WM', device='cpu', compute_type='int8')" >/dev/null 2>&1 \
  || echo "    (Whisper model will download on first start)"

say "Allow the web page to join Wi-Fi networks"
echo "$RUN_USER ALL=(root) NOPASSWD: /usr/bin/nmcli" | sudo tee /etc/sudoers.d/sanket-pi >/dev/null
sudo chmod 440 /etc/sudoers.d/sanket-pi

say "Always on: Wi-Fi power-save off, screen blanking off, hardware watchdog"
sudo mkdir -p /etc/NetworkManager/conf.d
printf '[connection]\nwifi.powersave = 2\n' | sudo tee /etc/NetworkManager/conf.d/sanket-wifi-powersave.conf >/dev/null
sudo iw dev wlan0 set power_save off 2>/dev/null || true
command -v raspi-config >/dev/null && sudo raspi-config nonint do_blanking 1 2>/dev/null || true
CMDLINE=/boot/firmware/cmdline.txt; [ -f $CMDLINE ] || CMDLINE=/boot/cmdline.txt
[ -f $CMDLINE ] && ! grep -q consoleblank=0 $CMDLINE && sudo sed -i '1 s/$/ consoleblank=0/' $CMDLINE || true
CONFIGTXT=/boot/firmware/config.txt; [ -f $CONFIGTXT ] || CONFIGTXT=/boot/config.txt
if [ -f $CONFIGTXT ] && ! grep -q '^dtparam=watchdog=on' $CONFIGTXT; then echo 'dtparam=watchdog=on' | sudo tee -a $CONFIGTXT >/dev/null; fi
if [ -e /dev/watchdog ] || [ -f $CONFIGTXT ]; then
  sudo mkdir -p /etc/systemd/system.conf.d
  printf '[Manager]\nRuntimeWatchdogSec=15\nRebootWatchdogSec=2min\n' | sudo tee /etc/systemd/system.conf.d/sanket-watchdog.conf >/dev/null
  echo "    hardware watchdog: systemd pets /dev/watchdog every 15 s (reboots if the Pi hangs)"
fi

say "Service (starts on boot, restarts on failure, software watchdog)"
sudo tee /etc/systemd/system/sanket-pi.service >/dev/null <<UNIT
[Unit]
Description=Sanket PTT Pi listener (receive-only) + web dashboard
After=network-online.target sound.target bluetooth.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$RUN_USER
Group=audio
SupplementaryGroups=bluetooth
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
Environment=XDG_RUNTIME_DIR=/run/user/$(id -u)
Environment=PATH=$APP_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/sanket_pi.py
Restart=always
RestartSec=3
NotifyAccess=main
WatchdogSec=120
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
UNIT
# keep the user's PipeWire running without a login so Bluetooth / PipeWire outputs work headless
sudo loginctl enable-linger "$RUN_USER" 2>/dev/null || true

say "Dashboard on an attached display (kiosk)"
if [ "$KIOSK" = 0 ] || [ "$KON" = 0 ] || [ "$KBROWSER" = none ]; then
  echo "    kiosk off"
  rm -f "$HOME/.config/autostart/sanket-kiosk.desktop"; sudo systemctl disable sanket-kiosk.service >/dev/null 2>&1 || true
elif [ -x /usr/bin/labwc ] || [ -x /usr/bin/wayfire ] || [ -x /usr/bin/startlxde-pi ] || [ -x /usr/bin/lxsession ]; then
  echo "    desktop found: autologin to desktop + autostart dashboard"
  if [ "$KBROWSER" = surf ]; then sudo apt-get install -y -qq surf unclutter >/dev/null 2>&1 || true
  else sudo apt-get install -y -qq chromium-browser >/dev/null 2>&1 || sudo apt-get install -y -qq chromium >/dev/null 2>&1 || true; fi
  command -v raspi-config >/dev/null && sudo raspi-config nonint do_boot_behaviour B4 2>/dev/null || true
  K="$APP_DIR/kiosk/sanket-kiosk.sh"
  mkdir -p "$HOME/.config/autostart" "$HOME/.config/labwc"
  printf '[Desktop Entry]\nType=Application\nName=Sanket PTT dashboard\nExec=%s\nX-GNOME-Autostart-enabled=true\n' "$K" > "$HOME/.config/autostart/sanket-kiosk.desktop"
  touch "$HOME/.config/labwc/autostart"; grep -q sanket-kiosk "$HOME/.config/labwc/autostart" || echo "$K &" >> "$HOME/.config/labwc/autostart"
  if [ -f "$HOME/.config/wayfire.ini" ] && ! grep -q sanket-kiosk "$HOME/.config/wayfire.ini"; then
    grep -q '^\[autostart\]' "$HOME/.config/wayfire.ini" || printf '\n[autostart]\n' >> "$HOME/.config/wayfire.ini"
    sed -i "/^\[autostart\]/a sanket = $K" "$HOME/.config/wayfire.ini"
  fi
elif [ "$HW" != pi3 ] || [ "$KIOSK" = 1 ]; then
  echo "    Lite image: installing cage + chromium kiosk on tty1 (only shows when a display is connected)"
  sudo apt-get install -y -qq cage chromium-browser >/dev/null 2>&1 || sudo apt-get install -y -qq cage chromium >/dev/null 2>&1 || true
  sudo tee /etc/systemd/system/sanket-kiosk.service >/dev/null <<UNIT
[Unit]
Description=Sanket PTT dashboard kiosk (attached display)
After=sanket-pi.service systemd-user-sessions.service
Wants=sanket-pi.service
ConditionPathExists=/dev/tty1

[Service]
User=$RUN_USER
PAMName=login
TTYPath=/dev/tty1
StandardInput=tty
Environment=APP_DIR=$APP_DIR
Environment=XDG_RUNTIME_DIR=/run/user/$(id -u)
ExecStartPre=/bin/sh -c 'grep -qx connected /sys/class/drm/*/status'
ExecStart=/usr/bin/cage -s -- $APP_DIR/kiosk/sanket-kiosk.sh
Restart=always
RestartSec=10

[Install]
WantedBy=graphical.target multi-user.target
UNIT
  sudo systemctl daemon-reload; sudo systemctl enable sanket-kiosk.service >/dev/null 2>&1 || true
else
  echo "    Pi 3 Lite: kiosk skipped (run with SANKET_KIOSK=1 to add it). The web page still works."
fi

sudo systemctl daemon-reload
sudo systemctl enable sanket-pi.service >/dev/null 2>&1
sudo systemctl restart sanket-pi.service
sleep 5
systemctl is-active --quiet sanket-pi && echo "    service running" || { echo "    service failed:"; sudo journalctl -u sanket-pi -n 20 --no-pager; }

H=$(hostname); IP=$(hostname -I 2>/dev/null | awk '{print $1}')
printf '\n\033[1;32m✔ Sanket PTT listener installed (%s).\033[0m\n' "$HW"
printf '  Open the dashboard:  \033[1mhttp://%s.local:%s\033[0m\n' "$H" "$PORT"
[ -n "$IP" ] && printf '                   or  http://%s:%s\n' "$IP" "$PORT"
echo "  Inputs, channels, audio/Bluetooth, voice, Whisper, SSTV, alerts, Wi-Fi, logs and updates are managed there."
echo "  A reboot applies the watchdog / kiosk / screen settings the first time."
