"""Time series for the dashboard: messages received / transcribed / announced and audio in/out levels.
10-second buckets, last hour kept in memory (tiny)."""
import collections, threading, time

BUCKET_S, KEEP = 10, 360


class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.series = collections.deque(maxlen=KEEP)
        self.totals = collections.Counter()
        self.levels = {}            # source -> (dBFS, ts)  live meters
        self._cur = None

    def _bucket(self):
        t = int(time.time() // BUCKET_S * BUCKET_S)
        if not self._cur or self._cur["t"] != t:
            self._cur = dict(t=t, received=0, transcribed=0, announced=0, sstv=0, in_db=-90.0, out_db=-90.0)
            self.series.append(self._cur)
        return self._cur

    def count(self, kind, n=1):
        with self.lock:
            b = self._bucket(); b[kind] = b.get(kind, 0) + n; self.totals[kind] += n

    def level(self, src, db):
        """src = 'out' or an input id. Keeps the loudest value seen in the bucket for the graph."""
        with self.lock:
            self.levels[src] = (round(db, 1), time.time())
            b = self._bucket(); k = "out_db" if src == "out" else "in_db"
            b[k] = max(b[k], round(db, 1))

    def snapshot(self):
        with self.lock:
            self._bucket(); now = time.time()
            return dict(bucket_s=BUCKET_S, series=list(self.series), totals=dict(self.totals),
                        levels={k: (v if now - t < 3 else -90.0) for k, (v, t) in self.levels.items()})
