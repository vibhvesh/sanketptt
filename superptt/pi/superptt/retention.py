"""Daily retention cleanup + disk-space guard (oldest audio deleted first; transcripts kept longer)."""
import logging, os, shutil, threading, time
log = logging.getLogger("retention")

def disk(path):
    u = shutil.disk_usage(path)
    return {"total_gb": round(u.total / 1e9, 1), "free_gb": round(u.free / 1e9, 1), "free_pct": round(100 * u.free / u.total, 1)}

def rec_size(root):
    n = 0
    for d, _, fs in os.walk(root):
        for f in fs:
            try: n += os.path.getsize(os.path.join(d, f))
            except OSError: pass
    return n

class Retention:
    def __init__(self, cfg, store):
        self.cfg, self.store = cfg, store; self.root = os.path.join(cfg["data_dir"], "rec")
        self.last = {"run": None, "deleted_audio": 0, "deleted_rows": 0, "guard_deleted": 0}
    def info(self):
        d = disk(self.cfg["data_dir"]); d["rec_gb"] = round(rec_size(self.root) / 1e9, 3)
        d["segments"], d["with_audio"], d["oldest"] = self.store.counts()
        return {"disk": d, "retention": self.cfg["retention"], "last": self.last}
    def _rm(self, rel):
        try: os.remove(os.path.join(self.root, rel)); return True
        except FileNotFoundError: return True
        except OSError as e: log.warning("rm %s: %s", rel, e); return False
    def run_once(self, now=None):
        now = now or time.time(); r = self.cfg["retention"]
        a = 0
        for sid, rel in self.store.audio_older(now - float(r["audio_days"]) * 86400):
            if self._rm(rel): self.store.drop_audio(sid); a += 1
        rows = self.store.delete_older(now - float(r["transcript_days"]) * 86400, self._rm)
        g = self.guard()
        self._prune_dirs()
        self.last.update(run=now, deleted_audio=a, deleted_rows=rows, guard_deleted=g)
        log.info("retention: %d audio, %d rows removed, guard %d", a, rows, g); return self.last
    def guard(self):
        """Free space < min_free_pct: delete oldest audio first (transcripts stay)."""
        r = self.cfg["retention"]; n = 0
        while disk(self.cfg["data_dir"])["free_pct"] < float(r["min_free_pct"]):
            batch = self.store.oldest_audio(10)
            if not batch: break
            for sid, rel in batch:
                if self._rm(rel): self.store.drop_audio(sid); n += 1
        if n: log.warning("disk guard deleted %d oldest recordings (transcripts kept)", n)
        return n
    def _prune_dirs(self):
        for d, ds, fs in os.walk(self.root, topdown=False):
            if d != self.root and not ds and not fs:
                try: os.rmdir(d)
                except OSError: pass
    def start(self):
        def loop():
            time.sleep(30)
            while True:
                try: self.run_once()
                except Exception as e: log.warning("retention failed: %s", e)
                for _ in range(24 * 12):      # daily run, guard every 5 min
                    time.sleep(300)
                    try: self.guard()
                    except Exception: pass
        threading.Thread(target=loop, daemon=True).start()
