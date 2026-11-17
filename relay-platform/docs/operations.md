# Operations and Admin Monitoring – V1

## Dashboard sections

- Overview: CPU, RAM, disk, network throughput, uptime, active devices, active media transports, active channels and current talkers.
- History: 15-minute, 1-hour, 24-hour, 7-day and 30-day views.
- Channel activity: tenant-scoped joins, leaves, floor requests, grants, busy responses and transmission durations (metadata only; no audio content).
- Service health: API, media workers, Redis, PostgreSQL and MQTT adapter when enabled.
- Alerts: configurable CPU, memory, disk, egress, packet loss, jitter, worker crash and connection-failure thresholds.
- Audit: administrator actions, device registration/revocation and security events.

## Metrics

Collect CPU, memory, disk, network, process uptime, WebRTC transports, producers, consumers, active talkers, channel occupancy, connection attempts, authentication failures, request latency, packet loss, jitter, RTT and media-worker errors.

## Separation and retention

Monitoring must not be in the media forwarding critical path. Protect Grafana and Prometheus behind admin authentication or a private network. Define retention and tenant access rules before production. Do not collect audio payloads or credentials in logs.

## Initial deployment checklist

- Confirm VPS OS, CPU, RAM, disk, public IP and firewall/NAT behaviour.
- Configure DNS and TLS.
- Open only required control and WebRTC UDP port ranges.
- Use persistent volumes and tested backups for PostgreSQL configuration/data.
- Set secrets through environment/secret management, never commit them.
- Run health checks, reconnect tests, tenant-isolation tests and 10/25/50-device load tests.
- Verify monitoring remains available when media workers restart, and media continues if the dashboard is unavailable.

No installer or production deployment is included in this bootstrap commit.
