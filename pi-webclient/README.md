# Sanket PTT Web Client — Raspberry Pi 3

Browser-only, listen-only receiver. It opens the existing Sanket PTT web client in Chromium kiosk mode; it does not install a native radio/relay client.

## Install

Use Raspberry Pi OS Desktop (32-bit or 64-bit) with desktop auto-login enabled:

```bash
curl -fsSL https://vibhvesh.github.io/sanketptt/pi-webclient/install.sh | bash
sudo reboot
```

The Pi opens the Sanket PTT page after desktop login, joins the configured channel automatically, and plays received audio through the Pi 3.5 mm analogue jack. The display can be connected to a monitor or HDMI TV.

## Defaults and configuration

- URL: https://vibhvesh.github.io/sanketptt/
- Channel: `virtual`
- Client name: `PI-` followed by the Pi's hardware MAC address (colons removed)
- Listen-only: enabled; microphone access and transmit UI are disabled.
- Chromium is relaunched if it exits.

Edit `/etc/default/sanket-webptt`:

```bash
sudo nano /etc/default/sanket-webptt
```

Set `SANKET_PTT_URL` or `SANKET_PTT_CHANNEL`, then reboot or run `/opt/sanket-webptt/start.sh` from the desktop session.

## Audio

The launcher selects the Raspberry Pi 3.5 mm analogue output using ALSA's legacy output selector. Connect powered speakers or an amplifier to the headphone jack and adjust volume with:

```bash
alsamixer
```

## Important

- Requires a graphical Raspberry Pi OS Desktop session; this is intentionally not a headless native listener.
- The browser needs internet access to load GitHub Pages, the MQTT JavaScript library, and the configured public WebSocket MQTT relay.
- Chromium's autoplay policy is relaxed for this dedicated kiosk profile so incoming PTT audio can play without a repeated click.
- The PTT web app must be deployed with its `listen=1` support. Normal web-client behaviour remains unchanged when that parameter is absent.
