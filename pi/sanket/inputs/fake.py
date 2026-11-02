"""Fake input for testing: synthesises a burst (tone + noise, or a WAV file) every few seconds through the real VOX."""
import time
import numpy as np
from .registry import InputBase, register
from .vox import Vox
from ..util import read_wav, resample

RATE = 16000


@register
class FakeInput(InputBase):
    TYPE, LABEL, LOCAL = "fake", "Test signal (fake input)", True
    FIELDS = [dict(k="name", label="Name", type="text"), dict(k="file", label="WAV file (optional)", type="text"),
              dict(k="interval_s", label="Every (s)", type="number", min=1, max=600, step=1),
              dict(k="vox_threshold", label="VOX threshold (dBFS)", type="range", min=-70, max=-5, step=1)]

    def burst(self):
        f = self.spec.get("file")
        if f:
            i16, r, _ = read_wav(f)
            return resample(i16, r, RATE).astype(np.int16)
        t = np.arange(int(RATE * 1.5)) / RATE
        return (0.3 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

    def run(self):
        vox = Vox(RATE, self.spec.get("vox_threshold", -40), 0.5, 0.4, self.spec.get("max_clip_s", 60))
        every = float(self.spec.get("interval_s") or 5)
        sig = self.burst(); quiet = np.zeros(int(RATE * every), np.int16)
        stream = np.concatenate([quiet[: RATE], sig, quiet])
        blk = RATE // 10
        while not self.stop_ev.is_set():
            for i in range(0, len(stream) - blk, blk):
                if self.stop_ev.is_set():
                    return
                x = stream[i:i + blk]
                if self.spec.get("noise", True):
                    x = (x + np.random.normal(0, 30, blk)).astype(np.int16)
                db, clip = vox.feed(x); self.set_level(db)
                if clip is not None:
                    self.emit(clip, RATE)
                time.sleep(float(self.spec.get("speed", 0.1)) if "speed" in self.spec else 0.1)
