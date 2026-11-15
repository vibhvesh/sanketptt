"""Provider-independent S3-compatible object storage for Sanket Broadcast.

Credentials are read only from the process environment. Never put access keys in
configuration backups or commit them to source control.
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config


_ALLOWED = {"config", "backups", "recordings", "transcripts", "media",
            "diagnostics", "releases"}
_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class StorageError(RuntimeError):
    """A safe, operator-displayable storage error."""


def _segment(value: str, label: str) -> str:
    if not _SEGMENT.fullmatch(value) or value in {".", ".."}:
        raise ValueError(f"Invalid {label}: use letters, numbers, dot, dash or underscore")
    return value


@dataclass(frozen=True)
class StorageSettings:
    endpoint_url: str
    region: str
    bucket: str
    access_key_id: str
    secret_access_key: str
    addressing_style: str = "auto"

    @classmethod
    def from_env(cls) -> "StorageSettings":
        required = {
            "SANKET_S3_ENDPOINT": os.getenv("SANKET_S3_ENDPOINT", ""),
            "SANKET_S3_BUCKET": os.getenv("SANKET_S3_BUCKET", ""),
            "SANKET_S3_ACCESS_KEY_ID": os.getenv("SANKET_S3_ACCESS_KEY_ID", ""),
            "SANKET_S3_SECRET_ACCESS_KEY": os.getenv("SANKET_S3_SECRET_ACCESS_KEY", ""),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise StorageError("Cloud storage is not configured. Missing: " + ", ".join(missing))
        return cls(
            endpoint_url=required["SANKET_S3_ENDPOINT"],
            region=os.getenv("SANKET_S3_REGION", "auto"),
            bucket=required["SANKET_S3_BUCKET"],
            access_key_id=required["SANKET_S3_ACCESS_KEY_ID"],
            secret_access_key=required["SANKET_S3_SECRET_ACCESS_KEY"],
            addressing_style=os.getenv("SANKET_S3_ADDRESSING_STYLE", "auto"),
        )


class SanketObjectStorage:
    """S3 API adapter; supports R2 and other S3-compatible providers."""

    def __init__(self, settings: StorageSettings):
        self.settings = settings
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.endpoint_url,
            region_name=settings.region,
            aws_access_key_id=settings.access_key_id,
            aws_secret_access_key=settings.secret_access_key,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": settings.addressing_style},
                retries={"max_attempts": 5, "mode": "standard"},
                connect_timeout=10,
                read_timeout=60,
            ),
        )

    @classmethod
    def from_env(cls) -> "SanketObjectStorage":
        return cls(StorageSettings.from_env())

    @staticmethod
    def object_key(tenant: str, site: str, category: str, filename: str) -> str:
        tenant = _segment(tenant, "tenant")
        site = _segment(site, "site")
        if category not in _ALLOWED:
            raise ValueError(f"Unsupported storage category: {category}")
        name = Path(filename).name
        if not name or name in {".", ".."} or "\\x00" in name:
            raise ValueError("Invalid filename")
        # Do not allow caller-supplied path separators or traversal.
        if name != filename or "/" in filename or "\\" in filename:
            raise ValueError("Filename must be a single path component")
        return f"tenants/{tenant}/sites/{site}/{category}/{name}"

    def check_connection(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.settings.bucket)
            return True
        except Exception as exc:
            raise StorageError(f"Cloud storage connection check failed: {exc}") from exc

    def upload_file(self, local_path: str | Path, *, tenant: str, site: str,
                    category: str, filename: str | None = None) -> dict:
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        key = self.object_key(tenant, site, category, filename or path.name)
        digest = _sha256(path)
        try:
            self.client.upload_file(
                str(path), self.settings.bucket, key,
                ExtraArgs={
                    "ServerSideEncryption": "AES256",
                    "Metadata": {"sha256": digest, "tenant": tenant, "site": site,
                                 "category": category},
                },
            )
        except Exception as exc:
            raise StorageError(f"Upload failed for {key}: {exc}") from exc
        return {"bucket": self.settings.bucket, "key": key, "sha256": digest,
                "size_bytes": path.stat().st_size}

    def download_file(self, key: str, destination: str | Path,
                      *, expected_sha256: str | None = None) -> Path:
        # Only accept keys in the Sanket namespace.
        if not key.startswith("tenants/") or ".." in Path(key).parts:
            raise ValueError("Refusing object key outside the Sanket namespace")
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".sanket-download-", dir=target.parent)
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            self.client.download_file(self.settings.bucket, key, str(temp_path))
            actual = _sha256(temp_path)
            if expected_sha256 and actual.lower() != expected_sha256.lower():
                raise StorageError("Backup checksum mismatch; downloaded file was not installed")
            os.replace(temp_path, target)
            return target
        except Exception as exc:
            temp_path.unlink(missing_ok=True)
            if isinstance(exc, (StorageError, ValueError)):
                raise
            raise StorageError(f"Download failed for {key}: {exc}") from exc

    def list_objects(self, *, tenant: str, site: str, category: str,
                     limit: int = 100) -> list[dict]:
        if category not in _ALLOWED:
            raise ValueError(f"Unsupported storage category: {category}")
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        prefix = f"tenants/{_segment(tenant, 'tenant')}/sites/{_segment(site, 'site')}/{category}/"
        try:
            response = self.client.list_objects_v2(
                Bucket=self.settings.bucket, Prefix=prefix, MaxKeys=limit
            )
        except Exception as exc:
            raise StorageError(f"Could not list cloud objects: {exc}") from exc
        return [
            {"key": item["Key"], "size_bytes": item["Size"],
             "last_modified": item["LastModified"].isoformat()}
            for item in response.get("Contents", [])
        ]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
