# Sanket Pi Listener 3.0.1 — install

## One-line upgrade on a Pi (keeps config + recordings)

```bash
curl -fsSL https://vibhvesh.github.io/sanketptt/pi/install.sh | bash
```

Then open `http://boondock.local:8080` (or your Pi’s `.local` / IP) → **CHANNELS**.

## From this zip (offline / USB)

1. Copy the zip to the Pi and unpack:
   ```bash
   unzip sanket-pi-listener-3.0.1.zip -d ~/sanket-pi-src
   cd ~/sanket-pi-src
   bash install.sh
   ```
2. Or point the installer at a local tree:
   ```bash
   SANKET_BASE="file://$HOME/sanket-pi-src" bash install.sh
   ```
   (Only if your install.sh supports file://; otherwise copy files into `~/sanket-pi` and re-run the online installer to refresh the service.)

## What’s new in 3.0.1

CHANNELS page: Edge-style multi-channel monitor — search/filter, listen toggles, live online/TX status, enable/disable all, listen-all + auto-discover grouped as control-room controls. Live feed and other tabs unchanged.

## Service

```bash
sudo systemctl restart sanket-pi   # name may be sanket-ptt / sanket depending on install
```
