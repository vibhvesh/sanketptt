"""Offline speech-to-text with faster-whisper (loaded lazily, reloaded when the model setting changes)."""
import os, threading, time
import numpy as np
from .util import log, resample


class Transcriber:
    def __init__(self, cfg):
        self.cfg, self.model, self.name, self.state, self.lock = cfg, None, None, "off", threading.Lock()

    def ensure(self):
        if not self.cfg["transcribe"]:
            return None
        want = self.cfg["whisper_model"]
        with self.lock:
            if self.model and self.name == want:
                return self.model
            try:
                self.state = f"loading {want}"
                from faster_whisper import WhisperModel
                t = time.time()
                self.model = WhisperModel(want, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
                self.name, self.state = want, f"{want} ready"
                log.info("whisper '%s' loaded in %.1fs", want, time.time() - t)
            except Exception as e:
                self.model, self.state = None, f"error: {e}"; log.error("whisper load failed: %s", e)
            return self.model

    def __call__(self, i16, rate):
        """Returns (text, language, seconds) or None when transcription is off/unavailable."""
        m = self.ensure()
        if not m:
            return None
        t0 = time.time()
        lang = None if str(self.cfg["language"]).lower() in ("auto", "") else self.cfg["language"]
        segs, info = m.transcribe(resample(i16.astype(np.float32) / 32768, rate, 16000), language=lang,
                                  beam_size=1, vad_filter=False, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segs).strip(), info.language, round(time.time() - t0, 2)

    def status(self):
        return self.state if self.cfg["transcribe"] else "off"
