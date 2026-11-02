# Sanket Edge – Raspberry Pi listener (v2)

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

## Update, restart, reboot

* **Update:** run the install command again, or use **System → Update** on the dashboard. Settings, recordings and voices are kept.
* **Restart the service:** `sudo systemctl restart sanket-pi` (or **System → Restart**). Status: `systemctl status sanket-pi`.
* **Logs:** `journalctl -u sanket-pi -f` (also under **System → Logs**).
* **Reboot:** `sudo reboot` – the service and the kiosk start again automatically.

## Bluetooth

**Audio → Bluetooth**: scan, pair, connect, disconnect and forget devices. A connected Bluetooth speaker can be chosen as
the output; a Bluetooth headset mic appears under **Inputs** as its own channel.

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

## RTL-SDR receiver

Plug an RTL2832U/R820T USB dongle into the Pi and add an **RTL-SDR receiver** input (Inputs → + Add input). It runs `rtl_fm` and feeds the audio through the same VOX → recording → offline transcription → announcement → dashboard path as the mic inputs. Works on Pi 3 and Pi 5.

- **Settings per input:** frequency (MHz), mode (NFM, FM, WBFM, AM), squelch (0 = off), tuner gain (`auto` or dB), sample rate, PPM correction, dongle index. You can also give a comma-separated **scan list** and a **dwell time**. The receiver stays on a frequency while a transmission is in progress.
- **Presets:** FM broadcast 88-108 (WBFM), airband 118-137 (AM), 2 m ham 144-146 (NFM), 70 cm ham 430-440 (NFM), marine VHF 156-162 (NFM).
- **Detect dongle** runs `rtl_test` and shows what it finds. The level meter shows the received audio level.
- The installer adds the `rtl-sdr` package, blacklists the `dvb_usb_rtl28xxu` TV driver and adds a udev rule. Unplug and replug the dongle (or reboot) after the first install.
- **Legal:** this is receive only. Listen only to public bands or bands you are licensed to listen to (broadcast, airband, amateur, marine). Do not monitor police, government or private communications. That is restricted under the Indian Wireless Telegraphy Act.

**Spectrum sweep / activity monitor.** Add an **RTL-SDR spectrum sweep** input to watch whole bands with `rtl_power`. It does no demodulation and records no audio or content. It only measures power per frequency bin.

- **Settings:** bands (`start-end` in MHz, comma separated, e.g. `430-440, 144-146`), bin size (kHz), sweep interval, alert threshold (dB above noise floor), allowlist of expected frequencies (MHz) with a tolerance, optional spoken alert, tuner gain, PPM, dongle index.
- A noise floor is learned for each bin. A bin that rises above floor + threshold and is not on the allowlist is logged as **suspicious activity** with time, frequency, peak dB and duration. With spoken alerts on, the Pi says e.g. "Unknown signal at 446.1 megahertz".
- The **Home** dashboard shows the latest sweep as bars with the floor and threshold lines, a short waterfall, and the activity log. **Export CSV** downloads the log (`/api/sweep.csv`).
- **One dongle, one mode.** A receiver and a sweep cannot use the same dongle index at the same time. Saving a second one is refused with a message. Disable the other input first or use a second dongle.
- The monitor logs signal presence only, for reporting to WPC monitoring. It does not intercept content.

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

User guide: [Sanket Edge User Guide (PDF)](../docs/Sanket_Edge_User_Guide.pdf) · https://vibhvesh.github.io/sanketptt/docs/

## Support

Akshat Singh · akshatsingh@canberravision.com
