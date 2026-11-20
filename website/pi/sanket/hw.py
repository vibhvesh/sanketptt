"""Hardware detection and per-model default profiles (Pi 5 / Pi 4 / Pi 3 / other)."""
import os, re

PROFILES = {
    "pi5":   dict(whisper_model="base", tts_engine="piper", sstv=True, sstv_decode=True, kiosk_browser="chromium"),
    "pi4":   dict(whisper_model="base", tts_engine="piper", sstv=True, sstv_decode=True, kiosk_browser="chromium"),
    "pi3":   dict(whisper_model="tiny", tts_engine="espeak-ng", sstv=False, sstv_decode=False, kiosk_browser="surf"),
    "other": dict(whisper_model="base", tts_engine="espeak-ng", sstv=True, sstv_decode=True, kiosk_browser="chromium"),
}


def model_string():
    for p in ("/proc/device-tree/model", "/sys/firmware/devicetree/base/model"):
        try:
            return open(p, "rb").read().decode(errors="ignore").strip("\x00 \n")
        except Exception:
            pass
    return os.environ.get("SANKET_MODEL", "")


def profile_key(model=None):
    m = (model if model is not None else model_string()).lower()
    if os.environ.get("SANKET_HW"):
        return os.environ["SANKET_HW"]
    g = re.search(r"raspberry pi (\d)", m)
    if g:
        return {"5": "pi5", "4": "pi4", "3": "pi3"}.get(g.group(1), "pi3" if g.group(1) < "3" else "other")
    if "zero 2" in m:
        return "pi3"
    return "other"


def info():
    m = model_string()
    return dict(model=m or "unknown (not a Raspberry Pi)", profile=profile_key(m), cpus=os.cpu_count(),
                watchdog=os.path.exists("/dev/watchdog"))
