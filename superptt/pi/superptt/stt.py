"""STT job queue: local faster-whisper workers (multilingual, per-utterance language detect),
LAN remote workers pulling from the same queue over HTTP, optional cloud fallback (off by default)."""
import heapq, io, itertools, logging, os, threading, time, wave
import numpy as np
log = logging.getLogger("stt")

def to16k(pcm, rate):
    x = pcm.astype(np.float32) / 32768.0
    if rate == 16000 or not len(x): return x
    n = int(len(x) * 16000 / rate)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def _unused_wav_bytes(pcm, rate):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm.tobytes())
    return b.getvalue()

SCRIPT = {"hi": (0x0900, 0x097F), "mr": (0x0900, 0x097F), "gu": (0x0A80, 0x0AFF), "pa": (0x0A00, 0x0A7F),
          "bn": (0x0980, 0x09FF), "ta": (0x0B80, 0x0BFF), "te": (0x0C00, 0x0C7F), "ur": (0x0600, 0x06FF)}
PROMPT = {"hi": "नमस्ते, यह हिंदी में संदेश है।", "gu": "નમસ્તે, આ ગુજરાતીમાં સંદેશ છે."}
def _in_script(t, r):
    letters = [c for c in t if c.isalpha()]
    return bool(letters) and sum(r[0] <= ord(c) <= r[1] for c in letters) / len(letters) > 0.5

class Whisper:
    """Shared by the Pi and by worker.py."""
    def __init__(self, threads=2):
        self.threads, self.models, self.lock = threads, {}, threading.Lock()
    def model(self, name):
        assert not name.endswith(".en"), "multilingual models only"
        with self.lock:
            if name not in self.models:
                from faster_whisper import WhisperModel
                t = time.time()
                self.models[name] = WhisperModel(name, device="auto", compute_type="int8", cpu_threads=self.threads)
                log.info("whisper %s loaded %.1fs", name, time.time() - t)
            return self.models[name]
    def _tx(self, m, x16, lang, prompt=None):
        segs, info = m.transcribe(x16, language=lang, beam_size=1, vad_filter=True, condition_on_previous_text=False,
                                  initial_prompt=prompt, no_repeat_ngram_size=3, repetition_penalty=1.1,
                                  compression_ratio_threshold=2.2, max_new_tokens=160)
        segs = list(segs); self.last_q = {
            "avg_logprob": min([s.avg_logprob for s in segs], default=-9.0),
            "no_speech": max([s.no_speech_prob for s in segs], default=1.0)}
        return " ".join(s.text.strip() for s in segs).strip(), info
    def run(self, x16, name, language=None, hints=None, min_prob=0.8):
        r = self.run_q(x16, name, language, hints, min_prob); return r["text"], r["lang"], r["lang_prob"]
    def run_q(self, x16, name, language=None, hints=None, min_prob=0.8):
        m = self.model(name); lang, prob = language, None
        if not lang:
            try:
                lang, prob, allp = m.detect_language(x16)
                if hints and lang not in hints:  # channel hints win over an out-of-set guess
                    d = dict(allp); lang = max(hints, key=lambda h: d.get(h, 0)); prob = d.get(lang)
            except Exception as e:
                log.debug("detect failed %s", e); lang = None
        text, info = self._tx(m, x16, lang); q = dict(self.last_q)
        # script guard: Whisper often writes Hindi in Urdu script / Gujarati in Devanagari on small models
        if lang in SCRIPT and text and not _in_script(text, SCRIPT[lang]):
            t2, _ = self._tx(m, x16, lang, prompt=PROMPT.get(lang))
            if _in_script(t2, SCRIPT[lang]) and len(t2) >= 0.5 * len(text): text = t2; q = dict(self.last_q)
        ok_script = not (lang in SCRIPT and text and not _in_script(text, SCRIPT[lang]))
        return {"text": text, "lang": lang or info.language,
                "lang_prob": prob if prob is not None else info.language_probability, "script_ok": ok_script, **q}

class WhisperCpp:
    """whisper.cpp CLI backend (Termux/Android fallback when CTranslate2 is unavailable).
    Same run_q() contract as Whisper. Models: <whispercpp_models>/ggml-<name>.bin (multilingual only)."""
    def __init__(self, cfg):
        self.cfg = cfg; self.threads = int(cfg["whisper_threads"]); self.last_q = {}
    def path(self, name):
        assert not name.endswith(".en"), "multilingual models only"
        d = os.path.expanduser(self.cfg.get("whispercpp_models") or "~/.superptt/models")
        p = os.path.join(d, f"ggml-{name}.bin")
        if not os.path.exists(p):   # tiered model missing -> use any installed multilingual one
            have = [m for m in ("base", "small", "tiny") if os.path.exists(os.path.join(d, f"ggml-{m}.bin"))]
            if not have: raise RuntimeError("no whisper.cpp model in " + d)
            p = os.path.join(d, f"ggml-{have[0]}.bin")
        return p
    def run_q(self, x16, name, language=None, hints=None, min_prob=0.8):
        import json, subprocess, tempfile
        lang = language or (hints[0] if hints and len(hints) == 1 else "auto")
        with tempfile.TemporaryDirectory() as td:
            wp = os.path.join(td, "a.wav")
            with wave.open(wp, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
                w.writeframes((np.clip(x16, -1, 1) * 32767).astype("<i2").tobytes())
            cmd = [self.cfg.get("whispercpp_bin") or "whisper-cli", "-m", self.path(name), "-f", wp, "-l", lang,
                   "-t", str(self.threads), "-nt", "-np", "-oj", "-of", os.path.join(td, "o")]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
            j = json.load(open(os.path.join(td, "o.json"), encoding="utf-8", errors="replace"))
        text = " ".join(s.get("text", "").strip() for s in j.get("transcription", [])).strip()
        lang = (j.get("result") or {}).get("language") or (None if lang == "auto" else lang)
        ok = not (lang in SCRIPT and text and not _in_script(text, SCRIPT[lang]))
        # whisper.cpp JSON has no logprob/no-speech: neutral values, so cloud routing uses lang/script/empty only
        self.last_q = {"avg_logprob": 0.0, "no_speech": 0.0 if text else 1.0}
        return {"text": text, "lang": lang, "lang_prob": None, "script_ok": ok, **self.last_q}

class STT:
    def __init__(self, cfg, store):
        self.cfg, self.store = cfg, store
        self.q = []; self.cv = threading.Condition(); self.cnt = itertools.count()
        eng = cfg["stt_engine"]
        self.w = WhisperCpp(cfg) if eng == "whispercpp" else Whisper(int(cfg["whisper_threads"])); self.busy = 0
        self.leased = {}   # seg_id -> (job, deadline) for remote workers
        self.stats = {"local": 0, "remote": 0, "cloud": 0, "cloud_fail": 0, "failed": 0}
    def start(self):
        if self.cfg["local_stt"] and self.cfg["stt_engine"] != "none":
            for i in range(max(1, int(self.cfg["stt_workers"]))):
                threading.Thread(target=self._worker, daemon=True, name=f"stt{i}").start()
        threading.Thread(target=self._lease_reaper, daemon=True).start()
        threading.Thread(target=self._cloud_retry, daemon=True).start()
        for sid, ch, wav in self.store.pending():
            self.submit(sid, ch, None, wav=wav)
    def qlen(self): return len(self.q)
    def submit(self, seg_id, ch, pcm, wav=None):
        pri = -int(self.cfg["priority"].get(ch, 0))
        with self.cv:
            heapq.heappush(self.q, (pri, next(self.cnt), seg_id, ch, pcm, wav)); self.cv.notify()
    def _pop(self):
        with self.cv:
            return heapq.heappop(self.q) if self.q else None
    def _load(self, wav):
        with wave.open(os.path.join(self.cfg["data_dir"], "rec", wav)) as w:
            return np.frombuffer(w.readframes(w.getnframes()), "<i2")
    def pick_model(self, qlen):
        if qlen > int(self.cfg["overload_queue"]): return self.cfg["fallback_model"]
        if qlen == 0 and self.cfg["quality_model"]: return self.cfg["quality_model"]
        return self.cfg["whisper_model"]
    def hints(self, ch): return self.cfg["language_hints"].get(ch) or None
    # ---- remote LAN workers (worker.py) ----
    def claim(self):
        j = self._pop()
        if not j: return None
        _, _, sid, ch, pcm, wav = j
        if pcm is None: pcm = self._load(wav)
        self.leased[sid] = (j, time.time() + 120)
        return {"id": sid, "channel": ch, "rate": self.cfg["rate"], "language": self.cfg["language"],
                "hints": self.hints(ch), "model": self.pick_model(len(self.q)), "pcm": pcm}
    def result(self, sid, text, lang, engine):
        job = self.leased.pop(sid, None)
        if job is None: return False
        self.store.set_text(sid, "done", engine, lang, text); self.stats["remote"] += 1
        c = self.cfg["cloud"]; ch = job[0][3]
        if lang in c["langs"] or ((self.hints(ch) or [None])[0] in c["langs"]):
            pcm = job[0][4] if job[0][4] is not None else self._load(job[0][5])
            threading.Thread(target=self.try_cloud, args=(sid, ch, pcm, lang, "lang:" + str(lang)), daemon=True).start()
        return True
    def _lease_reaper(self):
        while True:
            time.sleep(5); now = time.time()
            for sid, (j, dl) in list(self.leased.items()):
                if now > dl:
                    self.leased.pop(sid, None)
                    with self.cv: heapq.heappush(self.q, j); self.cv.notify()
    # ---- routing: local first, cloud when needed ----
    def cloud_reason(self, ch, r, qlen):
        c = self.cfg["cloud"]; hints = self.hints(ch) or []
        if r is None: return "queue" if qlen > int(c["when_queue_over"]) else None
        if r["lang"] in c["langs"]: return "lang:" + r["lang"]
        if hints and hints[0] in c["langs"]: return "expected:" + hints[0]
        if not r["text"]: return None if r["no_speech"] > c["max_no_speech"] else "empty"
        if not r["script_ok"]: return "script"
        if r["avg_logprob"] < float(c["min_avg_logprob"]): return "lowconf"
        if r["lang_prob"] is not None and r["lang_prob"] < float(c["min_lang_prob"]): return "lowlang"
        return None
    def cloud_ready(self):
        from .cloud import api_key
        c = self.cfg["cloud"]; return bool(c["enabled"] and api_key(c))
    def try_cloud(self, sid, ch, pcm, lang, reason):
        """True if cloud result stored. On failure the local result stays and the segment is retried later."""
        if not self.cloud_ready():
            self.store.mark_cloud(sid, "nokey", reason); return False
        try:
            from .cloud import transcribe
            # never pass a doubtful local guess (it forces the wrong script); only a trusted language
            send = (reason.split(":", 1)[1] if reason.startswith(("lang:", "expected:")) else None) or self.cfg["language"]
            t, l = transcribe(self.cfg["cloud"], pcm, self.cfg["rate"], send, self.hints(ch))
            self.store.set_cloud(sid, t, l, "cloud-" + self.cfg["cloud"]["provider"], reason)
            self.stats["cloud"] += 1; log.info("seg %s cloud(%s) [%s] %s", sid, reason, l, t); return True
        except Exception as e:
            log.warning("cloud failed seg %s: %s (local kept, retry later)", sid, e)
            self.stats["cloud_fail"] = self.stats.get("cloud_fail", 0) + 1
            self.store.mark_cloud(sid, "retry", reason); return False
    def _cloud_retry(self):
        while True:
            time.sleep(max(30, int(self.cfg["cloud"]["retry_s"])))
            if not self.cloud_ready(): continue
            for sid, ch, wav, lang, reason in self.store.cloud_pending():
                try: self.try_cloud(sid, ch, self._load(wav), lang, reason)
                except Exception as e: log.warning("retry seg %s: %s", sid, e)
    def _worker(self):
        while True:
            with self.cv:
                while not self.q: self.cv.wait()
                j = heapq.heappop(self.q); self.busy += 1
            _, _, sid, ch, pcm, wav = j
            try:
                if pcm is None: pcm = self._load(wav)
                if len(pcm) / self.cfg["rate"] < self.cfg["min_segment_s"]:
                    self.store.set_text(sid, "skipped"); continue
                self.store.set_text(sid, "transcribing")
                qlen = len(self.q); r = None
                pre = self.cloud_reason(ch, None, qlen)
                if pre and self.cloud_ready() and self.try_cloud(sid, ch, pcm, self.cfg["language"], pre):
                    continue                                   # overflow -> cloud first
                if self.cfg["stt_engine"] == "cloud":            # cloud-only (e.g. Android without local STT)
                    self.store.set_text(sid, "done", "none", None, "")
                    self.try_cloud(sid, ch, pcm, self.cfg["language"], "cloud-only"); continue
                if self.cfg["stt_engine"] == "vosk":
                    import json, vosk
                    if not hasattr(self, "vm"): self.vm = vosk.Model(self.cfg["vosk_model_path"])
                    rv = vosk.KaldiRecognizer(self.vm, self.cfg["rate"]); rv.AcceptWaveform(pcm.tobytes())
                    t, lang, eng = json.loads(rv.FinalResult()).get("text", ""), None, "vosk"
                else:
                    name = self.pick_model(qlen)
                    r = self.w.run_q(to16k(pcm, self.cfg["rate"]), name, self.cfg["language"],
                                     self.hints(ch), self.cfg["hint_min_prob"])
                    t, lang, eng = r["text"], r["lang"], ("whispercpp-" if self.cfg["stt_engine"] == "whispercpp" else "whisper-") + name; self.stats["local"] += 1
                self.store.set_text(sid, "done", eng, lang, t)
                why = self.cloud_reason(ch, r, qlen) if r else pre
                if why: self.try_cloud(sid, ch, pcm, lang, why)
                log.info("seg %s [%s/%s] %s", sid, eng, lang, t)
            except Exception as e:
                log.warning("stt failed seg %s: %s (pending)", sid, e); self.stats["failed"] += 1
                self.store.set_text(sid, "pending")
            finally:
                with self.cv: self.busy -= 1
