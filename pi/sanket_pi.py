#!/usr/bin/env python3
"""Sanket PTT - Raspberry Pi receive-only listener with web management.

* Joins Sanket PTT channels over MQTT/WSS exactly like the web radio:
  topics  ptt-radio-66ab9178/<channel>/{presence/<id>,floor,audio,sstv}
  audio = [n][id bytes][Int16LE PCM @ 12 kHz]; floor = {"t":"claim|hb|release","id","name"}.
* Receive-only: the ONLY thing ever published is retained presence (so the Pi shows as online).
  It never claims the floor and never sends audio/SSTV.
* Every message: play the audio, speak "New message on <channel> from <name>", then the transcript.
  Offline TTS (piper or espeak-ng), offline Whisper (faster-whisper).
* Everything is managed from the built-in web page (default http://<host>.local:8080).
  Settings persist in config.json next to this file.
"""
import base64, collections, datetime as dt, json, logging, logging.handlers, os, queue, random, re
import shutil, smtplib, socket, string, subprocess, sys, threading, time, wave
from email.message import EmailMessage
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

import numpy as np
import paho.mqtt.client as mqtt

VERSION = "2.0.0"
PREFIX = "ptt-radio-66ab9178/"
RATE = 12000
HB_S, EXPIRE_S, FLOOR_TIMEOUT_S = 5.0, 15.0, 2.5
MIN_CLIP_S, MAX_CLIP_S, SSTV_META_S = 0.4, 60.0, 180.0
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.environ.get("SANKET_CONFIG", os.path.join(APP_DIR, "config.json"))
REPO_RAW = "https://vibhvesh.github.io/sanketptt/pi"
APP_FILES = ["sanket_pi.py", "web/index.html", "requirements.txt", "install.sh"]
# Known Sanket PTT channels (auto-added). 'virtual' is the web app default (?ch=...).
KNOWN_CHANNELS = ["virtual", "master", "city-control", "kolkata-control", "unit-name"]
BROKERS = ["wss://public:public@public.cloud.shiftr.io", "wss://broker.emqx.io:8084/mqtt",
           "wss://broker.hivemq.com:8884/mqtt", "wss://test.mosquitto.org:8081"]

DEFAULTS = {
    "device_name": "",                     # shown as callsign in the online list; empty -> SanketPi-<host>
    "channels": [{"name": c, "enabled": True} for c in KNOWN_CHANNELS],
    "listen_all": True,                    # also monitor every other channel seen on the broker
    "auto_add_discovered": True,           # add newly seen channels to the list automatically
    "broker_url": BROKERS[0],
    "volume": 80,                          # 0-150 %
    "audio_device": "default",             # ALSA device for aplay
    "play_audio": True,                    # play the received transmission
    "announce": True,                      # speak "New message on <channel>"
    "announce_speaker": True,              # include who sent it
    "announce_transcript": True,           # read the transcript aloud
    "announce_template": "New message on {channel} from {name}",
    "beep": True,
    "tts_engine": "espeak-ng",             # espeak-ng | piper
    "espeak_voice": "en",
    "tts_speed": 150,
    "piper_model": "",
    "transcribe": True,
    "whisper_model": "base",               # tiny | base | small
    "language": "auto",
    "keywords": ["mayday", "emergency", "fire", "help", "chetavani", "चेतावनी", "alert"],
    "sstv": True,                          # detect SSTV, save the picture, announce "SSTV image"
    "email_enabled": False,
    "email_mode": "keywords",              # keywords | all
    "email_to": "", "smtp_host": "smtp.gmail.com", "smtp_port": 587,
    "smtp_user": "", "smtp_password": "", "smtp_tls": True,
    "web_port": 8080,
    "web_pin": "",                         # optional PIN to change settings
    "clips_dir": "~/sanket_clips",
    "retention_days": 7,
}
SECRET = ("smtp_password", "web_pin")
log = logging.getLogger("sanket")
LOG_RING = collections.deque(maxlen=600)


class RingHandler(logging.Handler):
    def emit(self, r):
        LOG_RING.append(self.format(r))


def clean_ch(s):
    return re.sub(r"[^\w-]", "", str(s or "")).lower()[:40]


# ---------------------------------------------------------------- config
class Config:
    def __init__(self, path):
        self.path, self.lock = path, threading.RLock()
        self.d = json.loads(json.dumps(DEFAULTS))
        if os.path.exists(path):
            try:
                self.d.update(json.load(open(path, encoding="utf-8")))
            except Exception as e:
                print("config.json unreadable, using defaults:", e)
        self.merge_known(); self.save()

    def merge_known(self):
        have = {c["name"] for c in self.d["channels"]}
        for c in KNOWN_CHANNELS:
            if c not in have:
                self.d["channels"].append({"name": c, "enabled": True})

    def __getitem__(self, k):
        return self.d.get(k, DEFAULTS.get(k))

    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"
            json.dump(self.d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)

    def public(self):
        d = json.loads(json.dumps(self.d))
        for k in SECRET:
            d[k + "_set"] = bool(d.get(k)); d[k] = ""
        return d

    def update(self, new):
        with self.lock:
            for k, v in new.items():
                if k not in DEFAULTS:
                    continue
                if k in SECRET and v in ("", None):
                    continue           # blank = keep existing secret
                if k == "channels":
                    seen, out = set(), []
                    for c in v:
                        n = clean_ch(c.get("name"))
                        if n and n not in seen:
                            seen.add(n); out.append({"name": n, "enabled": bool(c.get("enabled", True))})
                    v = out
                t = type(DEFAULTS[k])
                if t is bool: v = bool(v)
                elif t is int: v = int(float(v))
                elif t is list and k == "keywords" and isinstance(v, str):
                    v = [x.strip() for x in v.split(",") if x.strip()]
                self.d[k] = v
            self.save()

    def enabled(self):
        return [c["name"] for c in self.d["channels"] if c.get("enabled")]


# ---------------------------------------------------------------- audio helpers
def write_wav(path, i16, rate=RATE):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(i16.astype("<i2").tobytes())


def read_wav(path):
    with wave.open(path, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").copy(), w.getframerate(), w.getnchannels()


def resample(x, src, dst):
    if src == dst or len(x) == 0:
        return x.astype(np.float32)
    n = int(round(len(x) * dst / src))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def looks_like_sstv(i16):
    x = i16[: RATE].astype(np.float32) / 32768
    if len(x) < int(RATE * 0.6):
        return False
    hits, k = 0, 2 * np.pi * 1900 / RATE
    for s in range(0, int(RATE * 0.6), int(RATE * 0.05)):
        w = x[s:s + int(RATE * 0.05)]
        e = np.sqrt(np.mean(w ** 2)) + 1e-9
        if abs(np.dot(w, np.exp(-1j * k * np.arange(len(w))))) / len(w) / e > 0.5:
            hits += 1
    return hits >= 9


def kw_find(kws, text):
    if not kws or not text:
        return []
    alt = "|".join(re.escape(k) for k in sorted(kws, key=len, reverse=True))
    r = re.compile(r"(?<![\w\u0900-\u097F])(" + alt + r")(?![\w\u0900-\u097F])", re.I | re.U)
    return sorted({m.group(1).lower() for m in r.finditer(text)})


# ---------------------------------------------------------------- speaker
class Speaker:
    """Serialises everything that comes out of the speaker: clip audio, beep, TTS."""
    def __init__(self, cfg, tmp):
        self.cfg, self.tmp, self.lock = cfg, tmp, threading.Lock()
        self.dry = os.environ.get("SANKET_DRY_AUDIO") == "1"   # tests: write files, don't play
        self.last = []

    def _play(self, path):
        vol = max(0, min(150, int(self.cfg["volume"]))) / 100.0
        i16, rate, nch = read_wav(path)
        out = os.path.join(self.tmp, "out_" + os.path.basename(path))
        x = np.clip(i16.astype(np.float32) * vol, -32768, 32767).astype(np.int16)
        with wave.open(out, "wb") as w:
            w.setnchannels(nch); w.setsampwidth(2); w.setframerate(rate); w.writeframes(x.tobytes())
        self.last.append(out); self.last = self.last[-10:]
        if self.dry or not shutil.which("aplay"):
            log.info("[audio] %s", os.path.basename(out)); return
        r = subprocess.run(["aplay", "-q", "-D", self.cfg["audio_device"] or "default", out], capture_output=True, timeout=180)
        if r.returncode:
            log.error("aplay failed on '%s': %s", self.cfg["audio_device"], r.stderr.decode(errors="ignore").strip())

    def synth(self, text, path):
        c = self.cfg
        if c["tts_engine"] == "piper" and c["piper_model"] and os.path.exists(os.path.expanduser(c["piper_model"])):
            exe = shutil.which("piper") or os.path.join(APP_DIR, "venv/bin/piper")
            if os.path.exists(exe):
                subprocess.run([exe, "--model", os.path.expanduser(c["piper_model"]), "--output_file", path],
                               input=text.encode(), check=True, capture_output=True, timeout=120)
                return "piper"
        for exe in ("espeak-ng", "espeak"):
            if shutil.which(exe):
                subprocess.run([exe, "-v", c["espeak_voice"] or "en", "-s", str(int(c["tts_speed"])), "-w", path, text],
                               check=True, capture_output=True, timeout=60)
                return exe
        raise RuntimeError("no offline TTS engine installed (espeak-ng / piper)")

    def beep(self, path):
        t = np.arange(int(RATE * 0.15)) / RATE
        b = (0.35 * np.sin(2 * np.pi * 1000 * t) * 32767).astype(np.int16)
        write_wav(path, np.concatenate([b, np.zeros(int(RATE * .08), np.int16), b]))

    def say(self, lines, clip=None):
        with self.lock:
            stamp = dt.datetime.now().strftime("%H%M%S%f")
            try:
                if clip and self.cfg["play_audio"]:
                    self._play(clip)
                if self.cfg["beep"]:
                    p = os.path.join(self.tmp, f"beep_{stamp}.wav"); self.beep(p); self._play(p)
                for i, text in enumerate(l for l in lines if l):
                    p = os.path.join(self.tmp, f"tts_{stamp}_{i}.wav")
                    eng = self.synth(text, p); log.info("TTS (%s): %s", eng, text); self._play(p)
            except Exception as e:
                log.error("announcement failed: %s", e)


# ---------------------------------------------------------------- main app
class SanketPi:
    def __init__(self, cfg):
        self.cfg = cfg
        self.dir = os.path.expanduser(cfg["clips_dir"]); os.makedirs(self.dir, exist_ok=True)
        self.tmp = os.path.join(self.dir, ".tmp"); os.makedirs(self.tmp, exist_ok=True)
        self.id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.lock = threading.RLock()
        self.chs = {}            # channel -> {users, floor, clip, sstv, last}
        self.feed = collections.deque(maxlen=200)
        self.stats = dict(messages=0, sstv=0, emails=0, started=time.time())
        self.speaker = Speaker(cfg, self.tmp)
        self.jobs = queue.Queue()
        self.model, self.model_name, self.model_state = None, None, "off"
        self.c, self.subs, self.connected, self.broker_err = None, set(), False, ""
        self.stop = threading.Event()
        self.load_feed()

    def name(self):
        return (self.cfg["device_name"] or f"SanketPi-{socket.gethostname()}")[:40]

    def T(self, ch, s):
        return f"{PREFIX}{ch}/{s}"

    def st(self, ch):
        return self.chs.setdefault(ch, dict(users={}, floor=None, clip=None, sstv={}, last=None))

    # ---- mqtt
    def connect(self):
        if self.c:
            try:
                for ch in self.subs:
                    self.c.publish(self.T(ch, f"presence/{self.id}"), b"", retain=True)
                self.c.disconnect(); self.c.loop_stop()
            except Exception:
                pass
        self.subs, self.connected = set(), False
        u = urlparse(self.cfg["broker_url"])
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"ptt_{self.id}_{int(time.time()*1000)%1000000}",
                        transport="websockets", clean_session=True)
        c.ws_set_options(path=u.path or "/")
        if u.scheme == "wss":
            c.tls_set()
        if u.username:
            c.username_pw_set(unquote(u.username), unquote(u.password or ""))
        c.reconnect_delay_set(1, 30)
        c.on_connect, c.on_message, c.on_disconnect = self.on_connect, self.on_message, self.on_disconnect
        self.c = c
        port = u.port or (443 if u.scheme == "wss" else 80)
        log.info("connecting %s://%s:%d as %s (receive-only)", u.scheme, u.hostname, port, self.name())
        try:
            c.connect_async(u.hostname, port, keepalive=20); c.loop_start()
        except Exception as e:
            self.broker_err = str(e); log.error("broker: %s", e)

    def on_connect(self, c, ud, flags, rc, props=None):
        if rc != 0:
            self.broker_err = str(rc); log.error("connect refused: %s", rc); return
        self.connected, self.broker_err, self.subs = True, "", set()
        if self.cfg["listen_all"] or self.cfg["auto_add_discovered"]:
            c.subscribe(PREFIX + "+/presence/+", 0)       # discover channels
        self.sync_subs(); log.info("connected; monitoring %s", ", ".join(sorted(self.subs)) or "(none)")

    def on_disconnect(self, c, ud, flags, rc, props=None):
        self.connected = False
        if not self.stop.is_set():
            log.warning("disconnected (%s) - auto-reconnecting", rc)

    def wanted(self):
        w = set(self.cfg.enabled())
        if self.cfg["listen_all"]:
            w |= {ch for ch, s in self.chs.items() if s["users"]}
        return w

    def sync_subs(self):
        if not self.connected:
            return
        want = self.wanted()
        for ch in want - self.subs:
            self.c.subscribe([(self.T(ch, s), 0) for s in ("presence/+", "floor", "audio", "sstv")])
        for ch in self.subs - want:
            self.c.publish(self.T(ch, f"presence/{self.id}"), b"", retain=True)
            self.c.unsubscribe([self.T(ch, s) for s in ("presence/+", "floor", "audio", "sstv")])
        self.subs = want
        self.beat()

    def beat(self):   # the ONLY thing ever published
        if self.connected:
            for ch in self.cfg.enabled():
                self.c.publish(self.T(ch, f"presence/{self.id}"),
                               json.dumps({"id": self.id, "name": self.name(), "ts": int(time.time() * 1000)}), retain=True)

    def on_message(self, c, ud, msg):
        try:
            self.handle(msg.topic, msg.payload)
        except Exception as e:
            log.exception("message error: %s", e)

    def handle(self, topic, p):
        now = time.time()
        if not topic.startswith(PREFIX):
            return
        ch, _, s = topic[len(PREFIX):].partition("/")
        if not ch or clean_ch(ch) != ch:
            return
        with self.lock:
            S = self.st(ch)
            if s.startswith("presence/"):
                uid = s[9:]
                if uid == self.id:
                    return
                if not p:
                    S["users"].pop(uid, None); return
                try:
                    m = json.loads(p)
                    if now * 1000 - m["ts"] < 60000:
                        S["users"][uid] = dict(name=str(m.get("name"))[:40], seen=now)
                except Exception:
                    return
                names = {x["name"] for x in self.cfg["channels"]}
                if ch not in names and self.cfg["auto_add_discovered"]:
                    self.cfg.update({"channels": self.cfg["channels"] + [{"name": ch, "enabled": True}]})
                    log.info("discovered channel '%s' - added", ch)
                if ch not in self.subs and (self.cfg["listen_all"] or ch in self.cfg.enabled()):
                    threading.Thread(target=self.sync_subs, daemon=True).start()
                return
            if ch not in self.subs and not os.environ.get("SANKET_TEST"):
                return
            if s == "sstv":
                try:
                    m = json.loads(p)
                    if m.get("id"):
                        m["_rx"] = now; S["sstv"][m["id"]] = m
                except Exception:
                    pass
            elif s == "floor":
                try:
                    m = json.loads(p)
                except Exception:
                    return
                if m.get("id") == self.id:
                    return
                if m.get("t") in ("claim", "hb"):
                    if not S["floor"] or S["floor"]["id"] != m.get("id"):
                        if S["clip"]:
                            self.end_clip(ch, "floor change")
                        S["floor"] = dict(id=m.get("id"), name=str(m.get("name") or "?")[:40])
                    S["floor"]["seen"] = now
                elif m.get("t") == "release" and S["floor"] and S["floor"]["id"] == m.get("id"):
                    S["floor"] = None; self.end_clip(ch, "release")
            elif s == "audio" and p:
                n = p[0]; uid = p[1:1 + n].decode("latin-1")
                f = S["floor"]
                if not f or f["id"] != uid:
                    return
                f["seen"] = now
                pcm = p[1 + n:]
                i16 = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").copy()
                if not S["clip"]:
                    S["clip"] = dict(id=uid, name=f["name"], t=now, chunks=[], n=0)
                S["clip"]["chunks"].append(i16); S["clip"]["n"] += len(i16)
                if S["clip"]["n"] >= MAX_CLIP_S * RATE:
                    self.end_clip(ch, "60 s limit")

    def end_clip(self, ch, why):
        S = self.st(ch)
        k, S["clip"] = S["clip"], None
        if not k or not k["n"]:
            return
        dur = k["n"] / RATE
        if dur < MIN_CLIP_S:
            return
        i16 = np.concatenate(k["chunks"])
        ts = dt.datetime.fromtimestamp(k["t"])
        base = os.path.join(self.dir, f"{ts:%Y%m%d_%H%M%S}_{ch}_{re.sub(r'[^A-Za-z0-9_-]', '_', k['name'])[:24]}")
        write_wav(base + ".wav", i16)
        meta = dict(time=ts.isoformat(timespec="seconds"), channel=ch, speaker=k["name"], duration_s=round(dur, 2),
                    wav=os.path.basename(base + ".wav"), type="voice", text="", status="queued", keywords=[])
        sm = S["sstv"].pop(k["id"], None)
        sm = sm if sm and time.time() - sm["_rx"] < SSTV_META_S else None
        if self.cfg["sstv"] and (sm or looks_like_sstv(i16)):
            meta.update(type="sstv", mode=(sm or {}).get("mode", "SSTV"), status="sstv")
            if sm and str(sm.get("jpeg", "")).startswith("data:image"):
                open(base + ".jpg", "wb").write(base64.b64decode(sm["jpeg"].split(",", 1)[1]))
                meta["jpeg"] = os.path.basename(base + ".jpg")
        S["last"] = time.time()
        self.feed.appendleft(meta)
        log.info("message on '%s' from %s (%.1fs, %s)", ch, k["name"], dur, meta["type"])
        self.jobs.put((i16, meta, base))

    # ---- worker: transcribe -> announce -> email
    def ensure_model(self):
        if not self.cfg["transcribe"]:
            return None
        want = self.cfg["whisper_model"]
        if self.model and self.model_name == want:
            return self.model
        try:
            self.model_state = f"loading {want}"
            from faster_whisper import WhisperModel
            t = time.time()
            self.model = WhisperModel(want, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
            self.model_name, self.model_state = want, f"{want} ready"
            log.info("whisper '%s' loaded in %.1fs", want, time.time() - t)
        except Exception as e:
            self.model, self.model_state = None, f"error: {e}"; log.error("whisper load failed: %s", e)
        return self.model

    def worker(self):
        threading.Thread(target=self.ensure_model, daemon=True).start()
        while True:
            i16, meta, base = self.jobs.get()
            try:
                self.process(i16, meta, base)
            except Exception as e:
                log.exception("pipeline failed: %s", e)

    def process(self, i16, meta, base):
        c = self.cfg
        if meta["type"] == "voice" and c["transcribe"]:
            meta["status"] = "transcribing"
            m = self.ensure_model()
            if m:
                t0 = time.time()
                lang = None if str(c["language"]).lower() in ("auto", "") else c["language"]
                segs, info = m.transcribe(resample(i16.astype(np.float32) / 32768, RATE, 16000), language=lang,
                                          beam_size=1, vad_filter=False, condition_on_previous_text=False)
                meta["text"] = " ".join(s.text.strip() for s in segs).strip()
                meta.update(language=info.language, transcribe_s=round(time.time() - t0, 2))
                meta["keywords"] = kw_find(c["keywords"], meta["text"])
        meta["status"] = "announcing"
        self.stats["messages" if meta["type"] == "voice" else "sstv"] += 1
        json.dump(meta, open(base + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        log.info("[%s] %s: %s", meta["channel"], meta["speaker"], meta["text"] or "(no transcript)")
        lines = []
        if c["announce"]:
            chn = meta["channel"].replace("-", " ").replace("_", " ")
            if meta["type"] == "sstv":
                lines.append(f"New SSTV picture on {chn} from {meta['speaker']}")
            else:
                tpl = c["announce_template"] if c["announce_speaker"] else "New message on {channel}"
                try:
                    lines.append(tpl.format(channel=chn, name=meta["speaker"]))
                except Exception:
                    lines.append(f"New message on {chn}")
                if meta["keywords"]:
                    lines.insert(0, "Alert! Alert!")
                if c["announce_transcript"] and meta["text"]:
                    lines.append(meta["text"])
        self.speaker.say(lines, base + ".wav" if meta["type"] == "voice" else None)
        meta["announced"] = lines; meta["status"] = "done"
        json.dump(meta, open(base + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if c["email_enabled"] and c["email_to"] and (c["email_mode"] == "all" or meta["keywords"]):
            self.email(meta, base)

    def email(self, meta, base, test=False):
        c = self.cfg
        try:
            m = EmailMessage()
            m["From"] = c["smtp_user"] or "sanket-pi@localhost"; m["To"] = c["email_to"]
            kw = f" [ALERT: {', '.join(meta.get('keywords', []))}]" if meta.get("keywords") else ""
            m["Subject"] = f"Sanket PTT{kw}: {meta['channel']} - {meta['speaker']}"
            m.set_content(f"Channel: {meta['channel']}\nFrom: {meta['speaker']}\nTime: {meta['time']}\n"
                          f"Duration: {meta.get('duration_s', 0)} s\n\nTranscript:\n{meta.get('text') or '(none)'}\n\n-- {self.name()}")
            if base and os.path.exists(base + ".wav"):
                m.add_attachment(open(base + ".wav", "rb").read(), maintype="audio", subtype="wav", filename=os.path.basename(base) + ".wav")
            with smtplib.SMTP(c["smtp_host"], int(c["smtp_port"]), timeout=20) as s:
                if c["smtp_tls"]:
                    s.starttls()
                if c["smtp_user"]:
                    s.login(c["smtp_user"], c["smtp_password"])
                s.send_message(m)
            self.stats["emails"] += 1; log.info("email sent to %s", c["email_to"]); return "sent"
        except Exception as e:
            log.error("email failed: %s", e); return f"failed: {e}"

    # ---- feed / housekeeping
    def load_feed(self):
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
                if os.path.isfile(p) and os.path.getmtime(p) < (cut if d == self.dir else time.time() - 3600):
                    os.remove(p)

    def status(self):
        now = time.time()
        with self.lock:
            chans = []
            names = [c["name"] for c in self.cfg["channels"]]
            for ch in names + sorted(set(self.chs) - set(names)):
                S = self.chs.get(ch, {})
                en = ch in self.cfg.enabled()
                chans.append(dict(name=ch, enabled=en, listed=ch in names, monitored=ch in self.subs,
                                  online=sorted(u["name"] for u in S.get("users", {}).values()),
                                  talking=(S.get("floor") or {}).get("name"), last=S.get("last")))
        return dict(version=VERSION, name=self.name(), id=self.id, connected=self.connected, broker=re.sub(r"//.*@", "//", self.cfg["broker_url"]),
                    broker_error=self.broker_err, whisper=self.model_state if self.cfg["transcribe"] else "off",
                    queue=self.jobs.qsize(), channels=chans, stats=self.stats, uptime=int(now - self.stats["started"]),
                    host=socket.gethostname(), ips=ips(), port=self.cfg["web_port"])

    def run(self):
        threading.Thread(target=self.worker, daemon=True).start()
        self.connect(); self.purge()
        lb = lp = 0
        while not self.stop.is_set():
            now = time.time()
            if now - lb >= HB_S:
                lb = now; self.beat()
            if now - lp > 3600:
                lp = now; self.purge()
            with self.lock:
                for ch, S in self.chs.items():
                    for k in [k for k, v in S["users"].items() if now - v["seen"] > EXPIRE_S]:
                        del S["users"][k]
                    if S["floor"] and now - S["floor"]["seen"] > FLOOR_TIMEOUT_S:
                        S["floor"] = None; self.end_clip(ch, "silence")
            self.stop.wait(1)

    def shutdown(self):
        self.stop.set()
        try:
            for ch in self.subs:
                self.c.publish(self.T(ch, f"presence/{self.id}"), b"", retain=True)
            time.sleep(0.5); self.c.disconnect(); self.c.loop_stop()
        except Exception:
            pass


# ---------------------------------------------------------------- system info
def sh(cmd, t=10):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception:
        return ""


def ips():
    out = sh(["hostname", "-I"]).split()
    return [x for x in out if ":" not in x]


def audio_devices():
    devs = [{"id": "default", "label": "System default"}]
    for line in sh(["aplay", "-l"]).splitlines():
        m = re.match(r"card (\d+): (\S+) \[(.*?)\], device (\d+): .*?\[(.*?)\]", line)
        if m:
            devs.append({"id": f"plughw:{m.group(2)},{m.group(4)}", "label": f"{m.group(3)} - {m.group(5)}"})
    return devs


def voices():
    v = []
    for line in sh(["espeak-ng", "--voices"]).splitlines()[1:]:
        p = line.split()
        if len(p) >= 4:
            v.append({"id": p[1], "label": f"{p[3]} ({p[1]})"})
    pipers = []
    for d in (os.path.join(APP_DIR, "voices"), os.path.expanduser("~/piper")):
        if os.path.isdir(d):
            pipers += [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".onnx")]
    return {"espeak": v or [{"id": "en", "label": "English (en)"}, {"id": "hi", "label": "Hindi (hi)"}], "piper": pipers}


def wifi():
    info = {"ssid": sh(["iwgetid", "-r"]), "ips": ips(), "host": socket.gethostname()}
    if shutil.which("nmcli"):
        info["networks"] = [l.split(":") for l in sh(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"], 20).splitlines() if l.split(":")[0]][:20]
        info["active"] = sh(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "con", "show", "--active"])
    return info


# ---------------------------------------------------------------- web
def make_handler(app, cfg):
    page = os.path.join(APP_DIR, "web", "index.html")

    class H(BaseHTTPRequestHandler):
        server_version = "SanketPTT"

        def log_message(self, *a):
            pass

        def send(self, code, body, ctype="application/json"):
            if not isinstance(body, (bytes, bytearray)):
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code); self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body)

        def authed(self):
            pin = cfg["web_pin"]
            return not pin or self.headers.get("X-Pin", "") == pin

        def do_GET(self):
            u = urlparse(self.path); p = u.path
            if p in ("/", "/index.html"):
                return self.send(200, open(page, "rb").read(), "text/html; charset=utf-8")
            if p == "/api/status":
                return self.send(200, app.status())
            if p == "/api/feed":
                return self.send(200, list(app.feed)[:100])
            if p == "/api/config":
                return self.send(200, dict(config=cfg.public(), known=KNOWN_CHANNELS, brokers=BROKERS, pin=bool(cfg["web_pin"])))
            if p == "/api/devices":
                return self.send(200, dict(audio=audio_devices(), voices=voices()))
            if p == "/api/wifi":
                return self.send(200, wifi())
            if p == "/api/logs":
                n = int(parse_qs(u.query).get("n", ["300"])[0])
                return self.send(200, "\n".join(list(LOG_RING)[-n:]).encode(), "text/plain; charset=utf-8")
            if p.startswith("/clips/"):
                f = os.path.basename(unquote(p[7:]))
                fp = os.path.join(app.dir, f)
                if f and os.path.isfile(fp):
                    return self.send(200, open(fp, "rb").read(), "audio/wav" if f.endswith(".wav") else "image/jpeg")
            self.send(404, {"error": "not found"})

        def do_POST(self):
            p = urlparse(self.path).path
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                body = {}
            if not self.authed():
                return self.send(403, {"error": "wrong PIN"})
            if p == "/api/config":
                old = (cfg["broker_url"], cfg["device_name"], json.dumps(cfg["channels"]), cfg["listen_all"], cfg["web_port"])
                cfg.update(body)
                new = (cfg["broker_url"], cfg["device_name"], json.dumps(cfg["channels"]), cfg["listen_all"], cfg["web_port"])
                if old[0] != new[0]:
                    threading.Thread(target=app.connect, daemon=True).start()
                elif old != new:
                    threading.Thread(target=app.sync_subs, daemon=True).start()
                log.info("settings saved from web page")
                return self.send(200, {"ok": True, "restart_needed": old[4] != new[4], "config": cfg.public()})
            if p == "/api/test":
                ch = (cfg.enabled() or ["virtual"])[0].replace("-", " ")
                text = body.get("text") or f"This is a Sanket PTT test announcement. New message on {ch}."
                threading.Thread(target=app.speaker.say, args=([text],), daemon=True).start()
                return self.send(200, {"ok": True, "text": text})
            if p == "/api/test_email":
                r = app.email(dict(channel="test", speaker=app.name(), time=dt.datetime.now().isoformat(timespec="seconds"),
                                   text="Test email from the Sanket PTT Pi listener.", keywords=[]), None)
                return self.send(200, {"ok": r == "sent", "result": r})
            if p == "/api/replay":
                f = os.path.basename(body.get("wav", ""))
                fp = os.path.join(app.dir, f)
                if os.path.isfile(fp):
                    threading.Thread(target=app.speaker.say, args=([], fp), daemon=True).start()
                    return self.send(200, {"ok": True})
                return self.send(404, {"error": "no such clip"})
            if p == "/api/restart":
                log.warning("restart requested from web page")
                self.send(200, {"ok": True}); threading.Timer(1, restart, args=(app,)).start(); return
            if p == "/api/update":
                r = update_app(); self.send(200, r)
                if r.get("ok"):
                    threading.Timer(1, restart, args=(app,)).start()
                return
            if p == "/api/wifi":
                ssid, pw = body.get("ssid", ""), body.get("password", "")
                if not ssid:
                    return self.send(400, {"error": "ssid required"})
                cmd = ["sudo", "-n", "nmcli", "dev", "wifi", "connect", ssid] + (["password", pw] if pw else [])
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                log.info("wifi connect %s: %s", ssid, (r.stdout or r.stderr).strip())
                return self.send(200, {"ok": r.returncode == 0, "result": (r.stdout or r.stderr).strip()})
            if p == "/api/clear_feed":
                app.feed.clear(); return self.send(200, {"ok": True})
            self.send(404, {"error": "not found"})
    return H


def restart(app):
    app.shutdown()
    os._exit(3)   # systemd Restart=always brings us back with new settings/code


def update_app():
    import urllib.request
    got = []
    try:
        for f in APP_FILES:
            data = urllib.request.urlopen(f"{REPO_RAW}/{f}?t={int(time.time())}", timeout=30).read()
            if f.endswith(".py"):
                compile(data, f, "exec")
            dst = os.path.join(APP_DIR, f); os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst + ".new", "wb").write(data); got.append(dst)
        for dst in got:
            os.replace(dst + ".new", dst)
        pip = os.path.join(APP_DIR, "venv/bin/pip")
        if os.path.exists(pip):
            subprocess.run([pip, "install", "-q", "-r", os.path.join(APP_DIR, "requirements.txt")], timeout=900)
        log.info("updated %d files from %s", len(got), REPO_RAW)
        return {"ok": True, "files": [os.path.relpath(g, APP_DIR) for g in got]}
    except Exception as e:
        log.error("update failed: %s", e)
        return {"ok": False, "error": str(e)}


def main():
    cfg = Config(CFG_PATH)
    d = os.path.expanduser(cfg["clips_dir"]); os.makedirs(d, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    log.setLevel(logging.INFO)
    for h in (logging.StreamHandler(sys.stdout), RingHandler(),
              logging.handlers.RotatingFileHandler(os.path.join(d, "sanket_pi.log"), maxBytes=2_000_000, backupCount=3, encoding="utf-8")):
        h.setFormatter(fmt); log.addHandler(h)
    app = SanketPi(cfg)
    port = int(os.environ.get("SANKET_PORT") or cfg["web_port"])
    srv = ThreadingHTTPServer(("0.0.0.0", port), make_handler(app, cfg))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    log.info("Sanket PTT %s web page: http://%s.local:%d  (%s)", VERSION, socket.gethostname(), port,
             ", ".join(f"http://{i}:{port}" for i in ips()))
    import signal
    signal.signal(signal.SIGTERM, lambda *a: (app.shutdown(), os._exit(0)))
    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown()


if __name__ == "__main__":
    main()
