"""Bluetooth speakers / mics through bluetoothctl: scan, list, pair, connect, disconnect, forget."""
import re, shutil, subprocess, threading
from .util import sh, log

MAC = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$", re.I)


def available():
    return bool(shutil.which("bluetoothctl"))


def _ctl(*args, t=20):
    return sh(["bluetoothctl", *args], t)


def devices():
    if not available():
        return dict(available=False, devices=[])
    out, paired = {}, {m for m in re.findall(r"Device (\S+)", _ctl("devices", "Paired"))}
    for line in _ctl("devices").splitlines():
        m = re.match(r"Device (\S+) (.*)", line)
        if m:
            out[m.group(1)] = dict(mac=m.group(1), name=m.group(2), paired=m.group(1) in paired)
    for mac, d in out.items():
        info = _ctl("info", mac, t=5)
        d["connected"] = "Connected: yes" in info
        d["trusted"] = "Trusted: yes" in info
        icon = re.search(r"Icon: (\S+)", info)
        d["icon"] = icon.group(1) if icon else ""
    powered = "Powered: yes" in _ctl("show", t=5)
    return dict(available=True, powered=powered, devices=sorted(out.values(), key=lambda d: (not d["paired"], d["name"])))


def scan(seconds=10):
    if not available():
        return {"ok": False, "error": "bluetoothctl not installed"}
    _ctl("power", "on", t=5)
    threading.Thread(target=lambda: _ctl("--timeout", str(int(seconds)), "scan", "on", t=seconds + 5), daemon=True).start()
    return {"ok": True, "seconds": seconds}


def action(act, mac):
    if not available():
        return {"ok": False, "error": "bluetoothctl not installed"}
    if not MAC.match(mac or ""):
        return {"ok": False, "error": "bad address"}
    seq = {"pair": [("pair", mac), ("trust", mac), ("connect", mac)], "connect": [("connect", mac)],
           "disconnect": [("disconnect", mac)], "forget": [("remove", mac)]}.get(act)
    if not seq:
        return {"ok": False, "error": "unknown action"}
    outs = []
    for a in seq:
        r = subprocess.run(["bluetoothctl", *a], capture_output=True, text=True, timeout=40)
        outs.append((r.stdout or r.stderr).strip().splitlines()[-1:] or [""])
    res = " / ".join(o[0] for o in outs)
    log.info("bluetooth %s %s: %s", act, mac, res)
    return {"ok": "fail" not in res.lower() and "not available" not in res.lower(), "result": res}
