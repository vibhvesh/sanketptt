#!/usr/bin/env python3
"""Preflight checks for supported Sanket Broadcast Raspberry Pi deployments."""
from __future__ import annotations

import json
import platform
import re
from pathlib import Path


def read_os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
    except OSError:
        pass
    return values


def read_model() -> str:
    for path in (Path("/proc/device-tree/model"), Path("/sys/firmware/devicetree/base/model")):
        try:
            return path.read_bytes().decode("utf-8", "replace").strip("\x00\n ")
        except OSError:
            pass
    return "unknown"


def inspect() -> dict:
    osr = read_os_release()
    version = osr.get("VERSION_ID", "")
    major_minor = tuple(int(x) for x in re.findall(r"\d+", version)[:2]) if version else ()
    model = read_model()
    is_pi5 = "raspberry pi 5" in model.casefold()
    is_arm64 = platform.machine() in {"aarch64", "arm64"}
    supported_ubuntu = osr.get("ID") == "ubuntu" and bool(major_minor) and major_minor[0] in (24, 26)
    return {
        "model": model,
        "architecture": platform.machine(),
        "os": osr.get("PRETTY_NAME", "unknown"),
        "os_version": version,
        "checks": {
            "raspberry_pi_5": is_pi5,
            "arm64": is_arm64,
            "ubuntu_24_or_26": supported_ubuntu,
        },
        "supported": is_pi5 and is_arm64 and supported_ubuntu,
        "recommendation": (
            "Ubuntu 26.04.1 LTS 64-bit is the preferred deployment baseline. "
            "Ubuntu 24.04 LTS 64-bit remains a compatibility target."
        ),
        "notes": [
            "For Ubuntu 26.04 on Pi 5, verify the boot EEPROM meets Canonical's minimum date (2025-02-11).",
            "Use Ubuntu Desktop when the Pi itself must show the graphical touchscreen cockpit.",
            "Use Ubuntu Server only when a browser/display session is not required locally.",
            "Hardware and audio support still require on-device driver discovery and playback tests.",
        ],
    }


if __name__ == "__main__":
    result = inspect()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["supported"] else 2)
