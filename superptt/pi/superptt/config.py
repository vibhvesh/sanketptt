import json, os, copy
PREFIX = "ptt-radio-66ab9178/"
DEFAULTS = {
    "broker_url": "wss://public:public@public.cloud.shiftr.io",
    "prefix": PREFIX,
    "listen_all": True,          # auto-discover every channel seen via presence
    "channels": ["virtual"],     # always monitored
    "priority": {},              # channel -> int (higher wins ducking / STT queue)
    "data_dir": "./data",
    "rate": 12000,
    "segment_gap_s": 1.5,
    "min_segment_s": 0.4,
    "stt_engine": "faster-whisper",  # faster-whisper | vosk | none
    # Multilingual models only (never *.en). Tiered: quality when idle, base normally, tiny when overloaded.
    "whisper_model": "base",
    "quality_model": "small",       # used when queue is empty (better Hindi/Gujarati); "" to disable
    "fallback_model": "tiny",
    "whisper_threads": 2,
    "stt_workers": 2,
    "language": None,               # None = auto-detect per utterance
    "language_hints": {},           # channel -> ["gu","hi","en"]; detection restricted to these when unsure
    "hint_min_prob": 0.8,           # if detected lang prob < this and not in hints, use best hint
    "overload_queue": 6,            # queue length above which fallback_model is used
    "remote_workers": True,         # allow LAN workers (second Pi / PC / GPU) to pull jobs
    "worker_token": "",             # shared secret for LAN workers (set on first-run setup)
    "local_stt": True,              # set False to make the Pi record-only and rely on remote workers
    # Cloud = fallback only. Local Whisper always runs first (unless queue overflow).
    "cloud": {"enabled": True,      # routing on; nothing is sent until an api_key is set
              "provider": "elevenlabs",   # openai | elevenlabs | google
              "api_key": "", "model": "", "url": "", "timeout": 45,
              "langs": ["gu", "pa", "or", "as", "kn", "ml", "te", "ta", "mr", "bn", "ne", "si"],  # weak on small models
              "min_avg_logprob": -0.8, "max_no_speech": 0.6, "min_lang_prob": 0.5,
              "when_queue_over": 12, "retry_s": 300},
    "vosk_model_path": "",
    "output": {"mode": "all", "channels": [], "volume": 1.0, "duck_db": -12, "device": None},
    "http_port": 8090,
    "admin_pin": "",               # empty = must be set on first run via console
    "out_rate": 48000,
    "directory_token": "",          # read-only token for SuperPTT clients: /api/directory?t=...
    "session_hours": 12,
    "lockout": {"max_fail": 5, "window_s": 900, "lock_s": 900, "global_max_fail": 30},
    "tunnel_metrics": "http://127.0.0.1:20241",   # cloudflared --metrics; console shows the public URL
    "public_url": "",               # named-tunnel hostname (https://ptt.example.com) if used
    "retention": {"audio_days": 30, "transcript_days": 30, "min_free_pct": 10},
}
class Config:
    def __init__(self, path):
        self.path = path
        self.d = copy.deepcopy(DEFAULTS)
        if os.path.exists(path):
            with open(path) as f:
                self.update(json.load(f), save=False)
    def update(self, o, save=True):
        for k, v in o.items():
            if k in DEFAULTS:
                if isinstance(DEFAULTS[k], dict) and isinstance(v, dict):
                    self.d[k].update(v)
                else:
                    self.d[k] = v
        if save:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.d, f, indent=2)
            os.replace(tmp, self.path)
    def __getitem__(self, k): return self.d[k]
    def public(self):
        x = copy.deepcopy(self.d); x.pop("admin_pin", None); x.pop("worker_token", None); x.pop("directory_token", None)
        x["cloud"]["api_key"] = "***" if x["cloud"].get("api_key") else ""; from .cloud import api_key; x["cloud"]["key_set"] = bool(api_key(self.d["cloud"])); x["cloud"]["key_source"] = "config" if self.d["cloud"].get("api_key") else ("env" if x["cloud"]["key_set"] else ""); x["pin_set"] = bool(self.d["admin_pin"]); return x
