# Sanket PTT Web Client — Raspberry Pi

Browser-only, listen-only receiver for the existing Sanket PTT website. This is not a native MQTT radio client.

## Headless install (Raspberry Pi OS Lite 32-bit)

Run as the normal Pi login user, without `sudo`:

```bash
curl -fsSL https://vibhvesh.github.io/sanketptt/pi-webclient/install-lite.sh | bash
sudo reboot
```

The installer adds Xvfb (a virtual display, no desktop required), Chromium, ALSA utilities and a systemd service. It starts automatically at boot, joins the configured channel in listen-only mode, and restarts Chromium if it exits.

## Configure

Defaults:
- Web app: https://vibhvesh.github.io/sanketptt/
- Channel: `virtual`
- Device name: `PI-` plus the detected hardware MAC address
- Listen-only: `listen=1`; microphone and transmit controls remain disabled

Choose a channel during installation:

```bash
curl -fsSL https://vibhvesh.github.io/sanketptt/pi-webclient/install-lite.sh | SANKET_PTT_CHANNEL=master bash
```

Or edit `/etc/default/sanket-webptt`:

```bash
sudo nano /etc/default/sanket-webptt
sudo systemctl restart sanket-webptt
```

## Service diagnostics

```bash
sudo systemctl status sanket-webptt
sudo journalctl -u sanket-webptt -f
sudo systemctl restart sanket-webptt
```

## Audio

The launcher attempts to select the Raspberry Pi 3.5 mm analogue output with ALSA. The installer enables `dtparam=audio=on` in the boot config when that file exists. Connect powered speakers or an amplifier to the analogue jack. If needed, check mixer controls with `alsamixer`.

## Notes and limitations

- Intended for Raspberry Pi OS Lite (32-bit) on a Raspberry Pi with Chromium available from the configured OS repositories. It is not an installer for piCorePlayer.
- No desktop environment or monitor is required. Xvfb supplies an invisible display because Chromium's normal browser audio path is more reliable here than pure headless mode.
- Chromium still consumes significant RAM. A 512 MB Pi 3 may be memory-constrained; this has not been physically benchmarked on all Pi 3 variants.
- Internet access is required for GitHub Pages, the MQTT JavaScript library and the public WebSocket MQTT relay.
- This client uses the same hosted Sanket PTT web app and public relay list as the browser client; it does not install or host a relay server.
- Browser autoplay is enabled for the dedicated profile. Actual audio output depends on the Pi audio driver, selected output and connected speaker/amplifier.
