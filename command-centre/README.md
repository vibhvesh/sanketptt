# Sanket Voice Command Centre (PC)

Receive-only PC console for the existing Sanket MQTT/WSS relay. It plays one selected line through one PC speaker and supports offline Vosk voice commands and timed scanning.

## Install on Windows 10/11
1. Install Python 3.11 64-bit.
2. In PowerShell, run `py -3.11 -m venv .venv`, activate `.venv\\Scripts\\Activate.ps1`, then `pip install -r requirements.txt`.
3. Download the Vosk English model `vosk-model-small-en-us-0.15` from https://alphacephei.com/vosk/models and extract it under `models/`.
4. Copy `config.example.json` to `config.json`; set channel names, emergency channels, and model path.
5. Run `python app.py`; open http://127.0.0.1:8765.

## Commands
Alpha Romeo line one through line ten; scan all lines; stop scanning; next line; previous line; mute; unmute; volume fifty / twenty five / one hundred.

## Relay compatibility
Subscribes to `<prefix>/<channel>/floor` and `<prefix>/<channel>/audio`. Audio payload is `[one-byte sender-id length][sender-id][mono 12 kHz Int16LE PCM]`, matching `pi/sanket/mqtt_relay.py`. The app is receive-only and never publishes floor claims or audio.

## Safety
Emergency channels pre-empt ordinary playback. Scanner holds on a line while its floor is active. The local UI binds to 127.0.0.1 only. Validate the PC microphone, speaker, broker access, channel names and emergency policy in a controlled test before operational use. Use an authenticated private broker for production; do not rely on shared public broker credentials.
