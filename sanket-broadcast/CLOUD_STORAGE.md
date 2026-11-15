# Sanket Central Storage — first implementation slice

## Architecture

Sanket Broadcast uses an S3-compatible object-storage interface. Cloudflare R2 is the first target, but the application talks to the S3 API so another compatible provider can be selected later. The Raspberry Pi keeps its local NVMe/SSD buffer and continues recording when the internet or cloud is unavailable. Cloud upload is asynchronous and must never block PTT ingest, recording, playback or transcription.

The object namespace is tenant- and site-scoped:

`tenants/<tenant-id>/sites/<site-id>/<category>/<filename>`

Allowed categories:
- `config`
- `backups`
- `recordings`
- `transcripts`
- `media`
- `diagnostics`
- `releases`

## Credentials

Set these environment variables in the service's protected environment file. Do not put secrets in JSON configuration, backup manifests, logs, or Git:

| Variable | Purpose |
|---|---|
| `SANKET_S3_ENDPOINT` | S3 API endpoint URL |
| `SANKET_S3_REGION` | Region; use `auto` for R2 |
| `SANKET_S3_BUCKET` | Bucket name |
| `SANKET_S3_ACCESS_KEY_ID` | Access key |
| `SANKET_S3_SECRET_ACCESS_KEY` | Secret key |
| `SANKET_S3_ADDRESSING_STYLE` | Optional; defaults to `auto` |

For Cloudflare R2, the endpoint format is `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`. Create a dedicated bucket and a scoped API token for the Sanket service. Do not use an account-wide token.

## Install

From `sanket-broadcast/pi`:

    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt

The storage adapter is `sanket_broadcast/cloud_storage.py`. It provides connection checking, tenant/site-scoped object keys, upload, download with SHA-256 verification, and listing.

## Safety and current scope

- The adapter requests server-side AES-256 encryption for uploaded objects.
- Backup archives containing recordings or sensitive configuration must additionally be encrypted client-side before upload. Server-side encryption alone is not sufficient protection against a compromised cloud account.
- Credentials and private keys must never be included in exported backups.
- Downloads are written to a temporary file, verified, then atomically moved into place.
- Tenant and site identifiers are validated before constructing object keys.
- Cloud unavailability must leave local recording operational; a durable local upload queue, retry worker, backup manifest/restore orchestration, dashboard controls and full end-to-end tests are subsequent integration tasks.
- This first slice is not yet a complete cloud backup product and is not a production-ready installer. Test with a disposable bucket and non-critical sample files first.
