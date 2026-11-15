from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Annotated

import boto3
import jwt
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

APP_NAME = "Sanket Central Cloud"
BUCKET = os.environ["R2_BUCKET"]
ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
R2_ENDPOINT = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024**3)))
JWT_ISSUER = os.environ["JWT_ISSUER"]
JWT_AUDIENCE = os.environ["JWT_AUDIENCE"]
JWKS_URL = os.environ["JWKS_URL"]
DATABASE_URL = os.environ["DATABASE_URL"]

pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=10, kwargs={"row_factory": dict_row}, open=False)
s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    region_name="auto",
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
)
jwks = PyJWKClient(JWKS_URL)
bearer = HTTPBearer(auto_error=True)
app = FastAPI(title=APP_NAME, version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    pool.open(wait=True)


@app.on_event("shutdown")
def shutdown() -> None:
    pool.close()


def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> dict:
    try:
        signing_key = jwks.get_signing_key_from_jwt(credentials.credentials).key
        claims = jwt.decode(
            credentials.credentials,
            signing_key,
            algorithms=["RS256", "ES256"],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        tenant_id = str(uuid.UUID(str(claims["tenant_id"])))
        return {
            "tenant_id": tenant_id,
            "subject": str(claims["sub"]),
            "roles": claims.get("roles", []),
        }
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc


def tenant_connection(principal: dict):
    conn = pool.getconn()
    try:
        with conn.transaction():
            conn.execute("SELECT set_config('app.tenant_id', %s, true)", (principal["tenant_id"],))
            yield conn
    finally:
        pool.putconn(conn)


def require_admin(principal: dict) -> None:
    if "sanket_admin" not in principal["roles"] and "tenant_admin" not in principal["roles"]:
        raise HTTPException(status_code=403, detail="Tenant administrator role required")


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    external_ref: str | None = Field(default=None, max_length=120)


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    device_type: str = Field(default="raspberry_pi", max_length=40)
    software_version: str | None = Field(default=None, max_length=80)


class BackupCreate(BaseModel):
    object_id: uuid.UUID
    backup_type: str = Field(pattern="^(config_clone|full_migration|disaster_recovery|scheduled)$")
    source_device_id: uuid.UUID
    manifest: dict


ALLOWED_CATEGORIES = {
    "recordings", "transcripts", "backups", "images", "diagnostics",
    "screenshots", "exports", "releases",
}


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": APP_NAME, "time": datetime.now(timezone.utc).isoformat()}


@app.post("/v1/sites")
def create_site(body: SiteCreate, principal: dict = Depends(current_principal)):
    require_admin(principal)
    with tenant_connection(principal) as conn:
        row = conn.execute(
            "INSERT INTO sites (tenant_id, name, external_ref) VALUES (%s,%s,%s) RETURNING id,name,external_ref,created_at",
            (principal["tenant_id"], body.name, body.external_ref),
        ).fetchone()
        return row


@app.post("/v1/sites/{site_id}/devices")
def register_device(site_id: uuid.UUID, body: DeviceCreate, principal: dict = Depends(current_principal)):
    require_admin(principal)
    with tenant_connection(principal) as conn:
        site = conn.execute("SELECT id FROM sites WHERE id=%s", (site_id,)).fetchone()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        row = conn.execute(
            "INSERT INTO devices (tenant_id,site_id,name,device_type,software_version) VALUES (%s,%s,%s,%s,%s) RETURNING id,site_id,name,device_type,software_version,created_at",
            (principal["tenant_id"], site_id, body.name, body.device_type, body.software_version),
        ).fetchone()
        return row


@app.post("/v1/objects", status_code=201)
def upload_object(
    site_id: Annotated[uuid.UUID, Form()],
    device_id: Annotated[uuid.UUID, Form()],
    category: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    principal: dict = Depends(current_principal),
):
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Unsupported object category")
    with tenant_connection(principal) as conn:
        device = conn.execute(
            "SELECT id FROM devices WHERE id=%s AND site_id=%s",
            (device_id, site_id),
        ).fetchone()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found in this tenant/site")

        digest = hashlib.sha256()
        size = 0
        file.file.seek(0)
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Upload exceeds configured size limit")
            digest.update(chunk)
        sha256 = digest.hexdigest()
        file.file.seek(0)
        object_id = uuid.uuid4()
        key = f"tenants/{principal['tenant_id']}/sites/{site_id}/devices/{device_id}/{category}/{object_id}"
        s3.upload_fileobj(
            file.file,
            BUCKET,
            key,
            ExtraArgs={
                "ContentType": file.content_type or "application/octet-stream",
                "Metadata": {
                    "tenant-id": principal["tenant_id"],
                    "object-id": str(object_id),
                    "sha256": sha256,
                },
            },
        )
        row = conn.execute(
            """INSERT INTO stored_objects
               (id,tenant_id,site_id,device_id,category,object_key,file_name,content_type,size_bytes,sha256,uploaded_by)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING id,category,file_name,size_bytes,sha256,created_at""",
            (object_id, principal["tenant_id"], site_id, device_id, category, key,
             file.filename or "upload.bin", file.content_type or "application/octet-stream",
             size, sha256, principal["subject"]),
        ).fetchone()
        return row


@app.get("/v1/objects")
def list_objects(
    category: str | None = None,
    site_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    limit: int = 100,
    principal: dict = Depends(current_principal),
):
    limit = min(max(limit, 1), 500)
    with tenant_connection(principal) as conn:
        rows = conn.execute(
            """SELECT id,site_id,device_id,category,file_name,content_type,size_bytes,sha256,created_at
               FROM stored_objects
               WHERE (%s IS NULL OR category=%s)
                 AND (%s IS NULL OR site_id=%s)
                 AND (%s IS NULL OR device_id=%s)
               ORDER BY created_at DESC LIMIT %s""",
            (category, category, site_id, site_id, device_id, device_id, limit),
        ).fetchall()
        return {"items": rows}


@app.get("/v1/objects/{object_id}/download")
def download_object(object_id: uuid.UUID, principal: dict = Depends(current_principal)):
    with tenant_connection(principal) as conn:
        row = conn.execute("SELECT object_key,file_name FROM stored_objects WHERE id=%s", (object_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Object not found")
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": row["object_key"], "ResponseContentDisposition": f'attachment; filename="{row["file_name"]}"'},
            ExpiresIn=300,
        )
        return {"download_url": url, "expires_in": 300}


@app.post("/v1/backups", status_code=201)
def register_backup(body: BackupCreate, principal: dict = Depends(current_principal)):
    with tenant_connection(principal) as conn:
        obj = conn.execute(
            "SELECT id,site_id,device_id,category,size_bytes,sha256 FROM stored_objects WHERE id=%s AND category='backups'",
            (body.object_id,),
        ).fetchone()
        if not obj:
            raise HTTPException(status_code=404, detail="Backup archive not found")
        source = conn.execute(
            "SELECT id FROM devices WHERE id=%s AND site_id=%s",
            (body.source_device_id, obj["site_id"]),
        ).fetchone()
        if not source:
            raise HTTPException(status_code=400, detail="Backup source device does not match archive site")
        row = conn.execute(
            """INSERT INTO backups (tenant_id,site_id,source_device_id,object_id,backup_type,manifest,sha256,size_bytes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING id,backup_type,sha256,size_bytes,created_at""",
            (principal["tenant_id"], obj["site_id"], body.source_device_id, body.object_id,
             body.backup_type, body.manifest, obj["sha256"], obj["size_bytes"]),
        ).fetchone()
        return row


@app.get("/v1/backups")
def list_backups(
    site_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    limit: int = 100,
    principal: dict = Depends(current_principal),
):
    limit = min(max(limit, 1), 500)
    with tenant_connection(principal) as conn:
        rows = conn.execute(
            """SELECT id,site_id,source_device_id,object_id,backup_type,sha256,size_bytes,created_at
               FROM backups WHERE (%s IS NULL OR site_id=%s)
               AND (%s IS NULL OR source_device_id=%s)
               ORDER BY created_at DESC LIMIT %s""",
            (site_id, site_id, device_id, device_id, limit),
        ).fetchall()
        return {"items": rows}


@app.get("/v1/backups/{backup_id}/restore")
def get_restore_package(backup_id: uuid.UUID, principal: dict = Depends(current_principal)):
    with tenant_connection(principal) as conn:
        row = conn.execute(
            """SELECT o.object_key,o.file_name,b.sha256,b.manifest
               FROM backups b JOIN stored_objects o ON o.id=b.object_id
               WHERE b.id=%s""",
            (backup_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Backup not found")
        url = s3.generate_presigned_url(
            "get_object", Params={"Bucket": BUCKET, "Key": row["object_key"]}, ExpiresIn=300
        )
        return {"download_url": url, "expires_in": 300, "sha256": row["sha256"], "manifest": row["manifest"]}


@app.get("/v1/storage/summary")
def storage_summary(principal: dict = Depends(current_principal)):
    with tenant_connection(principal) as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS object_count, COALESCE(SUM(size_bytes),0) AS bytes_used,
                      COUNT(*) FILTER (WHERE category='backups') AS backup_count
               FROM stored_objects"""
        ).fetchone()
        return row
