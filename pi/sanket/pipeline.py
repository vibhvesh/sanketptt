"""One pipeline for every input: save -> SSTV check/decode -> transcribe -> announce -> email -> optional forward.
Clips from the relay and from local mics look the same here (see inputs/registry.py)."""
import base64, datetime as dt, os, queue, threading, time
from . import alerts, announce, sstv
from .util import kw_find, log


class Pipeline:
    def __init__(self, cfg, storage, speaker, transcriber, metrics, name_fn, forwarder=None):
        self.cfg, self.store, self.speaker, self.stt, self.metrics = cfg, storage, speaker, transcriber, metrics
        self.name_fn, self.forwarder = name_fn, forwarder
        self.jobs = queue.Queue(maxsize=200)
        self.stats = dict(messages=0, sstv=0, emails=0, local=0, forwarded=0, started=time.time())

    def submit(self, clip):
        """Called from input threads. Writes the clip at once, the slow work happens on the worker."""
        dur = len(clip["i16"]) / clip["rate"]
        base = self.store.base_for(clip["t"], clip["channel"], clip["speaker"])
        self.store.save_clip(base, clip["i16"], clip["rate"])
        meta = dict(time=dt.datetime.fromtimestamp(clip["t"]).isoformat(timespec="seconds"), channel=clip["channel"],
                    speaker=clip["speaker"], duration_s=round(dur, 2), wav=os.path.basename(base + ".wav"), type="voice",
                    text="", status="queued", keywords=[], source=clip.get("source", ""), source_type=clip.get("source_type", ""))
        sm = clip.get("sstv_meta")
        if self.cfg["sstv"] and (sm or sstv.looks_like_sstv(clip["i16"], clip["rate"])):
            meta.update(type="sstv", mode=(sm or {}).get("mode", "SSTV"), status="sstv")
            if sm and str(sm.get("jpeg", "")).startswith("data:image"):
                open(base + ".jpg", "wb").write(base64.b64decode(sm["jpeg"].split(",", 1)[1]))
                meta["jpeg"] = os.path.basename(base + ".jpg")
        if clip.get("source_type") not in ("relay", ""):
            self.stats["local"] += 1
        self.metrics.count("received")
        self.store.add(meta)
        log.info("message on '%s' from %s (%.1fs, %s, %s)", clip["channel"], clip["speaker"], dur, meta["type"], clip.get("source_type"))
        try:
            self.jobs.put_nowait((clip, meta, base))
        except queue.Full:
            meta["status"] = "dropped (queue full)"; log.error("pipeline queue full - clip saved but not processed")

    def worker(self):
        threading.Thread(target=self.stt.ensure, daemon=True).start()
        while True:
            clip, meta, base = self.jobs.get()
            try:
                self.process(clip, meta, base)
            except Exception as e:
                meta["status"] = f"error: {e}"; log.exception("pipeline failed: %s", e)

    def process(self, clip, meta, base):
        c, i16, rate = self.cfg, clip["i16"], clip["rate"]
        if meta["type"] == "sstv":
            if c["sstv_decode"] and not meta.get("jpeg"):
                meta["status"] = "decoding sstv"
                r = sstv.decode(i16, rate, (clip.get("sstv_meta") or {}).get("mode"))
                if r:
                    open(base + ".png", "wb").write(sstv.png(r["rgb"]))
                    meta.update(image=os.path.basename(base + ".png"), mode=r["mode"], slant_ppm=r["slant_ppm"], lines=r["height"])
                elif not clip.get("sstv_meta"):
                    meta.update(type="voice", mode=None)       # tone but no decodable picture: treat as speech
        if meta["type"] == "sstv":
            self.metrics.count("sstv"); self.stats["sstv"] += 1
        elif c["transcribe"]:
            meta["status"] = "transcribing"
            out = self.stt(i16, rate)
            if out:
                meta["text"], meta["language"], meta["transcribe_s"] = out
                meta["keywords"] = kw_find(c["keywords"], meta["text"])
                self.metrics.count("transcribed")
        if meta["type"] == "voice":
            self.stats["messages"] += 1
        meta["status"] = "announcing"
        self.store.save_meta(base, meta)
        log.info("[%s] %s: %s", meta["channel"], meta["speaker"], meta["text"] or "(no transcript)")
        lines = announce.lines_for(c, meta)
        ok = self.speaker.say(lines, base + ".wav" if meta["type"] == "voice" else None)
        if lines and ok:
            self.metrics.count("announced")
        meta["announced"] = lines; meta["status"] = "done"
        self.store.save_meta(base, meta)
        if alerts.wanted(c, meta):
            if alerts.send(c, meta, base, self.name_fn()) == "sent":
                self.stats["emails"] += 1
        if clip.get("forward") and self.forwarder and clip.get("source_type") != "relay":
            ch = clip.get("forward_channel") or (c.enabled() or ["virtual"])[0]
            if self.forwarder(ch, i16, rate):
                self.stats["forwarded"] += 1; meta["forwarded_to"] = ch; self.store.save_meta(base, meta)
