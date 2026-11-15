# Sanket Central Cloud — implementation status

Branch: `sanket-broadcast-v1`

## Implemented in this development slice

- FastAPI service scaffold using Cloudflare R2's S3-compatible endpoint.
- Verified OIDC/JWKS JWT validation with tenant identity derived from the token.
- PostgreSQL schema for sites, devices, stored objects and backup catalogue.
- PostgreSQL row-level security policies for tenant-scoped rows.
- Private object key generation under tenant/site/device prefixes.
- Authenticated upload with server-calculated SHA-256.
- Tenant-scoped object listing and short-lived signed downloads.
- Backup catalogue registration and restore-download URL.
- Responsive operator dashboard served at `/`, with tenant-scoped storage metrics, backup history, object inventory and signed download/restore package actions.
- Docker Compose deployment stack for PostgreSQL, API and Caddy HTTPS reverse proxy.
- Raspberry Pi backup agent for config-clone/full-migration/scheduled/disaster-recovery package creation.
- Restore agent verifies the archive hash and extracts into a staging directory only.
- Example daily systemd timer/service and example agent configuration.

## Not yet production-ready

- No R2 bucket has been created and no credentials have been provisioned.
- No live OIDC provider, PostgreSQL instance or deployed API has been configured.
- No end-to-end or load tests have been run against a real R2 account or Raspberry Pi.
- Scheduled backup requires a configured OIDC client-credentials identity with the required tenant/device claims.
- Upload is currently API-proxied, not resumable multipart direct-to-R2; large deployments need multipart upload with retry/resume.
- Restore only stages files; it does not automatically replace live Sanket PTT/Broadcast configuration or databases.
- Application-specific configuration export must be prepared to omit embedded credentials.
- Need quota enforcement, per-tenant retention policies, audit events, malware/archive scanning, backup immutability/version strategy, database backup, key management and credential rotation.
- Need cross-tenant security tests using a non-owner PostgreSQL runtime role with RLS enabled.
- Dashboard is an initial operator console; site/device inventory management, backup creation controls, quota management and operator approval/rollback workflow are not yet implemented.

## Latest build notes

- Corrected a malformed import line in the API module and added the dashboard root route.
- Corrected the dashboard asset path for the container layout.
- Added cleanup of an uploaded R2 object if its database metadata insert fails.
- The dashboard uses a short-lived bearer token held in page memory; it does not persist the token in local storage.
- Dashboard/API integration and the Docker image have not yet been executed in a real deployment. Run `docker compose config` before startup and perform API, RLS and R2 smoke tests.

## Required first deployment steps

1. Create a private R2 bucket with Automatic location (global access preference) and no public access.
2. Create bucket-scoped R2 credentials; keep them only in server-side secret storage.
3. Configure OIDC issuer, audience, JWKS and a device service identity.
4. Provision PostgreSQL and apply `migrations/001_initial.sql` as a migration owner.
5. Create a separate runtime role without table ownership or BYPASSRLS.
6. Configure environment variables and deploy behind HTTPS.
7. Register a tenant, site and Raspberry Pi device, then configure the Pi agent.
8. Run a small test backup, verify object checksum, and perform a restore into a disposable staging directory before enabling daily schedules.
