"""Wires the modules together. Nothing here knows how an input, TTS engine or web route works internally."""
import logging, logging.handlers, os, re, signal, socket, subprocess, sys, threading, time
from . import VERSION, hw
from .announce import Speaker
from .audio_io import Player
from .auth import Auth
from .config import Config, CFG_PATH
from .inputs import InputManager
from .metrics import Metrics
from .pipeline import Pipeline
from .sdnotify import notify
from .storage import Storage
from .sysmon import SysMon
from .transcribe import Transcriber
from .util import APP_DIR, RingHandler, log

REPO_RAW = "https://vibhvesh.github.io/sanketptt/pi"
MAIN_RELAY = "relay"


class App:
    def __init__(self, cfg):
        self.cfg, self.version = cfg, VERSION
        self.store = Storage(cfg)
        self.metrics = Metrics()
        self.player = Player(cfg, self.store.tmp, self.metrics)
        self.speaker = Speaker(cfg, self.store.tmp, self.player)
        self.stt = Transcriber(cfg)
        self.auth = Auth(cfg)
        self.sysmon = SysMon(self.store.dir)
        self.hw = hw.info()
        self.pipeline = Pipeline(cfg, self.store, self.speaker, self.stt, self.metrics, self.name, self.forward)
        self.inputs = InputManager(self, self.input_specs)
        self.stop = threading.Event()
        cfg.listeners.append(self.on_config)

    # ctx interface used by inputs
    def name(self):
        return (self.cfg["device_name"] or f"SanketPi-{socket.gethostname()}")[:40]

    def submit(self, clip):
        self.pipeline.submit(clip)

    def input_specs(self):
        main = dict(id=MAIN_RELAY, type="relay", name="Sanket PTT relay", main=True, enabled=self.cfg["relay_enabled"])
        return [main] + [s for s in self.cfg["inputs"] if s["id"] != MAIN_RELAY]

    def relay(self):
        r = self.inputs.get(MAIN_RELAY)
        return r.client if r else None

    def forward(self, ch, i16, rate):
        r = self.relay()
        return bool(r and r.send_clip(ch, i16, rate))

    def on_config(self, changed):
        if "inputs" in changed or "relay_enabled" in changed:
            self.inputs.reconcile()
        if set(changed) & {"channels", "listen_all", "auto_add_discovered", "device_name"} and self.relay():
            threading.Thread(target=self.relay().sync_subs, daemon=True).start()

    def status(self):
        r = self.relay(); rs = r.status() if r else dict(connected=False, error="relay off", channels={}, subs=[])
        names = [c["name"] for c in self.cfg["channels"]]; chans = []
        for ch in names + sorted(set(rs["channels"]) - set(names)):
            S = rs["channels"].get(ch, {})
            chans.append(dict(name=ch, enabled=ch in self.cfg.enabled(), listed=ch in names, monitored=ch in rs["subs"],
                              online=S.get("online", []), talking=S.get("talking"), last=S.get("last")))
        return dict(version=VERSION, name=self.name(), id=r.id if r else "", connected=rs["connected"],
                    broker=re.sub(r"//.*@", "//", self.cfg["broker_url"]), broker_error=rs.get("error", ""),
                    reconnects=rs.get("reconnects", 0), whisper=self.stt.status(), queue=self.pipeline.jobs.qsize(),
                    channels=chans, stats=self.pipeline.stats, uptime=int(time.time() - self.pipeline.stats["started"]),
                    host=socket.gethostname(), ips=self.sysmon.last.get("net", {}).get("ips", []), port=getattr(self, "port", self.cfg["web_port"]),
                    hw=self.hw, inputs=self.inputs.status(), speaking=self.speaker.busy, pin=self.auth.required())

    def run(self):
        threading.Thread(target=self.pipeline.worker, daemon=True).start()
        threading.Thread(target=self.sysmon.loop, args=(self.stop,), daemon=True).start()
        self.inputs.reconcile(); self.store.purge()
        notify("READY=1"); lp = time.time()
        while not self.stop.wait(10):
            notify("WATCHDOG=1")                     # systemd WatchdogSec: restart us if this loop hangs
            if time.time() - lp > 3600:
                lp = time.time(); self.store.purge()

    def shutdown(self):
        self.stop.set(); notify("STOPPING=1"); self.inputs.stop_all()
        r = self.relay()
        if r:
            r.close()


def restart(app):
    app.shutdown(); os._exit(3)          # systemd Restart=always brings us back


def update_app():
    """Pull every file listed in files.txt from Pages, verify Python compiles, then swap atomically."""
    import urllib.request
    got = []
    try:
        man = urllib.request.urlopen(f"{REPO_RAW}/files.txt?t={int(time.time())}", timeout=30).read().decode()
        files = [l.strip() for l in man.splitlines() if l.strip() and not l.startswith("#")]
        for f in files:
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


def setup_logging(cfg):
    d = os.path.expanduser(cfg["clips_dir"]); os.makedirs(d, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    log.setLevel(logging.INFO)
    for h in (logging.StreamHandler(sys.stdout), RingHandler(),
              logging.handlers.RotatingFileHandler(os.path.join(d, "sanket_pi.log"), maxBytes=2_000_000, backupCount=3, encoding="utf-8")):
        h.setFormatter(fmt); log.addHandler(h)


def main():
    from .web import serve
    cfg = Config(CFG_PATH)
    setup_logging(cfg)
    app = App(cfg)
    port = int(os.environ.get("SANKET_PORT") or cfg["web_port"])
    serve(app, port)
    log.info("Sanket PTT %s on %s (%s) web page: http://%s.local:%d", VERSION, app.hw["model"], app.hw["profile"],
             socket.gethostname(), port)
    signal.signal(signal.SIGTERM, lambda *a: (app.shutdown(), os._exit(0)))
    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown()
