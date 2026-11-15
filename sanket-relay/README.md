# Sanket Relay Server (Raspberry Pi)

Standalone, local-first relay service for Raspberry Pi 5. It is installed separately from Sanket PTT and Sanket Broadcast.

## Install

On a Raspberry Pi running Ubuntu or Raspberry Pi OS 64-bit:

```bash
curl -fsSL https://raw.githubusercontent.com/vibhvesh/sanketptt/sanket-core-v1/sanket-relay/install.sh -o /tmp/sanket-relay-install.sh
sudo bash /tmp/sanket-relay-install.sh
```

The installer creates an isolated `sanket-relay` Linux user, virtual environment, configuration directory at `/etc/sanket-relay`, data/log directory at `/var/lib/sanket-relay`, and systemd unit `sanket-relay.service`. It does not stop, replace, or modify Sanket PTT/Broadcast services.

The installer prints a generated access token once. Save it securely. Clients connect to:

`ws://PI-IP:8765/ws?token=YOUR_TOKEN&channel=CHANNEL_NAME`

This is suitable for a trusted LAN pilot only. Do not expose plain WebSocket port 8765 directly to the public internet. For remote access, put it behind a TLS reverse proxy or VPN; a TLS-enabled deployment guide will be added before public production use.

## Wire protocol (pilot v1)

- Client connects to `/ws` with token and channel query parameters.
- Server sends a JSON `welcome` message.
- Client sends binary WebSocket frames containing encoded audio payloads.
- Server forwards frames to other authenticated clients in the same channel, excluding the sender.
- JSON `ping` messages receive `pong`; `status` reports channel and client counts.
- Channel names are restricted to letters, digits, underscore and hyphen.

Audio codec, packet framing, PTT floor control, user/device identity, tenant ACLs and compatibility with the existing Sanket MQTT audio protocol are integration work, not silently assumed by this transport pilot.

## Operations

```bash
sudo systemctl status sanket-relay
sudo journalctl -u sanket-relay -f
sudo systemctl restart sanket-relay
sudo systemctl disable --now sanket-relay
```

Health check: `http://PI-IP:8765/health`

## Security notes

- A random bearer token is generated at install time and stored in a root-owned config file.
- The service binds to all interfaces for LAN access.
- Use a firewall to restrict access to trusted LAN clients.
- Use TLS/VPN before remote access.
- Do not share the token in screenshots, logs or public channels.
- This pilot is single-installation/single-token; tenant and per-user/device authorization are planned separately.
