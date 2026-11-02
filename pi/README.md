# Sanket PTT – Raspberry Pi listener

Receive-only Sanket PTT radio for a **Raspberry Pi 5 or Pi 3** (Raspberry Pi OS Bookworm/Trixie, Desktop or Lite).
It plays every transmission, transcribes it on the Pi (offline Whisper), and announces it aloud with offline TTS:
*"New message on <channel> from <name>"* followed by the transcript. It never transmits unless you turn on
forwarding for a local mic; otherwise the only thing it publishes is its online presence.

## Install / upgrade (one command)

```bash
curl -fsSL https://vibhvesh.github.io/sanketptt/pi/install.sh | bash
```

Run it again at any time to upgrade: code is replaced, `config.json`, recordings and voices are kept.
The installer detects the board and picks defaults on a new install:

| Board | Whisper | TTS | SSTV decode | Kiosk browser |
|---|---|---|---|---|
| Pi 5 / Pi 4 | base | piper | on | Chromium |
| Pi 3 / Zero 2 | tiny | espeak-ng | off | surf (Desktop) / skipped on Lite |

Options: `SANKET_KIOSK=0` (no dashboard on the display), `SANKET_KIOSK=1` (force it, e.g. Pi 3 Lite), `SANKET_HW=pi3|pi5`.
Example: `curl -fsSL https://vibhvesh.github.io/sanketptt/pi/install.sh | SANKET_KIOSK=0 bash`

### Always on
* `sanket-pi` systemd service: starts on boot, `Restart=always`, no start limit, software watchdog (`WatchdogSec=120`).
* Hardware watchdog: `dtparam=watchdog=on` + systemd `RuntimeWatchdogSec=15` (the Pi reboots if it hangs).
* Wi-Fi power-save off (NetworkManager), screen blanking off, the relay reconnects forever (and the client is rebuilt if it stays down for 60 s).
* Kiosk: with a display attached the Pi auto-logs in and opens the dashboard full screen (`/kiosk`); the browser is reopened if it closes.
  On Lite images a `cage` + Chromium kiosk runs on tty1 only when a display is connected. Headless Pis just serve the web page.

## Web page

Open **http://&lt;pi-hostname&gt;.local:8080** from any phone or PC on the same network.

* **Home**: configuration (device, channels, audio in/out, broker, model), live CPU / temperature / RAM / disk / uptime / network,
  graphs of messages received / transcribed / announced / SSTV and audio in/out levels, input level meters, latest messages.
* **Live**: message feed with transcripts, alerts, SSTV pictures and playback; who is online / talking.
* **Inputs**: every input is a channel — PTT web-relay links (editable https link `…/?ch=name` and broker), the Pi's mic,
  USB mics / sound cards (as many as are attached, one channel each), Bluetooth mics. Local inputs use VOX (adjustable threshold,
  hang time, gain) and go through the same transcribe → announce → feed pipeline. Optional forward to the relay (off by default).
* **Channels**: main relay channels, listen to all, auto-add, device name, broker.
* **Audio**: output device (default ALSA/PipeWire, 3.5 mm jack, HDMI, USB, Bluetooth speaker), volume, Bluetooth scan / pair /
  connect / disconnect / forget, TTS, Whisper, SSTV.
* **Alerts**: keywords and email. **System**: Wi-Fi, restart, update, port, settings PIN (login), retention, kiosk, logs.

## Code layout

```
sanket_pi.py          entry point (systemd runs this)
sanket/
  config.py           settings + defaults, backward-compatible config.json
  auth.py             settings PIN + login sessions
  storage.py          clips, metadata, feed, retention
  audio_io.py         output/input device lists, playback, capture commands
  bluetooth.py        bluetoothctl wrapper
  inputs/registry.py  plug-in input registry + manager (add a type = new module with @register)
  inputs/local_audio.py  Pi mic / USB / Bluetooth mic inputs (arecord / parec + VOX)
  inputs/relay.py     PTT web-relay inputs        inputs/vox.py  VOX segmenter   inputs/fake.py  test input
  mqtt_relay.py       Sanket PTT relay protocol (MQTT/WSS), auto-reconnect
  pipeline.py         save → SSTV → transcribe → announce → email → optional forward
  transcribe.py       faster-whisper          announce.py  TTS + speaker queue
  sstv.py             SSTV detect + decode (VIS, sync lock, slant correction)
  sysmon.py           CPU/temp/RAM/disk/net   metrics.py   time series for the graphs
  alerts.py  hw.py  sdnotify.py  web.py  app.py
web/index.html        dashboard + management page (no frameworks, canvas charts)
kiosk/sanket-kiosk.sh full-screen dashboard launcher
tests/test_box.py     off-Pi tests
```

Settings are in `~/sanket-pi/config.json`, recordings in `~/sanket_clips`. The Pi uses the same relay and topics as the web app:
`ptt-radio-66ab9178/<channel>/{presence/<id>,floor,audio,sstv}` with 12 kHz Int16 PCM audio.
