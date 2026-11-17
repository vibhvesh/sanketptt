# Control API Contract – Draft V1

Base path: `/api/v1`. All endpoints require TLS. Authenticated requests use short-lived bearer tokens issued to a registered device or user. Tenant identity is derived from the authenticated principal, not trusted from a caller-supplied tenant header.

## Endpoints

- `POST /auth/device-token` – exchange device ID and device secret for a short-lived access token.
- `GET /me` – return authenticated principal, tenant and assigned roles.
- `GET /channels` – list channels visible to the principal.
- `POST /channels/{channelId}/join` – authorize channel membership and return media-session negotiation details.
- `POST /channels/{channelId}/leave` – leave channel and close associated media resources.
- `POST /channels/{channelId}/floor/request` – request the half-duplex transmit lease; returns `GRANTED` or `BUSY`.
- `POST /channels/{channelId}/floor/renew` – renew the lease while PTT remains held.
- `POST /channels/{channelId}/floor/release` – release the lease.
- `POST /media/transports` – create a WebRTC transport for the authenticated session.
- `POST /media/transports/{transportId}/connect` – complete DTLS connection.
- `POST /media/transports/{transportId}/produce` – publish authorized Opus audio after floor grant.
- `POST /media/transports/{transportId}/consume` – subscribe to an authorized channel producer.
- `GET /health/live` – process liveness only.
- `GET /health/ready` – readiness including required dependencies; keep private/internal.

## WebSocket events

Authenticated WebSocket session events: `channel.state`, `floor.granted`, `floor.busy`, `floor.released`, `device.presence`, `media.reconnect_required`, and `service.notice`. Validate tenant and channel membership for every subscription.

## Error model

Use stable machine-readable codes: `UNAUTHENTICATED`, `FORBIDDEN`, `CHANNEL_NOT_FOUND`, `CHANNEL_BUSY`, `FLOOR_LEASE_EXPIRED`, `QUOTA_EXCEEDED`, `MEDIA_NEGOTIATION_FAILED`, and `RATE_LIMITED`. Include a request ID; never return secrets or cross-tenant resource existence details.

## Notes

This is a contract proposal, not a deployed API. Final request/response JSON schemas and OpenAPI document are part of implementation review. Never use REST polling for continuous audio; media flows through WebRTC.
