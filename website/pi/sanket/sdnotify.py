"""Minimal systemd notify (READY / WATCHDOG) without extra packages."""
import os, socket


def notify(msg):
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return False
    if addr[0] == "@":
        addr = "\0" + addr[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.connect(addr); s.sendall(msg.encode())
        return True
    except Exception:
        return False
