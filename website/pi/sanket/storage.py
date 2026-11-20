"""Recordings on disk: clip WAV + JSON metadata (+ SSTV image), the live feed and retention."""
import collections, datetime as dt, json, os, re, threading, time
from .util import write_wav


class Storage:
    def __init__(self, cfg):
        self.cfg = cfg
        self.dir = os.path.expanduser(cfg["clips_dir"]); os.makedirs(self.dir, exist_ok=True)
        self.tmp = os.path.join(self.dir, ".tmp"); os.makedirs(self.tmp, exist_ok=True)
        self.feed = collections.deque(maxlen=200); self.lock = threading.Lock()
        self.load()

    def base_for(self, t, channel, speaker):
        ts = dt.datetime.fromtimestamp(t)
        return os.path.join(self.dir, f"{ts:%Y%m%d_%H%M%S}_{channel}_{re.sub(r'[^A-Za-z0-9_-]', '_', speaker)[:24]}")

    def save_clip(self, base, i16, rate):
        write_wav(base + ".wav", i16, rate)

    def save_meta(self, base, meta):
        json.dump(meta, open(base + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    def add(self, meta):
        with self.lock:
            self.feed.appendleft(meta)

    def list(self, n=100):
        return list(self.feed)[:n]

    def clear(self):
        self.feed.clear()

    def path(self, name):
        f = os.path.basename(name or "")
        p = os.path.join(self.dir, f)
        return p if f and os.path.isfile(p) else None

    def load(self):
        try:
            for f in sorted((x for x in os.listdir(self.dir) if x.endswith(".json")), reverse=True)[:100]:
                try:
                    self.feed.append(json.load(open(os.path.join(self.dir, f), encoding="utf-8")))
                except Exception:
                    pass
        except Exception:
            pass

    def purge(self):
        cut = time.time() - float(self.cfg["retention_days"]) * 86400
        for d in (self.dir, self.tmp):
            for f in os.listdir(d):
                p = os.path.join(d, f)
                if os.path.isfile(p) and not f.endswith(".log") and os.path.getmtime(p) < (cut if d == self.dir else time.time() - 3600):
                    os.remove(p)

    def usage(self):
        n = b = 0
        for f in os.listdir(self.dir):
            p = os.path.join(self.dir, f)
            if os.path.isfile(p):
                n += f.endswith(".wav"); b += os.path.getsize(p)
        return dict(clips=n, bytes=b, dir=self.dir)
