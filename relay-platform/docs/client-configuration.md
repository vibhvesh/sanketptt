# SanketPTT Reference Client – Configuration

The reference client supports multiple saved relay profiles and provider adapters. A profile selects a control API and compatible media protocol; it does not assume every public relay implements the SanketPTT API.

## Profile fields

- `display_name`: user-visible profile label.
- `provider_type`: `sanket-relay` or a specifically implemented adapter such as `mqtt-legacy`.
- `control_api`: HTTPS base URL for the selected provider.
- `device_id`: registered device identifier.
- `credential_ref`: secure local keychain/keystore reference; never store a plaintext secret in exported YAML.
- `default_channel`: optional authorized channel.
- `auto_reconnect`: boolean.
- `media_protocol`: negotiated from provider capabilities; V1 Sanket Relay uses WebRTC.

## Example (illustrative; no real credentials)

```yaml
profile:
  display_name: Canberra Private
  provider_type: sanket-relay
  control_api: https://relay.example.invalid/api/v1
  device_id: DEVICE001
  credential_ref: os-keychain://sanketptt/device001
  default_channel: master
  media_protocol: negotiate
  auto_reconnect: true
```

## Connection sequence

1. User selects a saved profile.
2. Client obtains a short-lived token using the provider adapter.
3. Client fetches capabilities and authorized channels.
4. Client joins a channel and negotiates the media session.
5. Client listens; on PTT press it requests floor control before publishing audio.
6. On BUSY, client plays the locally generated radio busy tone. On grant, it plays a local grant tone and starts media publishing.
7. On release, it stops publishing and releases the floor lease.
8. On network loss, it stops transmission immediately, reconnects with backoff, and requires a fresh floor grant before transmitting again.

## Public relay compatibility

A configurable URL alone cannot make an arbitrary public relay compatible. Each provider needs a protocol adapter matching that provider's authentication, channel, audio and floor-control behaviour. Add adapters only against documented protocols and test devices.
