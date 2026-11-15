# Sanket Core — active development scope

**Status:** Active. This branch prioritizes local Raspberry Pi communication, audio and operator functions.

## Explicitly deferred
- Sanket Central Cloud and Cloudflare R2
- Backup/export, migration and disaster recovery
- Cloud storage dashboards, cloud sync and cloud device inventory

The existing cloud work is retained in the earlier draft PR/branch for later; it is not a dependency of the core runtime and must not be installed or started as part of the core pilot.

## Core product modules
1. **Sanket PTT:** existing MQTT-based PTT receive/transmit and channel membership.
2. **Sanket Broadcast:** operator-controlled broadcast to one, selected or all logical PTT channels.
3. **Sanket HDR:** independent multi-line recording and forensic playback, preserving original audio and event metadata.
4. **Recording-to-Text:** asynchronous transcription with language identification, channel/speaker separation, timestamps and searchable output.
5. **Operator Cockpit:** touch-friendly overview, line activity, routing matrix, broadcast/relay controls, alerts, recordings and hardware diagnostics.
6. **Pi Runtime:** local-first operation, systemd services, automatic startup and safe recovery after USB audio disconnects.

## Runtime invariants
- Audio ingest, recording and transcription are independent of speaker playback.
- A failed or unplugged output must never stop ingest or recording.
- Speaker monitoring, live PTT retransmission and alert notification are separate actions.
- Relay rules must prevent loops, source echo and duplicate forwarding.
- Local PTT, routing and recording continue without internet. Cloud features are not required.
- Existing Sanket PTT installation, ports, data and service remain untouched during the Broadcast pilot.

## Delivery order
1. Core relay engine with automated loop/deduplication tests.
2. Reliable audio routing and hardware readiness tests.
3. Integrate the existing PTT MQTT event/audio protocol without duplicate subscribers.
4. Local recording and asynchronous transcription pipeline.
5. Unified operator cockpit and broadcast controls.
6. Pi installer, systemd integration and hardware-in-loop/soak tests.

## Pilot gate
Do not replace the existing PTT service. First run Broadcast alongside it on one Pi, using a separate service/config/data directory and port. Validate multiple simultaneous lines, recording continuity during output failure, relay loop prevention, reboot recovery and long-duration stability before production use.
