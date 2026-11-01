#!/usr/bin/env python3
"""Sanket PTT - Raspberry Pi listen-only client.

Joins a Sanket PTT channel over MQTT/WSS exactly like the web radio's
listen-only monitor (transcribe/index.html 'SanketTranscribe'):
  * publishes ONLY retained presence  <prefix><ch>/presence/<id>  {"id","name","ts"}
    every 5 s (last-will = empty retained payload), so it shows in the online list;
  * subscribes presence/+, floor, audio, sstv;
  * NEVER publishes on floor / audio / sstv (never takes the floor, never transmits).
Incoming audio = [n][id bytes][Int16LE PCM @ 12 kHz]. Clips end on floor release,
floor silence > 2.5 s, or 60 s; clips < 0.4 s are ignored. SSTV transmissions are
saved (JPEG clean copy if sent) and not transcribed.
"""
import argparse, base64, datetime as dt, json, logging, logging.handlers, os, queue
import random, re, shutil, signal, socket, string, subprocess, sys, threading, time, wave
from urllib.parse import urlparse

import numpy as np
import yaml
import paho.mqtt.client as mqtt

PREFIX = "ptt-radio-66ab9178/"
RATE = 12000
HB_S, EXPIRE_S, FLOOR_TIMEOUT_S = 5.0, 15.0, 2.5
MIN_CLIP_S, MAX_CLIP_S, SSTV_META_S = 0.4, 60.0, 180.0
DEFAULTS = dict(channel="virtual", callsign="", broker_url="wss://public.cloud.shiftr.io",
                broker_username="public", broker_password="public", whisper_model="base",
                whisper_compute_type="int8", language="auto", beam_size=1,
                keywords=["mayday", "emergency", "fire", "help", "chetavani", "चेतावनी", "alert"],
                volume=1.0, audio_device=None, tts=True, tts_engine="espeak-ng", piper_model="",
                beep=True, clips_dir="~/sanket_clips", retention_days=7,
                log_file="~/sanket_clips/sanket_pi.log")
log = logging.getLogger("sanket")


# ---------------------------------------------------------------- helpers
def resample(x, src, dst):
    if src == dst or len(x) == 0:
        return x.astype(np.float32)
    n = int(round(len(x) * dst / src))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def write_wav(path, i16, rate=RATE):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(i16.astype("<i2").tobytes())


def tone_power(x, f, fs=RATE):
    n = len(x); k = 2 * np.pi * f / fs
    t = np.arange(n)
    return abs(np.dot(x, np.exp(-1j * k * t))) / max(1, n)


def looks_like_sstv(i16):
    """Robot36/VIS leader: ~300 ms of 1900 Hz, 10 ms 1200 Hz, 300 ms 1900 Hz at the start."""
    x = i16[: int(RATE * 1.0)].astype(np.float32) / 32768
    if len(x) < int(RATE * 0.6):
        return False
    hits = 0
    for s in range(0, int(RATE * 0.6), int(RATE * 0.05)):
        w = x[s:s + int(RATE * 0.05)]
        e = np.sqrt(np.mean(w ** 2)) + 1e-9
        if tone_power(w, 1900) / e > 0.5:   # pure 1900 Hz tone gives ~0.707
            hits += 1
    return hits >= 9


def kw_regex(kws):
    if not kws:
        return None
    alt = "|".join(re.escape(k) for k in sorted(kws, key=len, reverse=True))
    # same idea as the web app: keyword must not be glued to other letters/digits/marks
    return re.compile(r"(?<![\w\u0900-\u097F])(" + alt + r")(?![\w\u0900-\u097F])", re.I | re.U)


# ---------------------------------------------------------------- audio out
class Player:
    def __init__(self, cfg, enabled):
        self.enabled, self.vol, self.q, self.buf = enabled, float(cfg["volume"]), queue.Queue(), np.zeros(0, np.float32)
        self.rate, self.stream = RATE, None
        if not enabled:
            return
        try:
            import sounddevice as sd
            dev = cfg.get("audio_device")
            info = sd.query_devices(dev, "output")
            self.rate = int(info["default_samplerate"])
            self.stream = sd.OutputStream(samplerate=self.rate, channels=1, dtype="float32",
                                          device=dev, callback=self._cb, blocksize=1024)
            self.stream.start()
            log.info("audio out: %s @ %d Hz", info["name"], self.rate)
        except Exception as e:
            log.error("audio output unavailable (%s) - continuing without live playback", e)
            self.enabled = False

    def _cb(self, out, frames, t, status):
        while len(self.buf) < frames:
            try:
                self.buf = np.concatenate([self.buf, self.q.get_nowait()])
            except queue.Empty:
                break
        n = min(frames, len(self.buf))
        out[:n, 0] = self.buf[:n]; out[n:, 0] = 0
        self.buf = self.buf[n:]

    def play(self, i16):
        if self.enabled:
            f = np.clip(i16.astype(np.float32) / 32768 * self.vol, -1, 1)
            self.q.put(resample(f, RATE, self.rate))


# ---------------------------------------------------------------- alerts
class Alerter:
    def __init__(self, cfg, tts_dir=None, audio=True):
        self.cfg, self.tts_dir, self.audio = cfg, tts_dir, audio
        self.lock = threading.Lock()

    def _synth(self, text, path):
        c = self.cfg
        if c["tts_engine"] == "piper" and shutil.which("piper") and c.get("piper_model"):
            subprocess.run(["piper", "--model", os.path.expanduser(c["piper_model"]), "--output_file", path],
                           input=text.encode(), check=True, capture_output=True)
            return "piper"
        for exe in ("espeak-ng", "espeak"):
            if shutil.which(exe):
                subprocess.run([exe, "-v", "en", "-s", "150", "-w", path, text], check=True, capture_output=True)
                return exe
        from gtts import gTTS  # last-resort fallback (needs internet), used e.g. on dev boxes
        mp3 = path[:-4] + ".mp3"; gTTS(text, lang="en").save(mp3)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", mp3, path], check=True); os.remove(mp3)
        return "gTTS"

    def _beep(self, path):
        t = np.arange(int(RATE * 0.2)) / RATE
        b = (0.4 * np.sign(np.sin(2 * np.pi * 1200 * t)) * 32767).astype(np.int16)
        write_wav(path, np.concatenate([b, np.zeros(int(RATE * .1), np.int16), b]))

    def alert(self, callsign, text, kws):
        msg = f"Alert from {callsign}: {text}"
        log.warning("KEYWORD ALERT %s -> %s", kws, msg)
        threading.Thread(target=self._run, args=(msg,), daemon=True).start()

    def _run(self, msg):
        with self.lock:
            try:
                d = self.tts_dir or "/tmp"
                stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                files = []
                if self.cfg["beep"]:
                    files.append(os.path.join(d, f"alert_{stamp}_beep.wav")); self._beep(files[-1])
                if self.cfg["tts"]:
                    files.append(os.path.join(d, f"alert_{stamp}_tts.wav"))
                    eng = self._synth(msg, files[-1]); log.info("TTS (%s) -> %s", eng, files[-1])
                if self.audio and not self.tts_dir:
                    for f in files:
                        subprocess.run(["aplay", "-q", f], check=False)
                        os.remove(f)
            except Exception as e:
                log.error("alert TTS failed: %s", e)


# ---------------------------------------------------------------- transcriber
class Transcriber(threading.Thread):
    def __init__(self, cfg, alerter):
        super().__init__(daemon=True)
        self.cfg, self.alerter, self.q, self.model = cfg, alerter, queue.Queue(), None
        self.kre = kw_regex(cfg["keywords"])
        self.lang = None if str(cfg["language"]).lower() in ("auto", "", "none") else cfg["language"]

    def load(self):
        from faster_whisper import WhisperModel
        t = time.time()
        self.model = WhisperModel(self.cfg["whisper_model"], device="cpu",
                                  compute_type=self.cfg["whisper_compute_type"], cpu_threads=os.cpu_count() or 4)
        log.info("whisper '%s' (%s) loaded in %.1fs", self.cfg["whisper_model"], self.cfg["whisper_compute_type"], time.time() - t)

    def run(self):
        try:
            self.load()
        except Exception as e:
            log.error("whisper load failed: %s - clips will be saved untranscribed", e)
        while True:
            job = self.q.get()
            try:
                self.process(*job)
            except Exception as e:
                log.exception("transcribe failed: %s", e)

    def process(self, i16, meta, base):
        text, lang, secs = "", None, 0.0
        if self.model:
            t0 = time.time()
            audio = resample(i16.astype(np.float32) / 32768, RATE, 16000)
            segs, info = self.model.transcribe(audio, language=self.lang, beam_size=int(self.cfg["beam_size"]),
                                               vad_filter=False, condition_on_previous_text=False)
            text = " ".join(s.text.strip() for s in segs).strip()
            lang, secs = info.language, time.time() - t0
        kws = sorted({m.group(1).lower() for m in self.kre.finditer(text)}) if (self.kre and text) else []
        meta.update(text=text, language=lang, transcribe_s=round(secs, 2), keywords=kws, status="ok" if text else "no speech")
        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
        log.info("[%s] %s (%.1fs, %s, stt %.1fs): %s", meta["time"], meta["speaker"], meta["duration_s"], lang, secs, text or "(no speech)")
        if kws:
            self.alerter.alert(meta["speaker"], text, kws)


# ---------------------------------------------------------------- client
class SanketPi:
    def __init__(self, cfg, args):
        self.cfg, self.args = cfg, args
        self.ch = re.sub(r"[^\w-]", "", str(cfg["channel"])) or "virtual"
        self.name = (cfg.get("callsign") or f"SanketPi-{socket.gethostname()}")[:40]
        self.id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.dir = os.path.expanduser(cfg["clips_dir"]); os.makedirs(self.dir, exist_ok=True)
        self.users, self.floor, self.clip, self.sstv = {}, None, None, {}
        self.lock = threading.RLock()
        self.player = Player(cfg, not args.no_audio)
        self.alerter = Alerter(cfg, args.tts_file_dir, audio=not args.no_audio)
        self.stt = Transcriber(cfg, self.alerter)
        self.stats = dict(chunks=0, clips=0, sstv=0)
        self.stop = threading.Event()

    def T(self, s):
        return f"{PREFIX}{self.ch}/{s}"

    # -- mqtt
    def connect(self):
        u = urlparse(self.cfg["broker_url"])
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"ptt_{self.id}_{int(time.time()*1000)%1000000}",
                        transport="websockets", clean_session=True)
        c.ws_set_options(path=u.path or "/")
        if u.scheme == "wss":
            c.tls_set()
        user = u.username or self.cfg.get("broker_username"); pw = u.password or self.cfg.get("broker_password")
        if user:
            c.username_pw_set(user, pw)
        c.will_set(self.T(f"presence/{self.id}"), b"", qos=0, retain=True)
        c.reconnect_delay_set(1, 30)
        c.on_connect, c.on_message, c.on_disconnect = self.on_connect, self.on_message, self.on_disconnect
        self.c = c
        port = u.port or (443 if u.scheme == "wss" else 80)
        log.info("connecting %s://%s:%d channel '%s' as %s (id %s, listen-only)", u.scheme, u.hostname, port, self.ch, self.name, self.id)
        c.connect_async(u.hostname, port, keepalive=20)
        c.loop_start()

    def on_connect(self, c, ud, flags, rc, props=None):
        if rc != 0:
            log.error("connect refused: %s", rc); return
        c.subscribe([(self.T("presence/+"), 0), (self.T("floor"), 0), (self.T("audio"), 0), (self.T("sstv"), 0)])
        self.beat(); log.info("connected; monitoring '%s'", self.ch)

    def on_disconnect(self, c, ud, flags, rc, props=None):
        if not self.stop.is_set():
            log.warning("disconnected (%s) - auto-reconnecting", rc)

    def beat(self):
        if self.c.is_connected():  # the ONLY thing we ever publish
            self.c.publish(self.T(f"presence/{self.id}"),
                           json.dumps({"id": self.id, "name": self.name, "ts": int(time.time() * 1000)}), retain=True)

    def on_message(self, c, ud, msg):
        now, s, p = time.time(), msg.topic[len(PREFIX) + len(self.ch) + 1:], msg.payload
        with self.lock:
            if s.startswith("presence/"):
                uid = s[9:]
                if not p:
                    self.users.pop(uid, None)
                else:
                    try:
                        m = json.loads(p)
                        if now * 1000 - m["ts"] < 60000:
                            self.users[uid] = dict(name=str(m.get("name"))[:40], seen=now, loc=m.get("loc"))
                    except Exception:
                        pass
            elif s == "sstv":
                try:
                    m = json.loads(p)
                    if m.get("id"):
                        m["_rx"] = now; self.sstv[m["id"]] = m
                        log.info("SSTV meta from %s (%s)", m.get("name"), m.get("mode"))
                except Exception:
                    pass
            elif s == "floor":
                try:
                    m = json.loads(p)
                except Exception:
                    return
                if m.get("t") in ("claim", "hb"):
                    if not self.floor or self.floor["id"] != m.get("id"):
                        if self.clip:
                            self.end_clip("floor change")
                        self.floor = dict(id=m.get("id"), name=str(m.get("name") or "?")[:40])
                        log.info("floor: %s", self.floor["name"])
                    self.floor["seen"] = now
                    if m.get("id") in self.users:
                        self.users[m["id"]]["seen"] = now
                elif m.get("t") == "release" and self.floor and self.floor["id"] == m.get("id"):
                    self.floor = None; self.end_clip("release")
            elif s == "audio" and p:
                n = p[0]; uid = p[1:1 + n].decode("latin-1")
                if not self.floor or self.floor["id"] != uid or uid == self.id:
                    return
                self.floor["seen"] = now
                pcm = p[1 + n:]
                i16 = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").copy()
                if not self.clip:
                    self.clip = dict(id=uid, name=self.floor["name"], t=now, chunks=[], n=0)
                self.clip["chunks"].append(i16); self.clip["n"] += len(i16); self.stats["chunks"] += 1
                self.player.play(i16)
                if self.clip["n"] >= MAX_CLIP_S * RATE:
                    self.end_clip("60 s limit")

    def end_clip(self, why):
        k, self.clip = self.clip, None
        if not k or not k["n"]:
            return
        dur = k["n"] / RATE
        if dur < MIN_CLIP_S:
            log.info("short burst from %s ignored (%.2fs)", k["name"], dur); return
        i16 = np.concatenate(k["chunks"])
        ts = dt.datetime.fromtimestamp(k["t"])
        base = os.path.join(self.dir, f"{ts:%Y%m%d_%H%M%S}_{re.sub(r'[^A-Za-z0-9_-]', '_', k['name'])[:24]}")
        write_wav(base + ".wav", i16)
        u = self.users.get(k["id"], {})
        meta = dict(time=ts.isoformat(timespec="seconds"), channel=self.ch, speaker=k["name"], speaker_id=k["id"],
                    loc=u.get("loc"), duration_s=round(dur, 2), end_reason=why, wav=os.path.basename(base + ".wav"))
        sm = self.sstv.get(k["id"])
        sm = sm if sm and time.time() - sm["_rx"] < SSTV_META_S else None
        if sm or looks_like_sstv(i16):
            self.sstv.pop(k["id"], None); self.stats["sstv"] += 1
            meta.update(type="sstv", mode=(sm or {}).get("mode", "Robot36"), text=f"SSTV image from {k['name']}")
            if sm and str(sm.get("jpeg", "")).startswith("data:image"):
                with open(base + ".jpg", "wb") as f:
                    f.write(base64.b64decode(sm["jpeg"].split(",", 1)[1]))
                meta["jpeg"] = os.path.basename(base + ".jpg")
            with open(base + ".json", "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=1)
            log.info("[%s] SSTV image from %s (%.1fs) saved%s - not transcribed", meta["time"], k["name"], dur,
                     " with JPEG" if "jpeg" in meta else ""); return
        meta["type"] = "voice"; self.stats["clips"] += 1
        log.info("clip from %s: %.1fs (%s) -> transcribing", k["name"], dur, why)
        self.stt.q.put((i16, meta, base))

    def purge(self):
        cut = time.time() - float(self.cfg["retention_days"]) * 86400
        for f in os.listdir(self.dir):
            p = os.path.join(self.dir, f)
            if f.endswith((".wav", ".json", ".jpg")) and os.path.getmtime(p) < cut:
                os.remove(p)

    def run(self):
        self.stt.start(); self.connect(); self.purge()
        last_beat = last_purge = 0
        while not self.stop.is_set():
            now = time.time()
            if now - last_beat >= HB_S:
                last_beat = now; self.beat()
            if now - last_purge > 3600:
                last_purge = now; self.purge()
            with self.lock:
                for k in [k for k, v in self.users.items() if now - v["seen"] > EXPIRE_S]:
                    del self.users[k]
                if self.floor and now - self.floor["seen"] > FLOOR_TIMEOUT_S:
                    self.floor = None; self.end_clip("2.5 s silence")
            if self.args.status_file:
                with open(self.args.status_file, "w") as f:
                    json.dump(dict(id=self.id, name=self.name, connected=self.c.is_connected(),
                                   online=sorted(v["name"] for v in self.users.values()), **self.stats), f)
            self.stop.wait(1)

    def shutdown(self, *a):
        if self.stop.is_set():
            return
        self.stop.set()
        log.info("leaving channel")
        with self.lock:
            self.end_clip("shutdown")
        try:
            self.c.publish(self.T(f"presence/{self.id}"), b"", retain=True).wait_for_publish(2)
            self.c.disconnect(); self.c.loop_stop()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="Sanket PTT Raspberry Pi listen-only client")
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("-c", "--config", default=os.path.join(here, "config.yaml"))
    ap.add_argument("--channel"); ap.add_argument("--callsign"); ap.add_argument("--model")
    ap.add_argument("--no-audio", action="store_true", help="no live playback / no speaker output (headless test)")
    ap.add_argument("--tts-file-dir", help="write alert beep/TTS WAVs here instead of playing them")
    ap.add_argument("--status-file", help="write JSON status every second (for tests)")
    args = ap.parse_args()
    cfg = dict(DEFAULTS)
    if os.path.exists(args.config):
        cfg.update({k: v for k, v in (yaml.safe_load(open(args.config, encoding="utf-8")) or {}).items() if v is not None or k == "audio_device"})
    if args.channel: cfg["channel"] = args.channel
    if args.callsign: cfg["callsign"] = args.callsign
    if args.model: cfg["whisper_model"] = args.model
    if args.tts_file_dir: os.makedirs(args.tts_file_dir, exist_ok=True)
    os.makedirs(os.path.expanduser(cfg["clips_dir"]), exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    log.setLevel(logging.INFO)
    sh = logging.StreamHandler(sys.stdout); sh.setFormatter(fmt); log.addHandler(sh)
    fh = logging.handlers.RotatingFileHandler(os.path.expanduser(cfg["log_file"]), maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt); log.addHandler(fh)
    app = SanketPi(cfg, args)
    signal.signal(signal.SIGTERM, lambda *a: app.shutdown()); signal.signal(signal.SIGINT, lambda *a: app.shutdown())
    try:
        app.run()
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
