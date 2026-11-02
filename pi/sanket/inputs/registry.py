"""Input registry + manager. An input turns some audio source into clips and hands them to ctx.submit(clip).

clip = dict(source, source_type, channel, speaker, t, i16 (np.int16 mono), rate, sstv_meta=None)
"""
import json, threading, time
from ..util import log

_TYPES = {}


def register(cls):
    _TYPES[cls.TYPE] = cls
    return cls


def types():
    return [dict(type=t, label=c.LABEL, fields=c.FIELDS, local=c.LOCAL, kinds=c.KINDS) for t, c in _TYPES.items() if not c.HIDDEN]


def create(spec, ctx):
    cls = _TYPES.get(spec.get("type"))
    if not cls:
        raise ValueError(f"unknown input type {spec.get('type')!r}")
    return cls(spec, ctx)


class InputBase:
    TYPE, LABEL, FIELDS, LOCAL, HIDDEN, KINDS = "base", "Base", [], False, False, []

    def __init__(self, spec, ctx):
        self.spec, self.ctx = dict(spec), ctx
        self.id = spec["id"]; self.state, self.error, self.level = "stopped", "", -90.0
        self.clips, self.last_clip = 0, None
        self.stop_ev = threading.Event()

    def channel(self):
        return self.spec.get("channel") or self.id

    def start(self):
        self.stop_ev.clear(); self.state = "starting"
        threading.Thread(target=self._guard, daemon=True, name=f"in-{self.id}").start()

    def _guard(self):
        """Always on: if run() crashes or the device disappears, retry with back-off."""
        delay = 2
        while not self.stop_ev.is_set():
            try:
                self.state = "running"; self.run(); delay = 2
            except Exception as e:
                self.error = str(e)[:200]; self.state = "error"; log.error("input %s: %s", self.id, e)
            if self.stop_ev.wait(delay):
                break
            delay = min(delay * 2, 30)
        self.state = "stopped"

    def run(self):
        raise NotImplementedError

    def stop(self):
        self.stop_ev.set()

    def emit(self, i16, rate, speaker=None, channel=None, t=None, sstv_meta=None):
        self.clips += 1; self.last_clip = time.time()
        self.ctx.submit(dict(source=self.id, source_type=self.TYPE, channel=channel or self.channel(),
                             speaker=speaker or self.spec.get("name") or self.id, t=t or time.time(),
                             i16=i16, rate=rate, sstv_meta=sstv_meta, forward=bool(self.spec.get("forward")),
                             forward_channel=self.spec.get("forward_channel") or ""))

    def set_level(self, db):
        self.level = db
        if self.ctx.metrics:
            self.ctx.metrics.level(self.id, db)

    def status(self):
        return dict(id=self.id, type=self.TYPE, name=self.spec.get("name"), state=self.state, error=self.error,
                    level=round(self.level, 1), clips=self.clips, last_clip=self.last_clip, enabled=True)


class InputManager:
    """Keeps running inputs in sync with config (start new, restart edited, stop removed/disabled)."""
    def __init__(self, ctx, specs_fn):
        self.ctx, self.specs_fn, self.running, self.lock = ctx, specs_fn, {}, threading.RLock()

    def reconcile(self):
        with self.lock:
            want = {s["id"]: s for s in self.specs_fn() if s.get("enabled", True)}
            for iid in list(self.running):
                inp = self.running[iid]
                if iid not in want or json.dumps(inp.spec, sort_keys=True) != json.dumps(want[iid], sort_keys=True):
                    inp.stop(); del self.running[iid]; log.info("input %s stopped", iid)
            for iid, s in want.items():
                if iid not in self.running:
                    try:
                        inp = create(s, self.ctx); inp.start(); self.running[iid] = inp
                        log.info("input %s (%s) started", iid, s["type"])
                    except Exception as e:
                        log.error("input %s not started: %s", iid, e)

    def get(self, iid):
        return self.running.get(iid)

    def status(self):
        out = []
        for s in self.specs_fn():
            r = self.running.get(s["id"])
            st = r.status() if r else dict(id=s["id"], type=s.get("type"), name=s.get("name"), state="disabled",
                                           error="", level=-90.0, clips=0, last_clip=None)
            st["enabled"] = bool(s.get("enabled", True)); out.append(st)
        return out

    def stop_all(self):
        for r in list(self.running.values()):
            r.stop()
