# Sanket PTT — Raspberry Pi 5 listen-only client

Turns a Raspberry Pi 5 into a always-on **listen-only** station for the Sanket PTT web radio:
it joins a channel, shows up in the radio's online list as `SanketPi-<hostname>`, plays traffic
live on a speaker, transcribes every transmission with Whisper (offline, on the Pi), saves
WAV + JSON per clip, and speaks keyword alerts aloud. It **never takes the floor or transmits**
(it only publishes its own presence heartbeat, exactly like `transcribe/` "SanketTranscribe").

## Hardware
- Raspberry Pi 5, 4 GB or 8 GB (8 GB recommended for `small` model)
- Official Active Cooler (Whisper keeps the CPU busy)
- Official 27 W USB-C PSU
- microSD 32 GB+ (A2 class) with Raspberry Pi OS Bookworm 64-bit
- Audio: USB speaker / USB sound card, **or** an audio HAT (ReSpeaker 2-Mic / WM8960)
- Network: Ethernet or Wi-Fi

## Install (one line)
```bash
curl -sSL https://raw.githubusercontent.com/vibhvesh/sanketptt/main/pi/install.sh | bash
```
Installs apt deps (python3-venv, espeak-ng, libportaudio2, alsa-utils, ffmpeg), a venv in
`~/sanket-pi`, pre-downloads the Whisper model, and enables `sanket-pi.service` at boot (runs as your user).

## Configure
Edit `~/sanket-pi/config.yaml`, then `sudo systemctl restart sanket-pi`.

| key | meaning |
|---|---|
| `channel` | channel name (`?ch=` in the radio link), default `virtual` |
| `callsign` | shown in the online list; empty → `SanketPi-<hostname>` |
| `broker_url` | `wss://public.cloud.shiftr.io` (same broker as the radio) |
| `whisper_model` | `tiny` / `base` (default) / `small` |
| `language` | `auto`, `en`, `hi`, … |
| `keywords` | alert words (Latin + Devanagari OK) |
| `volume` | live playback gain 0–2 |
| `audio_device` | `null` = ALSA default, or a name/index from `~/sanket-pi/venv/bin/python -m sounddevice` |
| `tts`, `tts_engine`, `piper_model`, `beep` | spoken alert "Alert from <callsign>: <text>" via espeak-ng (or piper) + beep |
| `retention_days` | clips in `~/sanket_clips` older than this are deleted |

Run manually: `~/sanket-pi/venv/bin/python ~/sanket-pi/sanket_pi.py --channel test --no-audio`
(`--tts-file-dir DIR` writes alert audio to files instead of playing it).

## Logs & files
- `journalctl -u sanket-pi -f`
- rotating log: `~/sanket_clips/sanket_pi.log`
- per clip: `~/sanket_clips/YYYYMMDD_HHMMSS_<callsign>.wav` + `.json` (transcript, language, keywords, location);
  SSTV transmissions are not transcribed — their JPEG clean copy is saved as `.jpg`.

## Audio HAT notes
- **USB speaker/card**: plug in; check `aplay -l`. Make it default with `~/.asoundrc`:
  `defaults.pcm.card 1` / `defaults.ctl.card 1` (use your card number).
- **WM8960 HAT / ReSpeaker 2-Mic (v2 uses TLV320AIC3104, v1 uses WM8960)**: on Bookworm add to
  `/boot/firmware/config.txt`: `dtparam=i2s=on` and `dtoverlay=wm8960-soundcard` (v1/WM8960) or
  `dtoverlay=respeaker-2mic-v2_0` (v2), reboot, then `aplay -l` should list the card. If the overlay is
  missing, use the vendor driver (`git clone https://github.com/waveshare/WM8960-Audio-HAT && sudo ./install.sh`
  or Seeed's `seeed-voicecard`) — these need matching kernel headers. Set volume with `alsamixer`.

## Troubleshooting
- **No sound**: `speaker-test -t wav -c 2`; set `audio_device`; ensure user is in the `audio` group (reboot after install).
- **Not in online list**: check network/time (`timedatectl`), presence uses timestamps; check the channel name matches.
- **Slow transcripts**: use `tiny` or `base`; `small` is ~3–5× slower. Live audio is never delayed by transcription.
- **Hindi**: set `language: hi` for Devanagari output; `auto` may sometimes output Urdu script or romanised text for short clips.
- **Service won't start**: `journalctl -u sanket-pi -b --no-pager | tail -50`.
