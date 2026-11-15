# Sanket Broadcast v1 — Operator Cockpit & Hardware Requirements

Status: requirements baseline for the Raspberry Pi implementation. This document extends the initial audio-router slice; it does not replace or modify the existing Sanket PTT Control Room.

## Product objective

A lay operator should be able to power on the Raspberry Pi 5, click one desktop icon (or use the attached display/touchscreen), and operate an eight-line PTT monitoring and broadcast cockpit without a keyboard or terminal.

## 1. Hardware discovery and readiness

At startup and on demand, the application shall inventory:
- Raspberry Pi model, OS/architecture, kernel, CPU, RAM, storage and temperature/throttling status.
- USB devices and USB topology; identify audio interfaces by descriptive hardware identity (USB vendor/product, serial where available, ALSA card ID, interface name and host API).
- ALSA/PulseAudio/PipeWire/PortAudio playback and capture endpoints, channel counts, sample rates and supported formats.
- HDMI/external display state, resolution and touch input devices where available.
- Required kernel modules, firmware and permissions; report missing or failed components with operator-friendly remediation.

The app must not blindly install random third-party drivers. Prefer in-kernel Linux drivers and class-compliant USB Audio devices. Where a device requires a vendor driver or is unsupported, show it as unsupported with the exact diagnostic. Do not claim a device is ready until a playback test succeeds.

Device identity must not depend on transient numeric ALSA or PortAudio indexes. If identical USB dongles cannot be uniquely distinguished (no serial/unique path), show their physical USB port path and let the operator label them (Speaker A, Speaker B, etc.).

Provide:
- Automatic scan at boot and hot-plug/unplug monitoring.
- Rescan button.
- Per-device status: detected, driver/module, output channels, sample rate, selected/assigned, test status, last error.
- Safe recovery after disconnect/reconnect; no crash and no loss of MQTT ingest, recordings or STT.

## 2. Eight-line routing matrix

Support at least eight logical PTT lines initially and four physical output devices in the initial hardware profile. Do not hard-code the system to exactly eight/four; use a configurable device/line inventory.

Routing is many-to-many:
- One PTT line can feed one or several outputs.
- Several PTT lines can be mixed into one output.
- All eight lines can be routed to one output, all four outputs, or any chosen combination.
- One-to-one routing is supported.
- A line can be muted from monitoring without stopping its recording/transcription.
- Each output has independent volume, mute, gain limit, and channel assignment.
- Support mono logical feeds and stereo physical output devices. Display logical channels separately from physical output channels.

The cockpit must display the active routing matrix and allow an operator to save named routing profiles (e.g. Normal, Night Shift, Emergency).

## 3. Line-to-line forwarding (PTT relay)

Treat this as a distinct feature from speaker monitoring.

Allow an authorized operator to configure a source PTT line to be retransmitted to one or more destination PTT lines through the existing MQTT protocol. This is a controlled digital relay, not simply copying sound to a speaker.

Requirements:
- Explicit source → destination rules; support one-to-many and selected groups.
- Per-rule enable/disable, schedule/profile, priority and audit log.
- Prevent forwarding loops and duplicate retransmission (loop detection, hop/relay metadata, TTL and origin tracking).
- Prevent accidental echo-back to the source line.
- Respect floor/busy state and channel permissions; define whether relay waits, drops, or queues when destination is busy.
- Emergency relays may use a configured priority/cut-in policy only where the protocol and recipient clients support it.
- Show relay state and last forwarded event on the dashboard.

## 4. IF-THIS-THEN-THAT alert automation

Use the existing alert/event publication path as the trigger source; do not create a parallel alert publisher.

Rule examples:
- IF emergency alert on any monitored line → forward alert/audio to all configured PTT lines.
- IF MAYDAY on Line 2 → relay to Control and Master.
- IF keyword alert on a selected line → play a local audible alarm and notify selected lines.
- IF a USB output fails → show operator warning; optionally reroute monitoring to a configured fallback output (never silently change routing).

Rule fields:
- Trigger type, source line/group, event/keyword/severity, optional time window.
- Actions: local alarm, dashboard notification, route live monitoring to outputs, relay PTT message to destination lines.
- Conditions, cooldown, deduplication, enabled state, priority and audit trail.
- Test/simulate rule mode before enabling.
- Emergency rules must be visually distinct and require an explicit confirmation before activation.

Important distinction: forwarding an alert notification/event is not automatically the same as forwarding the original live audio or retransmitting a PTT message. The rule editor must let the administrator choose the intended action.

## 5. Operator cockpit UI

Tabbed, touch-friendly web application shared by the Pi's local display and remote browser. One backend/service and one configuration store; no duplicate audio engine.

Tabs:
1. **Overview** — green/amber/red system health, broker connection, monitored line count, active speakers, USB outputs, recording/STT status, alerts.
2. **Lines** — eight (or configured number) PTT line tiles, activity, speaker/source, recording and transcription state, monitor/mute controls.
3. **Audio Routing** — many-to-many matrix, output meters, per-output volume/mute, test tone, saved profiles.
4. **Broadcast & Relay** — source/destination rules, live relay state, floor/busy indication, loop prevention status.
5. **Alert Automation** — IF/THEN rules, test mode, enable/disable and event history.
6. **Hardware** — hardware inventory, driver/module status, output channel counts, rescan, test playback and diagnostics.
7. **Recordings & Transcripts** — search/filter and playback of independent channel/speaker recordings and transcripts.
8. **Settings & Diagnostics** — network/MQTT, admin, retention, logs, update/repair and support bundle.

Design for large touch targets, high contrast, clear words/icons, no terminal interaction for normal operations. Confirm destructive or safety-critical actions. Provide a simple mode for operators and an advanced admin mode.

## 6. Raspberry Pi 5 display and desktop integration

- Support HDMI external monitor and common touch displays; adapt to the detected resolution/orientation.
- Install a desktop shortcut named Sanket Broadcast with an application icon.
- Optional auto-launch in kiosk/full-screen mode after desktop login.
- A second desktop shortcut opens Hardware Diagnostics.
- If the kiosk browser exits, provide a desktop relaunch shortcut; backend services continue running.
- Remote web dashboard and local display use the same authenticated web app/API.
- Do not assume every external monitor is a touchscreen; detect touch input separately.

## 7. Installer, upgrades and recovery

One-line installer should:
- Check supported OS, architecture, Pi model and available disk/RAM.
- Install only required system packages and standard in-kernel audio support; no arbitrary driver downloads.
- Create isolated application environment and dedicated service account.
- Install systemd service, desktop icons and optional kiosk launcher.
- Preserve existing Sanket PTT installation, configuration, recordings and database.
- Offer LAN-only by default; remote tunnel is optional and explicit.
- Provide update, repair and uninstall modes. Uninstall must ask whether to retain recordings/configuration.
- Verify service health, dashboard availability and detected audio devices at completion.

## 8. Reliability, security and acceptance tests

- MQTT ingest, recording and transcription continue if all speaker outputs are unplugged.
- Eight simultaneous logical PTT lines can be monitored and routed according to the matrix.
- Multiple lines mix on one output; one line can be duplicated to multiple outputs.
- Disconnect/reconnect each USB output without crashing the service.
- No silent routing changes; fallback behavior is visible and logged.
- Relay loops, source echo and duplicate forwarding are blocked in automated tests.
- Emergency rules are tested in simulation before live activation.
- Dashboard works locally on HDMI and remotely over LAN; kiosk restart does not restart the audio engine.
- Admin-only changes are authenticated and audited.
- Long-duration soak test for audio underruns, clock drift, memory growth and queue backpressure.

## 9. Implementation sequence

1. Hardware inventory and diagnostics API.
2. Robust multi-output audio engine and routing matrix.
3. Integrate existing Sanket PTT MQTT ingest, recorder and STT without duplicating them.
4. Cockpit dashboard and touchscreen/kiosk packaging.
5. Safe PTT line relay with loop prevention and floor handling.
6. Alert automation using existing alert events.
7. Installer, update/repair/uninstall, hardware-in-loop and soak tests.

## Engineering constraints

- Four USB stereo sound cards do not automatically guarantee eight perfectly synchronized independent mono outputs. Validate the actual devices, clocks, ALSA configuration and simultaneous stream stability on the target Pi. For higher reliability, consider a single multichannel USB audio interface.
- Audio monitoring routing, event notification forwarding, and live PTT retransmission are separate operations and must be separately configured.
- Hardware support depends on Linux kernel/firmware and device compatibility; the app can detect/report driver readiness but cannot promise a driver exists for every USB device.


## 10. Same-device coexistence: Sanket PTT + Sanket Broadcast

The first deployment and test target is one Raspberry Pi running both applications at the same time. A second Pi is not required for the initial pilot.

- Keep the existing Sanket PTT Control Room installed and operational alongside Sanket Broadcast.
- Use separate application directories, virtual environments, systemd services, configuration files, logs and data directories.
- Leave the existing PTT dashboard/API on its current port (documented as 8090). Give Broadcast a configurable separate port, initially proposed as 8091, and check for conflicts during installation.
- Never overwrite, migrate, rename or delete existing PTT databases, recordings, environment files, configuration, service or desktop shortcuts.
- Define service ownership clearly: existing PTT remains authoritative for its current ingest, recording and transcription until a tested migration is explicitly approved. Broadcast owns its new routing cockpit and relay features.
- Integrate through documented interfaces. Avoid duplicate MQTT subscriptions that could cause duplicate recording, transcription or alert handling.
- Establish a single owner for each physical playback stream. Do not let both applications open the same exclusive ALSA device in conflicting modes; use an explicit API/IPC audio handoff where needed.
- Monitor combined CPU, RAM, storage and USB load, plus each service's health.
- Installer detects the existing PTT installation, checks its health before and after installing Broadcast, and supports rollback/uninstall of Broadcast independently.
- Start, stop, restart, update and uninstall each application independently. Restarting Broadcast must not stop PTT.
- Provide separate desktop shortcuts and a clear landing choice for both applications.

### Same-device acceptance test

1. Boot one Raspberry Pi 5 with both services enabled.
2. Confirm both services remain active and both dashboards open on separate ports.
3. Receive multiple PTT lines and verify existing recording/transcription is unchanged.
4. Route monitoring through Broadcast to the configured USB outputs.
5. Test alert automation and relay in a controlled environment.
6. Disconnect/reconnect an output and restart Broadcast; verify PTT ingest, recording and transcription continue.
7. Reboot and verify independent startup without port, device-lock or data-directory conflicts.

The same-device pilot is the default deployment target. A second Pi is an optional later scale-out or redundancy option.
