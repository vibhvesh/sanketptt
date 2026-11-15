# Sanket Broadcast — Raspberry Pi v1

A new Raspberry Pi broadcast/control-room runtime, developed alongside the existing Sanket PTT Control Room. The legacy implementation is not modified.

## v1 goals
- Receive Sanket PTT MQTT audio using the existing wire protocol.
- Keep recording and transcription independent of speaker playback.
- Route each channel to one or more independently selected USB audio devices.
- Mix multiple channels assigned to the same physical output.
- Discover devices by stable name/host API selectors; never persist numeric indexes.
- Provide one API and one web dashboard for remote browsers and the Pi touchscreen.
- Continue receiving/recording if a speaker or USB audio device is unavailable.

## Proposed runtime
MQTT ingest → per-channel/per-speaker stream buffers → recorder + transcription queues
                                      ↘ output router → USB audio devices

The output router is isolated from recording and transcription. A failed output must not stop ingest or lose recordings.

## Initial implementation slice
pi/sanket_broadcast/audio_router.py implements device discovery, stable selector resolution, per-output streams, per-channel routing, per-output gain/mute and software mixing. Hardware validation is still required on the target Pi and sound cards.

## Configuration
See pi/config.example.json. Each output has a stable device selector (name_contains and optional hostapi_contains), an id, channel list, volume and mute flag.

## Development
On Raspberry Pi OS 64-bit:

    sudo apt-get install -y python3-venv libportaudio2 alsa-utils
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt

This first commit establishes the independent audio-routing core; MQTT, storage, STT, web API, kiosk launcher and installer are subsequent integration steps. Do not point production services at this v1 until integration and hardware tests pass.
