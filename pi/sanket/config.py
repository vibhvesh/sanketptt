"""Settings stored in config.json. Backward compatible: old keys are kept, new keys get defaults."""
import json, os, threading, uuid
from .util import APP_DIR, clean_ch, log

CFG_PATH = os.environ.get("SANKET_CONFIG", os.path.join(APP_DIR, "config.json"))
KNOWN_CHANNELS = ["virtual", "master", "city-control", "unit-name"]
BROKERS = ["wss://public:public@public.cloud.shiftr.io", "wss://broker.emqx.io:8084/mqtt",
           "wss://broker.hivemq.com:8884/mqtt", "wss://test.mosquitto.org:8081"]
WEB_RADIO = "https://vibhvesh.github.io/sanketptt/"

DEFAULTS = {
    # identity + main relay (unchanged keys from v2)
    "device_name": "",
    "channels": [{"name": c, "enabled": True} for c in KNOWN_CHANNELS],
    "listen_all": True, "auto_add_discovered": True,
    "broker_url": BROKERS[0],
    "relay_enabled": True,
    # output
    "volume": 80, "audio_device": "default", "audio_backend": "auto",   # auto | alsa | pulse
    "play_audio": True, "announce": True, "announce_speaker": True, "announce_transcript": True,
    "announce_template": "New message on {channel} from {name}", "beep": True,
    "tts_engine": "espeak-ng", "espeak_voice": "en", "tts_speed": 150, "piper_model": "",
    # transcription
    "transcribe": True, "whisper_model": "base", "language": "auto",
    "keywords": ["mayday", "emergency", "fire", "help", "chetavani", "चेतावनी", "alert"],
    # sstv
    "sstv": True, "sstv_decode": True,
    # local / extra inputs (see inputs/registry.py). Each: {id,type,name,enabled,...}
    "inputs": [],
    # alerts
    "email_enabled": False, "email_mode": "keywords", "email_to": "", "smtp_host": "smtp.gmail.com",
    "smtp_port": 587, "smtp_user": "", "smtp_password": "", "smtp_tls": True,
    # system
    "web_port": 8080, "web_pin": "", "clips_dir": "~/sanket_clips", "retention_days": 7,
    "kiosk": True, "kiosk_browser": "chromium",
    "hw_profile": "",      # set once at first install from hw.py; never overrides user changes later
}
SECRET = ("smtp_password", "web_pin")
INPUT_KEYS = {"id", "type", "name", "enabled", "device", "vox_threshold", "vox_hang_s", "min_clip_s", "max_clip_s",
              "gain", "forward", "forward_channel", "url", "broker_url", "channel", "file", "interval_s",
              "freq_mhz", "mode", "squelch", "rf_gain", "sample_rate", "ppm", "device_index", "scan", "dwell_s", "preset",
              "bands", "bin_khz", "threshold_db", "allowlist", "allow_tol_khz", "speak_alerts"}


def _copy(x):
    return json.loads(json.dumps(x))


class Config:
    def __init__(self, path=CFG_PATH):
        self.path, self.lock, self.listeners = path, threading.RLock(), []
        self.d = _copy(DEFAULTS); self.file_keys = set()
        if os.path.exists(path):
            try:
                old = json.load(open(path, encoding="utf-8")); self.file_keys = set(old); self.d.update(old)
            except Exception as e:
                log.error("config.json unreadable, using defaults: %s", e)
        self.merge_known(); self.d["inputs"] = [self.clean_input(i) for i in self.d.get("inputs") or []]
        self.save()

    def merge_known(self):
        have = {c["name"] for c in self.d["channels"]}
        for c in KNOWN_CHANNELS:
            if c not in have:
                self.d["channels"].append({"name": c, "enabled": True})

    def apply_profile(self, key, profile, only_missing=False):
        """Board defaults. New install: all profile keys. Upgrade (only_missing): only keys the old
        config.json did not have yet, so nothing the user already set is changed. Runs once per board."""
        with self.lock:
            if self.d.get("hw_profile"):
                return False
            for k, v in profile.items():
                if not only_missing or k not in self.file_keys:
                    self.d[k] = v
            self.d["hw_profile"] = key; self.save(); return True

    def __getitem__(self, k):
        return self.d.get(k, DEFAULTS.get(k))

    def get(self, k, default=None):
        return self.d.get(k, default)

    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"
            json.dump(self.d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)

    def public(self):
        d = _copy(self.d)
        for k in SECRET:
            d[k + "_set"] = bool(d.get(k)); d[k] = ""
        return d

    @staticmethod
    def clean_input(i):
        o = {k: v for k, v in dict(i).items() if k in INPUT_KEYS}
        o["id"] = clean_ch(o.get("id")) or uuid.uuid4().hex[:8]
        o["type"] = str(o.get("type") or "alsa")
        o["name"] = str(o.get("name") or o["id"])[:40]
        o["enabled"] = bool(o.get("enabled", True))
        o["forward"] = bool(o.get("forward", False))           # receive-only by default
        for k, d in (("vox_threshold", -40.0), ("vox_hang_s", 1.2), ("min_clip_s", 0.6), ("max_clip_s", 60.0), ("gain", 1.0)):
            try:
                o[k] = float(o.get(k, d))
            except Exception:
                o[k] = d
        if o.get("channel"):
            o["channel"] = clean_ch(o["channel"])
        return o

    def update(self, new):
        with self.lock:
            changed = []
            if new.get("web_pin_clear"):
                self.d["web_pin"] = ""; changed.append("web_pin")
            for k, v in new.items():
                if k not in DEFAULTS:
                    continue
                if k in SECRET and v in ("", None):
                    continue
                if k == "channels":
                    seen, out = set(), []
                    for c in v:
                        n = clean_ch(c.get("name"))
                        if n and n not in seen:
                            seen.add(n); out.append({"name": n, "enabled": bool(c.get("enabled", True))})
                    v = out
                elif k == "inputs":
                    seen, out = set(), []
                    for i in v:
                        i = self.clean_input(i)
                        if i["id"] not in seen:
                            seen.add(i["id"]); out.append(i)
                    v = out
                t = type(DEFAULTS[k])
                if t is bool: v = bool(v)
                elif t is int: v = int(float(v))
                elif t is list and k == "keywords" and isinstance(v, str):
                    v = [x.strip() for x in v.split(",") if x.strip()]
                if self.d.get(k) != v:
                    changed.append(k)
                self.d[k] = v
            self.save()
        for fn in self.listeners:
            try:
                fn(changed)
            except Exception as e:
                log.error("config listener: %s", e)
        return changed

    def enabled(self):
        return [c["name"] for c in self.d["channels"] if c.get("enabled")]
