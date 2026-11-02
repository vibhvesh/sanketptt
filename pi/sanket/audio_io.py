"""Audio devices: list outputs/inputs (ALSA cards, 3.5 mm jack, HDMI, USB, PipeWire/Pulse sinks incl. Bluetooth),
play a WAV on the chosen output, and open a raw capture stream from a chosen input."""
import os, re, shutil, subprocess, time, wave
import numpy as np
from .util import sh, log, read_wav, dbfs


def _kind(text):
    t = text.lower()
    if "bluez" in t or "bluetooth" in t: return "bluetooth"
    if "hdmi" in t or "vc4hdmi" in t: return "hdmi"
    if "headphones" in t or "bcm2835" in t or "analog" in t: return "jack"
    if "usb" in t: return "usb"
    return "other"


def have_pulse():
    return bool(shutil.which("pactl")) and sh(["pactl", "info"], 4) != ""


_cache = {}


def cached(fn, ttl=15):
    def w():
        t, v = _cache.get(fn.__name__, (0, None))
        if time.time() - t > ttl or v is None:
            v = fn(); _cache[fn.__name__] = (time.time(), v)
        return v
    w.refresh = lambda: _cache.pop(fn.__name__, None)
    return w


def output_devices():
    devs = [{"id": "default", "label": "System default (ALSA / PipeWire)", "kind": "default"}]
    for line in sh(["aplay", "-l"]).splitlines():
        m = re.match(r"card (\d+): (\S+) \[(.*?)\], device (\d+): .*?\[(.*?)\]", line)
        if m:
            label = f"{m.group(3)} - {m.group(5)}"
            k = _kind(m.group(2) + " " + label)
            nice = {"jack": "3.5 mm jack", "hdmi": "HDMI", "usb": "USB sound card"}.get(k, "Sound card")
            devs.append({"id": f"plughw:CARD={m.group(2)},DEV={m.group(4)}", "label": f"{nice}: {label}", "kind": k})
    if have_pulse():
        for line in sh(["pactl", "list", "short", "sinks"]).splitlines():
            p = line.split("\t")
            if len(p) >= 2:
                k = _kind(p[1])
                devs.append({"id": "pulse:" + p[1], "label": ("Bluetooth speaker: " if k == "bluetooth" else "PipeWire: ") + p[1], "kind": k})
    return devs


def input_devices():
    devs = [{"id": "default", "label": "System default mic", "kind": "default"}]
    for line in sh(["arecord", "-l"]).splitlines():
        m = re.match(r"card (\d+): (\S+) \[(.*?)\], device (\d+): .*?\[(.*?)\]", line)
        if m:
            k = _kind(m.group(2) + " " + m.group(3))
            devs.append({"id": f"plughw:CARD={m.group(2)},DEV={m.group(4)}",
                         "label": ("USB mic / sound card: " if k == "usb" else "Mic: ") + f"{m.group(3)} - {m.group(5)}", "kind": k})
    if have_pulse():
        for line in sh(["pactl", "list", "short", "sources"]).splitlines():
            p = line.split("\t")
            if len(p) >= 2 and not p[1].endswith(".monitor"):
                k = _kind(p[1])
                devs.append({"id": "pulse:" + p[1], "label": ("Bluetooth mic: " if k == "bluetooth" else "PipeWire mic: ") + p[1], "kind": k})
    return devs


output_devices_cached = cached(output_devices)


def play_cmd(device, path):
    device = device or "default"
    if device.startswith("pulse:"):
        exe = shutil.which("paplay") or shutil.which("pw-play")
        if exe:
            return [exe, "--device=" + device[6:], path] if exe.endswith("paplay") else [exe, "--target", device[6:], path]
        device = "default"
    return ["aplay", "-q", "-D", device, path]


class Player:
    """Plays a WAV at the configured volume on the configured output. Reports output level."""
    def __init__(self, cfg, tmp, metrics=None):
        self.cfg, self.tmp, self.metrics = cfg, tmp, metrics
        self.dry = os.environ.get("SANKET_DRY_AUDIO") == "1"
        self.last = []

    def play(self, path):
        vol = max(0, min(150, int(self.cfg["volume"]))) / 100.0
        i16, rate, nch = read_wav(path)
        x = np.clip(i16.astype(np.float32) * vol, -32768, 32767).astype(np.int16)
        if self.metrics:
            self.metrics.level("out", dbfs(x))
        out = os.path.join(self.tmp, "out_" + os.path.basename(path))
        with wave.open(out, "wb") as w:
            w.setnchannels(nch); w.setsampwidth(2); w.setframerate(rate); w.writeframes(x.tobytes())
        self.last.append(out); self.last = self.last[-10:]
        if self.dry or not shutil.which("aplay"):
            log.info("[audio] %s -> %s", os.path.basename(out), self.cfg["audio_device"]); return
        cmd = play_cmd(self.cfg["audio_device"], out)
        r = subprocess.run(cmd, capture_output=True, timeout=180)
        if r.returncode:
            log.error("playback failed on '%s': %s", self.cfg["audio_device"], r.stderr.decode(errors="ignore").strip())


def capture_cmd(device, rate):
    device = device or "default"
    if device.startswith("pulse:"):
        if shutil.which("parec"):
            return ["parec", "--device=" + device[6:], "--format=s16le", f"--rate={rate}", "--channels=1", "--latency-msec=100"]
        device = "default"
    return ["arecord", "-q", "-D", device, "-f", "S16_LE", "-r", str(rate), "-c", "1", "-t", "raw"]
