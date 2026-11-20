"""Shared helpers: logging ring, shell, WAV I/O, resampling, levels, keyword matching."""
import collections, logging, os, re, subprocess, wave
import numpy as np

log = logging.getLogger("sanket")
LOG_RING = collections.deque(maxlen=600)
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATE = 12000            # Sanket PTT relay audio rate (Int16LE mono)


class RingHandler(logging.Handler):
    def emit(self, r):
        LOG_RING.append(self.format(r))


def sh(cmd, t=10, inp=None):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=t, input=inp).stdout.strip()
    except Exception:
        return ""


def clean_ch(s):
    return re.sub(r"[^\w-]", "", str(s or "")).lower()[:40]


def write_wav(path, i16, rate=RATE):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(np.asarray(i16).astype("<i2").tobytes())


def read_wav(path):
    with wave.open(path, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").copy(), w.getframerate(), w.getnchannels()


def resample(x, src, dst):
    if src == dst or len(x) == 0:
        return np.asarray(x, np.float32)
    n = int(round(len(x) * dst / src))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def dbfs(i16):
    """RMS level of an int16 block in dBFS (-90 .. 0)."""
    if len(i16) == 0:
        return -90.0
    r = float(np.sqrt(np.mean((np.asarray(i16, np.float32) / 32768.0) ** 2)))
    return max(-90.0, 20 * np.log10(r + 1e-9))


def kw_find(kws, text):
    if not kws or not text:
        return []
    alt = "|".join(re.escape(k) for k in sorted(kws, key=len, reverse=True))
    r = re.compile(r"(?<![\w\u0900-\u097F])(" + alt + r")(?![\w\u0900-\u097F])", re.I | re.U)
    return sorted({m.group(1).lower() for m in r.finditer(text)})
