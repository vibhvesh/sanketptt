# Sanket PTT – Raspberry Pi listener

Receive-only Sanket PTT radio for a Raspberry Pi 5 (Raspberry Pi OS Bookworm, 64-bit).
It plays every transmission, transcribes it on the Pi (offline Whisper), and announces it aloud
with offline TTS: *"New message on <channel> from <name>"* followed by the transcript.
It never transmits; the only thing it publishes is its online presence.

## Install (one command)

```bash
curl -fsSL https://vibhvesh.github.io/sanketptt/pi/install.sh | bash
```

You can run it again at any time. It keeps your settings, adds all known Sanket PTT channels,
sets up the `sanket-pi` service so it starts on boot, and prints the page address.

## Manage it from the web page

Open **http://&lt;pi-hostname&gt;.local:8080** (or http://&lt;pi-ip&gt;:8080) from any phone or PC on the same network.

* **Live**: the incoming message feed (transcripts, alerts, SSTV pictures, playback), the channel list with who is online and talking, link status, a test announcement button and volume.
* **Channels**: add, remove, enable or disable channels, enable all, add all known channels, listen to every active channel, auto-add discovered channels, device name, relay (broker).
* **Audio & Voice**: output device, volume, play received audio, beep, announcements on or off, say the sender, read the transcript, announcement text, voice engine (piper or espeak-ng) and voice, speaking speed, transcription on or off, Whisper model, language, SSTV on or off.
* **Alerts**: alert keywords, alert email (keyword alerts or every message, SMTP settings, test email).
* **System**: Wi-Fi status and joining a network, restart service, update app, web port, optional settings PIN, how long recordings are kept, logs.

Settings are stored in `~/sanket-pi/config.json`. Recordings go to `~/sanket_clips`.

The Pi uses the same relay and topics as the web app: `ptt-radio-66ab9178/<channel>/{presence/<id>,floor,audio,sstv}`,
with 12 kHz Int16 PCM audio. A channel name is the same as `?ch=<channel>` in the radio link.
