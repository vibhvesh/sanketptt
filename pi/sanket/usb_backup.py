"""USB-only encrypted backup and migration for Sanket Edge."""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import uuid

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = "SanketBackups"
ALLOWED_ROOTS = ("/media/", "/run/media/", "/mnt/")


def usb_mounts():
    found = []
    try:
        with open("/proc/mounts", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 3:
                    continue
                mount = parts[1].replace("\\040", " ")
                if not mount.startswith(ALLOWED_ROOTS) or not os.path.isdir(mount) or not os.access(mount, os.W_OK):
                    continue
                if mount not in ("/media", "/mnt", "/run/media"):
                    found.append({"path": mount, "label": os.path.basename(mount.rstrip("/")) or "USB"})
    except OSError:
        pass
    return sorted(found, key=lambda x: x["path"])


def _safe_mount(path):
    real = os.path.realpath(path or "")
    if not any(real.startswith(root) for root in ALLOWED_ROOTS) or real not in [x["path"] for x in usb_mounts()]:
        raise ValueError("Select a mounted, writable USB drive")
    return real


def status():
    return {"usb": usb_mounts(), "openssl": bool(shutil.which("openssl")),
            "host": subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()}


def list_backups(mount):
    root = os.path.join(_safe_mount(mount), BACKUP_DIR)
    if not os.path.isdir(root):
        return []
    out = []
    for name in sorted(os.listdir(root), reverse=True):
        if re.fullmatch(r"sanket-[0-9]{8}-[0-9]{6}\.tar\.gz\.enc", name):
            p = os.path.join(root, name)
            if os.path.isfile(p):
                out.append({"name": name, "bytes": os.path.getsize(p), "modified": int(os.path.getmtime(p))})
    return out


def create(mount, passphrase, include_recordings=True, include_voices=True):
    if not passphrase or len(passphrase) < 10:
        raise ValueError("Use a backup passphrase of at least 10 characters")
    if not shutil.which("openssl"):
        raise RuntimeError("OpenSSL is required; install it with: sudo apt install openssl")
    usb = _safe_mount(mount)
    target_dir = os.path.join(usb, BACKUP_DIR)
    os.makedirs(target_dir, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"sanket-{stamp}.tar.gz.enc"
    final = os.path.join(target_dir, name)
    temp_tar = tempfile.NamedTemporaryFile(prefix="sanket-backup-", suffix=".tar.gz", delete=False)
    temp_tar.close()
    temp_enc = final + ".tmp"
    manifest = {"format": 1, "created": dt.datetime.now().isoformat(timespec="seconds"),
                "hostname": subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip(),
                "software": "Sanket Edge", "includes_recordings": bool(include_recordings),
                "includes_voices": bool(include_voices)}
    try:
        with tarfile.open(temp_tar.name, "w:gz") as tar:
            cfg = os.path.join(os.path.expanduser("~"), "sanket-pi", "config.json")
            if not os.path.isfile(cfg):
                raise RuntimeError("Sanket config.json was not found")
            tar.add(cfg, arcname="config.json")
            data = json.dumps(manifest, indent=2).encode()
            info = tarfile.TarInfo("manifest.json"); info.size = len(data)
            import io
            tar.addfile(info, io.BytesIO(data))
            if include_recordings:
                clips = os.path.expanduser("~/sanket_clips")
                if os.path.isdir(clips):
                    tar.add(clips, arcname="sanket_clips")
            if include_voices:
                voices = os.path.join(os.path.expanduser("~"), "sanket-pi", "voices")
                if os.path.isdir(voices):
                    tar.add(voices, arcname="voices")
        # Passphrase is sent over stdin, never exposed in process arguments.
        with open(temp_tar.name, "rb") as src, open(temp_enc, "wb") as out:
            proc = subprocess.Popen(["openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2", "-iter", "200000",
                                     "-pass", "stdin"], stdin=subprocess.PIPE, stdout=out, stderr=subprocess.PIPE)
            # OpenSSL reads the passphrase first; feed it, then archive bytes.
            proc.stdin.write((passphrase + "\\n").encode())
            shutil.copyfileobj(src, proc.stdin)
            proc.stdin.close()
            err = proc.stderr.read()
            if proc.wait() != 0:
                raise RuntimeError(err.decode(errors="replace") or "OpenSSL encryption failed")
        os.replace(temp_enc, final)
        return {"ok": True, "name": name, "bytes": os.path.getsize(final), "manifest": manifest}
    finally:
        for p in (temp_tar.name, temp_enc):
            try:
                os.remove(p)
            except OSError:
                pass


def restore(mount, name, passphrase, hostname):
    if not passphrase:
        raise ValueError("Backup passphrase is required")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,61}[A-Za-z0-9]", hostname or ""):
        raise ValueError("Hostname must be 2–63 characters: letters, numbers and hyphens")
    if not re.fullmatch(r"sanket-[0-9]{8}-[0-9]{6}\\.tar\\.gz\\.enc", name or ""):
        raise ValueError("Invalid backup filename")
    usb = _safe_mount(mount)
    source = os.path.join(usb, BACKUP_DIR, name)
    if not os.path.isfile(source):
        raise ValueError("Backup file not found on selected USB drive")
    stage = tempfile.mkdtemp(prefix="sanket-restore-")
    decrypted = os.path.join(stage, "backup.tar.gz")
    try:
        with open(source, "rb") as src, open(decrypted, "wb") as out:
            proc = subprocess.Popen(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000",
                                     "-pass", "stdin"], stdin=subprocess.PIPE, stdout=out, stderr=subprocess.PIPE)
            proc.stdin.write((passphrase + "\\n").encode())
            shutil.copyfileobj(src, proc.stdin); proc.stdin.close()
            err = proc.stderr.read()
            if proc.wait() != 0:
                raise ValueError("Could not decrypt backup. Check the passphrase and file.")
        with tarfile.open(decrypted, "r:gz") as tar:
            members = tar.getmembers()
            allowed = {"config.json", "manifest.json", "sanket_clips", "voices"}
            for member in members:
                normalized = os.path.normpath(member.name)
                if normalized.startswith("..") or os.path.isabs(member.name):
                    raise ValueError("Backup contains an unsafe file path")
                if member.name not in allowed and not member.name.startswith(("sanket_clips/", "voices/")):
                    raise ValueError("Backup contains an unexpected file path")
                if member.issym() or member.islnk() or member.isdev():
                    raise ValueError("Backup contains unsupported links or device files")
            tar.extractall(stage, members=members)
        manifest = json.load(open(os.path.join(stage, "manifest.json"), encoding="utf-8"))
        if manifest.get("format") != 1 or not os.path.isfile(os.path.join(stage, "config.json")):
            raise ValueError("Unsupported or incomplete Sanket backup")
        home = os.path.expanduser("~")
        app = os.path.join(home, "sanket-pi")
        shutil.copy2(os.path.join(stage, "config.json"), os.path.join(app, "config.json"))
        clips_src = os.path.join(stage, "sanket_clips")
        if os.path.isdir(clips_src):
            dest = os.path.join(home, "sanket_clips")
            os.makedirs(dest, exist_ok=True)
            shutil.copytree(clips_src, dest, dirs_exist_ok=True)
        voices_src = os.path.join(stage, "voices")
        if os.path.isdir(voices_src):
            dest = os.path.join(app, "voices")
            os.makedirs(dest, exist_ok=True)
            shutil.copytree(voices_src, dest, dirs_exist_ok=True)
        cfg_path = os.path.join(app, "config.json")
        cfg = json.load(open(cfg_path, encoding="utf-8"))
        cfg["device_name"] = hostname
        with open(cfg_path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
        os.replace(cfg_path + ".tmp", cfg_path)
        subprocess.run(["sudo", "-n", "hostnamectl", "set-hostname", hostname], check=True, capture_output=True)
        return {"ok": True, "hostname": hostname, "manifest": manifest,
                "message": "Restore complete. Restart Sanket to apply the restored settings."}
    finally:
        shutil.rmtree(stage, ignore_errors=True)
