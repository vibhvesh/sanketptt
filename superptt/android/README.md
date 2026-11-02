# SuperPTT control room on Android (Termux): Vivo X300 as a backup control room

The phone runs the same control room as the Pi: MQTT ingest, recording, transcripts, the web console on :8090,
retention, channel encryption and a Cloudflare quick tunnel. It runs inside Termux only. **Nothing is erased or
rooted, and no Android settings change except the battery and autostart permissions you set yourself.**

## One-line install (in Termux)
```sh
curl -fsSL https://vibhvesh.github.io/sanketptt/superptt/android/install-termux.sh | bash
```
It takes 5–40 minutes, depending on which speech engine builds. Re-run it to update; config, data and the PIN are kept.

## Steps on the Vivo X300 (Android 16, OriginOS/Funtouch)
1. **Install Termux from F-Droid** (https://f-droid.org/packages/com.termux/) **or GitHub**
   (https://github.com/termux/termux-app/releases, `arm64-v8a` APK). Do **not** use the Play Store build, which is outdated
   and incompatible. Allow "Install unknown apps" for your browser or F-Droid when Android asks.
2. Install **Termux:Boot** and **Termux:API** from the *same* source as Termux (F-Droid or GitHub; mixed sources fail
   with signature errors). Open Termux:Boot once so Android registers it.
3. Open Termux, run `termux-setup-storage` (optional), then run the one-line install above.
4. **Battery and autostart (needed: vivo kills background apps aggressively):**
   - Settings › Apps › Termux › Battery (or *Power consumption*) › **Background power consumption: Allow**
     (also "Allow high background power consumption"). Do the same for **Termux:Boot** and **Termux:API**.
   - Settings › Battery › More settings / *Background power management*: turn **off optimisation** for Termux.
   - Settings › Apps › **Autostart** (on some builds: i Manager › App manager › Autostart manager): **allow Termux and Termux:Boot**.
   - In Recents, pull down on Termux (or tap the lock icon) to **lock** it so "clear all" doesn't kill it.
   - Keep the Termux notification; `superptt-start` holds a wake lock (`termux-wake-lock`).
5. Open `http://127.0.0.1:8090` in the phone browser and set the admin PIN. The public `https://…trycloudflare.com`
   URL is printed by `superptt-start`, shown by `superptt-url`, and shown in the console header.

## Commands
| | |
|---|---|
| `superptt-start` | start control room + quick tunnel in the background (wake lock on), print the URL |
| `superptt-stop`  | stop both, release the wake lock |
| `superptt-url`   | print the current public URL (a quick-tunnel URL changes on every start) |
| logs | `~/superptt/logs/superptt.log`, `tunnel.log`, `boot.log` |

Auto-start after reboot: `~/.termux/boot/superptt` (Termux:Boot) waits 20 s, then runs `superptt-start`.

## Layout (same as the Pi, with Termux paths)
| Pi | Android |
|---|---|
| `/opt/superptt/{config.json,data,venv,superptt}` | `~/superptt/{config.json,data,venv,superptt}` |
| `/etc/superptt.env` (600) | `~/.superptt.env` (600), loaded by `superptt-start` |
| systemd `superptt`, `superptt-tunnel` | `superptt-start` / `superptt-stop` + Termux:Boot |
| `journalctl -u superptt` | `~/superptt/logs/` |

Cloud key: `nano ~/.superptt.env`, set `ELEVENLABS_API_KEY=...`, then run `superptt-stop; superptt-start`. Never commit this file.

## Speech-to-text engine (picked automatically, `SUPERPTT_STT=auto`)
1. **faster-whisper**, same as the Pi. It uses Termux's `python-ctranslate2` and `python-onnxruntime` packages. The installer
   pip-builds `tokenizers` (Rust) and `av` (FFmpeg), then loads the tiny model as a check. If any step fails, it moves to option 2.
2. **whisper.cpp** (`stt_engine: whispercpp`). Termux has no package for it, so the installer builds `whisper-cli` from source
   with clang/cmake into `~/superptt/bin` and downloads multilingual `ggml-{tiny,base,small}.bin` to `~/.superptt/models`.
   It uses the same tiers and language hints. whisper.cpp reports no confidence scores, so cloud fallback triggers only on
   language, script check, empty text or queue overflow, not on low confidence.
3. **cloud-only** (`stt_engine: cloud`). Every message goes to the cloud provider (ElevenLabs by default). Without a key,
   messages are recorded and marked `nokey`, then sent automatically once a key is set.

You can force an engine: `SUPERPTT_STT=whispercpp curl … | bash`, or `cloud`, or `faster-whisper`. `SUPERPTT_MODELS="tiny base"`
saves space. The engine in use appears in the installer's last line and as `stt_engine` in `~/superptt/config.json`.

## Audio playback
Android gives Termux no ALSA/PortAudio device, so the mixer's live speaker output is off (`output.mode: "off"`).
Play recordings in the console (each message has an audio player, which also works over the tunnel), or on the phone run
`termux-media-player play ~/superptt/data/rec/<day>/<channel>/<file>.wav`.

## Limitations
- The quick-tunnel URL changes on every restart. For a fixed hostname, set `public_url` in config.json and run a named
  tunnel by hand (`cloudflared tunnel run --token …`).
- `--private-broker` (Mosquitto) is not supported on the phone; use the public brokers or the Pi's broker.
- Android can still kill Termux under memory pressure or after OS updates. Check the battery settings again after an update.
- The `small` model on a phone CPU is slower than real time under load; the tiered queue falls back to base/tiny.
- Keep the phone on a charger; continuous STT drains the battery.
