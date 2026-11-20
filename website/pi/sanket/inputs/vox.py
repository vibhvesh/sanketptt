"""VOX: voice-operated switch that cuts a continuous stream into clips (adjustable dBFS threshold, hang time)."""
import collections
import numpy as np
from ..util import dbfs


class Vox:
    def __init__(self, rate, threshold_db=-40.0, hang_s=1.2, min_s=0.6, max_s=60.0, preroll_s=0.3):
        self.rate, self.th, self.hang, self.min, self.max = rate, threshold_db, hang_s, min_s, max_s
        self.pre = collections.deque(maxlen=max(1, int(preroll_s * 10)))
        self.buf, self.n, self.quiet, self.active = [], 0, 0.0, False

    def feed(self, block):
        """Feed ~100 ms int16 blocks. Returns (level_db, finished_clip_or_None)."""
        db = dbfs(block); dur = len(block) / self.rate; out = None
        if not self.active:
            self.pre.append(block)
            if db >= self.th:
                self.active, self.buf, self.n, self.quiet = True, list(self.pre), sum(len(b) for b in self.pre), 0.0
                self.pre.clear()
        else:
            self.buf.append(block); self.n += len(block)
            self.quiet = 0.0 if db >= self.th else self.quiet + dur
            if self.quiet >= self.hang or self.n >= self.max * self.rate:
                out = self._cut()
        return db, out

    def _cut(self):
        clip = np.concatenate(self.buf) if self.buf else np.zeros(0, np.int16)
        tail = int(max(0.0, self.quiet - 0.3) * self.rate)        # trim most of the trailing silence
        if tail and tail < len(clip):
            clip = clip[:-tail]
        self.active, self.buf, self.n, self.quiet = False, [], 0, 0.0
        return clip if len(clip) >= self.min * self.rate else None

    def flush(self):
        return self._cut() if self.active else None
