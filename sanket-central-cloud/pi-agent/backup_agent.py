#!/usr/bin/env python3
"""Sanket Central Cloud Pi backup and staged-restore agent.

Secrets are supplied through a root-readable environment file. Backup paths are
explicitly allow-listed in JSON; credentials and private-key files are excluded.
Restore only extracts into a staging directory and never overwrites live data.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import requests

SECRET_PATTERNS = (
    ".env", "*.pem", "*.key", "id_rsa", "*secret*", "*token*", "*credential*",
    "authorized_keys", "known_hosts",
)
DEFAULT_EXCLUDES = ("*.sock", "*.pid", "*.lock", "*.tmp", "*.swp", "__pycache__")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_access_token() -> str:
    token = os.getenv("SANKET_ACCESS_TOKEN")
    if token:
        return token
    token_url = os.environ["SANKET_TOKEN_URL"]
    client_id = os.environ["SANKET_CLIENT_ID"]
    client_secret = os.environ["SANKET_CLIENT_SECRET"]
    response = requests.post(
        token_url,
        data={"grant_type": "client_credentials", "client_id": client_id,
              "client_secret": client_secret, "scope": "sanket.backup"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def api_session(base_url: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {get_access_token()}"})
    session.base_url = base_url.rstrip("/")  # type: ignore[attr-defined]
    return session


def iter_safe_files(source: Path, excludes: list[str]):
    source = source.expanduser().resolve(strict=True)
    if source.is_symlink() or not source.is_dir():
        raise ValueError(f"Backup source must be a real directory: {source}")
    for path in source.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(source).as_posix()
        parts = PurePosixPath(rel).parts
        if any(fnmatch.fnmatch(part.lower(), pattern.lower()) for part in parts
               for pattern in (*SECRET_PATTERNS, *DEFAULT_EXCLUDES, *excludes)):
            continue
        yield path, rel


def export_backup(config_path: Path, backup_type: str) -> None:
    config = json.loads(config_path.read_text())
    base_url = config["cloud_api"].rstrip("/")
    site_id, device_id = config["site_id"], config["device_id"]
    sources = config["sources"][backup_type]
    excludes = config.get("exclude_patterns", [])
    entries = []
    with tempfile.TemporaryDirectory(prefix="sanket-backup-") as tmp:
        archive = Path(tmp) / "sanket-backup.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for item in sources:
                root = Path(item["path"]).expanduser()
                label = item["archive_name"]
                for file_path, rel in iter_safe_files(root, excludes):
                    arcname = f"payload/{label}/{rel}"
                    zf.write(file_path, arcname)
                    entries.append({
                        "path": arcname,
                        "size_bytes": file_path.stat().st_size,
                        "sha256": sha256_file(file_path),
                    })
            manifest = {
                "format": "sanket-backup-v1",
                "backup_type": backup_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": {
                    "hostname": platform.node(),
                    "os": platform.platform(),
                    "architecture": platform.machine(),
                    "site_id": site_id,
                    "device_id": device_id,
                },
                "items": entries,
                "notes": [
                    "Credentials, private keys and files matching secret patterns are excluded.",
                    "Review application-specific configuration for embedded secrets before export.",
                    "This archive is a migration payload; it must be staged and validated before activation.",
                ],
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive_sha = sha256_file(archive)
        session = api_session(base_url)
        with archive.open("rb") as fh:
            response = session.post(
                f"{base_url}/v1/objects",
                data={"site_id": site_id, "device_id": device_id, "category": "backups"},
                files={"file": ("sanket-backup.zip", fh, "application/zip")},
                timeout=(30, 3600),
            )
        response.raise_for_status()
        obj = response.json()
        manifest["archive_sha256"] = archive_sha
        registered = session.post(
            f"{base_url}/v1/backups",
            json={"object_id": obj["id"], "backup_type": backup_type,
                  "source_device_id": device_id, "manifest": manifest},
            timeout=30,
        )
        registered.raise_for_status()
        print(json.dumps({"backup": registered.json(), "object": obj}, indent=2))


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            name = PurePosixPath(member.filename)
            if name.is_absolute() or ".." in name.parts:
                raise ValueError(f"Unsafe archive path: {member.filename}")
            target = (root / Path(*name.parts)).resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"Archive path escapes staging directory: {member.filename}")
        zf.extractall(root)


def restore_backup(config_path: Path, backup_id: str, staging_dir: Path) -> None:
    config = json.loads(config_path.read_text())
    base_url = config["cloud_api"].rstrip("/")
    session = api_session(base_url)
    response = session.get(f"{base_url}/v1/backups/{backup_id}/restore", timeout=30)
    response.raise_for_status()
    info = response.json()
    with tempfile.TemporaryDirectory(prefix="sanket-restore-") as tmp:
        archive = Path(tmp) / "restore.zip"
        with requests.get(info["download_url"], stream=True, timeout=(30, 600)) as download:
            download.raise_for_status()
            with archive.open("wb") as output:
                for chunk in download.iter_content(1024 * 1024):
                    if chunk:
                        output.write(chunk)
        actual = sha256_file(archive)
        if actual != info["sha256"]:
            raise ValueError("Backup SHA-256 does not match cloud catalogue; restore aborted")
        safe_extract(archive, staging_dir)
    print(json.dumps({
        "status": "staged_not_activated",
        "staging_directory": str(staging_dir.resolve()),
        "message": "Review manifest and hardware mappings. Do not copy into live paths until an operator approves.",
        "manifest": info.get("manifest", {}),
    }, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanket Central Cloud backup/restore agent")
    parser.add_argument("--config", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--type", choices=("config_clone", "full_migration", "scheduled", "disaster_recovery"), default="scheduled")
    restore = sub.add_parser("restore")
    restore.add_argument("--backup-id", required=True)
    restore.add_argument("--staging-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "export":
        export_backup(args.config, args.type)
    else:
        restore_backup(args.config, args.backup_id, args.staging_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
