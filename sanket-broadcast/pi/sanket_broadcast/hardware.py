"""Read-only hardware inventory for the Sanket Broadcast operator cockpit.

This module reports what Linux can actually see. It does not download or install
vendor drivers, and it never treats a USB audio device as ready until a later
playback self-test has succeeded.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _run(argv: list[str], timeout: float = 3.0) -> dict[str, Any]:
    exe = shutil.which(argv[0])
    if not exe:
        return {"available": False, "error": f"{argv[0]} not installed"}
    try:
        p = subprocess.run([exe, *argv[1:]], capture_output=True, text=True,
                           timeout=timeout, check=False)
        return {"available": True, "returncode": p.returncode,
                "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": str(exc)}


def _os_release() -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                result[k] = v.strip().strip('"')
    except OSError:
        pass
    return result


def _pi_model() -> str:
    for candidate in (Path("/proc/device-tree/model"), Path("/sys/firmware/devicetree/base/model")):
        try:
            return candidate.read_bytes().decode("utf-8", "replace").strip("\x00\n ")
        except OSError:
            continue
    return "Unknown (device-tree model unavailable)"


def _alsa_cards() -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    try:
        for line in Path("/proc/asound/cards").read_text().splitlines():
            # Typical format: " 2 [Device         ]: USB-Audio - USB Audio"
            m = re.match(r"\s*(\d+)\s+\[([^]]+)\]:\s*(.*)", line)
            if m:
                cards.append({"card_index": m.group(1), "card_id": m.group(2),
                              "description": m.group(3).strip()})
    except OSError:
        pass
    return cards


def _sounddevice_outputs() -> dict[str, Any]:
    try:
        import sounddevice as sd  # type: ignore
        hostapis = sd.query_hostapis()
        outputs = []
        for index, dev in enumerate(sd.query_devices()):
            count = int(dev.get("max_output_channels", 0))
            if count <= 0:
                continue
            host_index = int(dev.get("hostapi", 0))
            host = hostapis[host_index] if 0 <= host_index < len(hostapis) else {}
            outputs.append({
                "runtime_index": index,
                "name": str(dev.get("name", "Unknown")),
                "hostapi": str(host.get("name", "Unknown")),
                "max_output_channels": count,
                "default_samplerate": float(dev.get("default_samplerate", 0)),
                "ready": False,
                "readiness_note": "Detected only; run an output test before marking ready",
            })
        return {"available": True, "outputs": outputs}
    except Exception as exc:  # PortAudio may fail if ALSA is unavailable
        return {"available": False, "outputs": [], "error": str(exc)}


def _display() -> dict[str, Any]:
    env = {k: os.environ.get(k) for k in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_SESSION_TYPE")}
    xrandr = _run(["xrandr", "--query"])
    connected = []
    if xrandr.get("returncode") == 0:
        for line in xrandr["stdout"].splitlines():
            if " connected" in line:
                connected.append(line.strip())
    return {"session": env, "xrandr": xrandr, "connected_outputs": connected}


def collect_hardware_inventory() -> dict[str, Any]:
    """Return a JSON-serializable snapshot for the dashboard and support bundle."""
    os_info = _os_release()
    mem = _run(["bash", "-lc", "awk '/MemTotal/ {print $2}' /proc/meminfo"])
    disk = shutil.disk_usage("/")
    temp = None
    for p in (Path("/sys/class/thermal/thermal_zone0/temp"),):
        try:
            temp = int(p.read_text().strip()) / 1000.0
            break
        except (OSError, ValueError):
            pass

    usb = _run(["lsusb"])
    eeprom = _run(["rpi-eeprom-update"])
    vcgencmd = _run(["vcgencmd", "get_throttled"])
    throttled = vcgencmd.get("stdout", "")
    return {
        "system": {
            "model": _pi_model(),
            "architecture": platform.machine(),
            "kernel": platform.release(),
            "hostname": platform.node(),
            "os": os_info.get("PRETTY_NAME", "Unknown"),
            "os_id": os_info.get("ID", ""),
            "os_version_id": os_info.get("VERSION_ID", ""),
            "ubuntu_supported_baseline": os_info.get("ID") == "ubuntu" and
                os_info.get("VERSION_ID", "").split(".")[0] in {"24", "26"},
            "memory_total_kib": int(mem.get("stdout") or 0) if mem.get("returncode") == 0 else None,
            "root_disk_total_bytes": disk.total,
            "root_disk_free_bytes": disk.free,
            "temperature_c": temp,
            "throttling_raw": throttled or None,
            "throttling_warning": bool(throttled and not throttled.endswith("=0x0")),
            "eeprom": eeprom,
        },
        "usb": usb,
        "alsa_cards": _alsa_cards(),
        "audio": _sounddevice_outputs(),
        "display": _display(),
        "tools": {name: bool(shutil.which(name)) for name in
                  ("aplay", "arecord", "alsamixer", "lsusb", "xrandr", "libinput")},
        "notes": [
            "Detected does not mean playback-tested; run a test tone for each output.",
            "Use class-compliant USB Audio devices where possible; do not install random vendor drivers.",
            "USB audio device indexes can change after reboot. Persist stable identity and physical USB path instead.",
            "Four independent USB DAC clocks may drift; long-duration synchronization testing is required.",
        ],
    }
