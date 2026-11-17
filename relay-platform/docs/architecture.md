# Architecture – SanketPTT Relay V1

## Service boundaries

1. **Control API**: tenant, device, channel and session authorization over HTTPS; emits state events over WebSocket.
2. **Media plane**: mediasoup SFU workers carrying Opus audio over WebRTC/SRTP. The relay forwards media; it does not record or transcribe.
3. **Floor control**: atomic per-tenant/per-channel talker lease. A request succeeds only when the channel is free or the requester has an explicitly authorized priority. Lease has a short expiry and is renewed while PTT is held; release/disconnect/timeout frees it.
4. **MQTT adapter**: optional compatibility/control adapter for legacy clients. MQTT carries commands and status, not continuous audio by default.
5. **Admin and observability**: isolated from the media process. Dashboard failure must not stop media routing.

## Radio behaviour

- Half-duplex per channel: one active transmitter; all authorized subscribers may listen.
- Client sends PTT request; server grants or returns BUSY plus current talker metadata permitted for that tenant.
- On grant, client publishes its WebRTC audio producer; server routes it to authorized consumers in that channel.
- Release, disconnect, lease expiry or media failure ends the transmission.
- Emergency priority is role-gated, audited, and explicitly configured per tenant. It must not be an unauthenticated override.
- Busy/grant tones are generated locally by the client from server state, avoiding unnecessary tone streams.

## Multi-tenancy and security

- Every database row and cache key is tenant-scoped.
- Authorization is enforced server-side for every device, channel, producer and consumer operation.
- Use TLS for control traffic and DTLS-SRTP for WebRTC media; do not expose reusable API secrets in URLs.
- Store only hashed device credentials; support rotation and revocation.
- Admin accounts use separate authentication and role-based access.
- Apply rate limits, connection quotas, audit events and strict CORS/origin policy.

## Proposed components

- TypeScript/Node.js control service.
- mediasoup media workers (separate process/container boundary).
- PostgreSQL for tenants, users, devices, channels, roles and audit metadata.
- Redis for presence, short-lived session state and atomic floor leases.
- MQTT broker/adapter only when required for compatibility.
- Prometheus, Node Exporter and Grafana for metrics; application metrics for sessions, channels, active talkers, packet loss, jitter, RTT and errors.

## Capacity and scaling

The initial acceptance target is 50 simultaneously connected devices, validated by load tests on the selected VPS. Capacity depends on codec bitrate, number of listeners per transmission, packet overhead, network egress, CPU and media-worker configuration. Measure rather than promise a fixed user count. Scale media workers/nodes independently from the control plane when measurements justify it.

## Key design correction

WebRTC is the primary media path for the first reference client. RTP/UDP is not exposed as a generic public player URL. MQTT remains a compatibility/control path. A future RTP/SRT/RTSP gateway can be added as a separately secured adapter if a real device interoperability requirement calls for it.
