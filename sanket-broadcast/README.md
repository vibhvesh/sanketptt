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


## Central cloud storage (initial adapter)

The provider-independent S3-compatible storage adapter is in `pi/sanket_broadcast/cloud_storage.py`. It supports tenant/site-scoped object keys, connection checks, uploads, checksum-verified downloads and listing. See [CLOUD_STORAGE.md](CLOUD_STORAGE.md) for setup and security boundaries. This is the storage adapter foundation, not yet the complete background sync, backup/restore workflow or production installer.


## Central storage

Sanket Central Cloud is being developed under `../sanket-central-cloud/`. It provides the first API and Raspberry Pi agent foundation for tenant-isolated Cloudflare R2 object storage, backup catalogue and staged migration/restore.

- Cloud storage design: `../sanket-central-cloud/README.md`
- Implementation status and deployment gates: `../sanket-central-cloud/IMPLEMENTATION_STATUS.md`
- Raspberry Pi export/restore agent: `../sanket-central-cloud/pi-agent/backup_agent.py`

The cloud service is not yet deployed or production-ready. See the implementation status before connecting real customer recordings.
