# SanketPTT Relay Platform

Independent, multi-tenant, radio-style audio relay service for Canberra Vision AI.

## V1 goals

- 50+ connected devices as an initial load-test target (not a capacity guarantee).
- Multiple tenant-isolated channels.
- Half-duplex, one active talker per channel, many listeners.
- Opus voice media with WebRTC/SRTP for supported clients.
- HTTPS control API and WebSocket events.
- MQTT compatibility adapter for existing integrations; MQTT is not the primary continuous-audio transport.
- Configurable SanketPTT reference client with saved relay profiles.
- Admin dashboard and independent monitoring.
- No recording or transcription in V1.

## Repository status

This is an architecture/bootstrap proposal on branch `sanketptt-relay-bootstrap`, under `relay-platform/` in the existing `vibhvesh/sanketptt` repository. It is intentionally isolated from `main`. A dedicated `vibhvesh/SanketPTT-Relay` repository should be created and this directory moved there before production implementation.

## First review

Review `docs/architecture.md`, `docs/api-contract.md`, `docs/client-configuration.md`, and `docs/operations.md`. No service is deployed and no credentials or live endpoints are included.
