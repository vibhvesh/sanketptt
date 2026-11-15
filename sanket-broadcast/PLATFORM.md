# Sanket Broadcast platform baseline

## Supported target

- Hardware: Raspberry Pi 5, 64-bit ARM.
- Preferred OS: Ubuntu 26.04.1 LTS 64-bit.
- Compatibility OS: Ubuntu 24.04 LTS 64-bit.
- Use Ubuntu Desktop when the Pi's HDMI display/touchscreen must run the local operator cockpit.
- Ubuntu Server is supported for headless/LAN deployments.

Canonical currently lists Raspberry Pi 5 as certified for Ubuntu 26.04 LTS. For a fresh Ubuntu 26.04 image on Pi 5, Canonical documents a minimum boot EEPROM date of 2025-02-11. Check with `rpi-eeprom-update` before deployment.

## Recommended pilot hardware

- Raspberry Pi 5, 8 GB RAM recommended for the combined PTT + Broadcast + local speech workload.
- Active cooler and official 27 W USB-C power supply.
- NVMe SSD (with a compatible Pi 5 M.2 HAT) for recordings and database; high-endurance microSD is acceptable for initial bench tests.
- Powered USB 3 hub for multiple USB audio adapters; use class-compliant USB Audio devices.
- HDMI monitor; touch support is optional and must be detected rather than assumed.
- Ethernet preferred for stable MQTT/network operation.

## Support policy

The application must inspect the real OS, kernel, Pi model, USB topology, ALSA/PortAudio devices and display session at runtime. It must not install arbitrary vendor drivers. Prefer Linux in-kernel USB Audio class drivers. A device is only marked playback-ready after an output test succeeds.

Ubuntu 26.10 is not the production baseline: use the LTS release for a long-running operator appliance. Revalidate this policy when a later LTS release becomes available.

## Workload boundaries

The eight logical PTT lines and four physical outputs are routing capacities, not a promise that every speech-to-text model can transcribe eight simultaneous conversations in real time on the Pi CPU. Recording and live audio routing must remain independent of transcription queues. Gujarati and other lower-resource language recognition can use the existing configured LAN/cloud fallback when local inference is too slow or inaccurate.
