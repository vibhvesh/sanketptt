"""Control-room output: route one / selected / all channels, mix, duck lower priority, limit."""
import logging, threading, time
import numpy as np
log = logging.getLogger("mixer")
BLOCK = 480  # 40 ms @ 12 kHz

class Mixer:
    def __init__(self, cfg):
        self.cfg = cfg; self.lock = threading.Lock()
        self.bufs = {}      # (ch,sid) -> deque-ish np array
        self.active = {}    # ch -> last audio time
        self.gain = {}      # ch -> smoothed gain
        self.stream = None
    def routed(self, ch):
        o = self.cfg["output"]
        if o["mode"] == "off": return False
        return o["mode"] == "all" or (o["mode"] in ("single", "select") and ch in o["channels"])
    def feed(self, ch, sid, pcm):
        if not self.routed(ch): return
        with self.lock:
            b = self.bufs.get((ch, sid))
            self.bufs[(ch, sid)] = pcm.astype(np.float32) if b is None else np.concatenate([b, pcm.astype(np.float32)])[-12000 * 5:]
            self.active[ch] = time.time()
    def render(self, n=BLOCK):
        o = self.cfg["output"]; pr = self.cfg["priority"]; now = time.time()
        out = np.zeros(n, np.float32)
        with self.lock:
            live = [c for c, t in self.active.items() if now - t < 0.5]
            top = max([pr.get(c, 0) for c in live], default=0)
            duck = 10 ** (o["duck_db"] / 20)
            for key in list(self.bufs):
                ch = key[0]; b = self.bufs[key]
                target = 1.0 if pr.get(ch, 0) >= top else duck
                g = self.gain.get(ch, 1.0)
                g += (target - g) * (0.5 if target < g else 0.1)   # fast attack, slow release
                self.gain[ch] = g
                k = min(n, len(b)); out[:k] += b[:k] * g
                rest = b[k:]
                if len(rest): self.bufs[key] = rest
                else: del self.bufs[key]
        out *= o["volume"] / 32768.0
        return np.tanh(out * 1.2) / 1.2                    # soft limiter
    def start(self):
        if self.cfg["output"]["mode"] == "off":
            log.info("local audio output off (play recordings in the browser console)"); return
        try:
            import sounddevice as sd
        except Exception as e:
            log.warning("no audio output (%s); mixer disabled", e); return
        R = int(self.cfg["out_rate"]); src = self.cfg["rate"]; ratio = R / src
        self.tail = np.zeros(0, np.float32)
        def cb(outdata, frames, t, status):
            # render at 12 kHz, linear-resample to 48 kHz (most USB/HDMI/BT sinks reject 12k)
            need = int(round(frames / ratio))              # 48k/12k = exactly 4x, no drift
            x = np.concatenate([self.tail, self.render(need)])   # carry last sample for continuity
            pos = np.arange(frames) / ratio + (len(x) - need - 1 if len(self.tail) else 0)
            outdata[:, 0] = np.interp(pos, np.arange(len(x)), x).astype(np.float32)
            self.tail = x[-1:]
        try:
            self.stream = sd.OutputStream(samplerate=R, channels=1, blocksize=int(BLOCK * ratio),
                                          device=self.cfg["output"]["device"], callback=cb, latency="high")
            self.stream.start(); log.info("audio out started")
        except Exception as e:
            log.warning("audio out failed: %s", e)
