#!/usr/bin/env python3
"""Sanket PTT - Raspberry Pi receive-only listener (entry point).
The code lives in the sanket/ package (one module per concern). This file stays so that the
systemd unit and the v2 in-app updater keep working: if the package is missing (an old updater only
fetched this file) it downloads the files listed in files.txt first."""
import os, sys, urllib.request, time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_RAW = "https://vibhvesh.github.io/sanketptt/pi"
sys.path.insert(0, APP_DIR)


def bootstrap():
    man = urllib.request.urlopen(f"{REPO_RAW}/files.txt?t={int(time.time())}", timeout=30).read().decode()
    for f in [l.strip() for l in man.splitlines() if l.strip() and not l.startswith("#")]:
        dst = os.path.join(APP_DIR, f)
        if f == "sanket_pi.py":
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        data = urllib.request.urlopen(f"{REPO_RAW}/{f}?t={int(time.time())}", timeout=30).read()
        open(dst + ".new", "wb").write(data); os.replace(dst + ".new", dst)


if not os.path.exists(os.path.join(APP_DIR, "sanket", "app.py")):
    print("sanket package missing - fetching modules", flush=True)
    bootstrap()

from sanket.app import main  # noqa: E402

if __name__ == "__main__":
    main()
