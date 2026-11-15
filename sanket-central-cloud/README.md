# Sanket Central Cloud

Central multi-tenant object storage, backup catalogue and Raspberry Pi migration service for Sanket PTT and Sanket Broadcast.

## Decisions

- Object store: Cloudflare R2, accessed through its S3-compatible API.
- Location preference: **Automatic / global access**, with no jurisdiction restriction selected.
- Bucket: one private bucket, `sanket-central`.
- Database: PostgreSQL for tenant/site/device registry, object metadata, backup manifests and audit-ready catalogue.
- API: FastAPI. Raspberry Pi devices authenticate using short-lived OIDC access tokens. R2 credentials remain on the server.
- Tenant isolation: tenant claim from verified JWT + PostgreSQL row-level security + server-generated object keys.
- Initial backup classes: configuration clone, full migration, scheduled backup and disaster recovery.

Global access does not mean every object is replicated to every region. R2 Automatic placement selects a location based on the bucket-creation request; location hints are best-effort. Choose the bucket's location deliberately at creation because it cannot simply be changed later. If a legal residency guarantee is required, select a jurisdiction explicitly before creating a separate bucket.

## Object layout

```text
tenants/{tenant_uuid}/sites/{site_uuid}/devices/{device_uuid}/{category}/{object_uuid}
```

Categories: recordings, transcripts, backups, images, diagnostics, screenshots, exports and releases.

Clients cannot submit an arbitrary tenant prefix. The API takes tenant identity only from the verified JWT, checks that the device belongs to the tenant/site, and generates the object key itself.

## API implemented in this first slice

- `GET /health`
- `POST /v1/sites` (tenant administrator)
- `POST /v1/sites/{site_id}/devices` (tenant administrator)
- `POST /v1/objects` (authenticated multipart upload with SHA-256)
- `GET /v1/objects` (tenant-scoped listing)
- `GET /v1/objects/{object_id}/download` (short-lived signed URL)
- `POST /v1/backups` (register a verified uploaded backup archive)
- `GET /v1/backups`
- `GET /v1/backups/{backup_id}/restore`
- `GET /v1/storage/summary`

This is a foundation, not a production-ready service yet. Scheduled backup orchestration, resumable multipart upload, restore-agent, lifecycle policies, quotas, audit events, malware scanning, admin UI, and end-to-end tests remain implementation work.

## Deployment prerequisites

1. Create a private R2 bucket named `sanket-central` in Cloudflare. For the requested global preference, choose Automatic location and no jurisdiction restriction. Do not enable public bucket access.
2. Create an R2 API token scoped only to this bucket with object read/write permissions required by the service.
3. Provision PostgreSQL 16+ and an OIDC identity provider. Configure JWT issuer, audience and JWKS URL.
4. Apply `migrations/001_initial.sql` with a database migration owner.
5. Create a separate runtime database role that does not own tables and does not have BYPASSRLS. Grant only required table permissions.
6. Configure environment variables from `.env.example` in the deployment secret manager.
7. Deploy the API behind HTTPS. Do not expose PostgreSQL or R2 credentials to Pi clients.

## Local API container

Build with `api/Dockerfile`. Run the API only after PostgreSQL, schema, R2 bucket and OIDC settings are configured. The repository intentionally contains no live credentials and does not create cloud resources automatically.

## Backup and migration package contract

Every archive must include a versioned manifest with:
- backup UUID, type, schema version, application version and creation timestamp;
- source tenant/site/device identifiers;
- component inventory and relative paths;
- per-file size and SHA-256;
- source OS, architecture and hardware inventory;
- configuration version and selected recording/transcript ranges.

Never include plaintext MQTT passwords, API tokens, private keys or R2 credentials. Re-provision secrets on the replacement Pi. Before restore, validate signature/checksums, compatibility, free space and hardware mappings; stage restore, then activate only after operator confirmation. Keep the original backup immutable.

## Production hardening required before customer data

- Use a dedicated non-owner PostgreSQL role; verify RLS using cross-tenant negative tests.
- Add audit log table and immutable backup state transitions.
- Add resumable multipart upload and upload-finalize verification for large media.
- Add quotas/rate limits per tenant and device, plus retention policies that never delete unverified-only copies.
- Add object versioning/retention strategy and a second independent backup of critical manifests/database.
- Add backup encryption at the Pi before upload (tenant-scoped key management); R2 server-side encryption alone does not replace end-to-end package encryption.
- Add malware scanning for imported archives and strict archive path traversal protections.
- Add OIDC provisioning, refresh-token rotation and device revocation.
- Add scheduled agent on Pi with offline queue, retry/backoff and idempotency.
- Add restore dry-run, rollback and same-device Sanket PTT/Broadcast coexistence tests.

## Pricing reference

R2 standard storage is currently listed at $0.015 per GB-month, with no internet egress fee; request operations are charged separately. Confirm current pricing before production budgeting.
