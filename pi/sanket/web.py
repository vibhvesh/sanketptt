"""HTTP server + JSON API for the web page / kiosk dashboard. Routes are a table; handlers stay small."""
import datetime as dt, json, os, shutil, subprocess, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from . import alerts, audio_io, bluetooth, inputs as inputs_mod
from .config import KNOWN_CHANNELS, BROKERS, WEB_RADIO
from .util import APP_DIR, LOG_RING, log, sh

WEB = os.path.join(APP_DIR, "web")
CTYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript", ".css": "text/css",
          ".wav": "audio/wav", ".jpg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml"}


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
    info = {"ssid": sh(["iwgetid", "-r"]), "ips": [x for x in sh(["hostname", "-I"]).split() if ":" not in x]}
    if shutil.which("nmcli"):
        info["networks"] = [l.split(":") for l in sh(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"], 20).splitlines() if l.split(":")[0]][:20]
    return info


def routes(app):
    cfg = app.cfg
    G = {
        "/api/status": lambda q, b: app.status(),
        "/api/feed": lambda q, b: app.store.list(100),
        "/api/config": lambda q, b: dict(config=cfg.public(), known=KNOWN_CHANNELS, brokers=BROKERS, pin=bool(cfg["web_pin"]), web_radio=WEB_RADIO),
        "/api/devices": lambda q, b: dict(audio=audio_io.output_devices(), inputs=audio_io.input_devices(), voices=voices()),
        "/api/dashboard": lambda q, b: dict(status=app.status(), sys=app.sysmon.snapshot(), metrics=app.metrics.snapshot(),
                                            storage=app.store.usage(), config=dash_config(app)),
        "/api/sysmon": lambda q, b: app.sysmon.snapshot(),
        "/api/metrics": lambda q, b: app.metrics.snapshot(),
        "/api/levels": lambda q, b: dict(levels=app.metrics.snapshot()["levels"], inputs=app.inputs.status()),
        "/api/input_types": lambda q, b: inputs_mod.types(),
        "/api/inputs": lambda q, b: dict(inputs=cfg["inputs"], status=app.inputs.status(), types=inputs_mod.types()),
        "/api/bt": lambda q, b: bluetooth.devices(),
        "/api/wifi": lambda q, b: wifi(),
        "/api/auth": lambda q, b: dict(required=app.auth.required()),
    }
    def save_cfg(q, b):
        cfg.update(b); log.info("settings saved from web page")
        return dict(ok=True, restart_needed="web_port" in b and int(b["web_port"]) != int(os.environ.get("SANKET_PORT") or app.port), config=cfg.public())
    def input_save(q, b):
        spec = cfg.clean_input(b); items = [i for i in cfg["inputs"] if i["id"] != spec["id"]]
        if spec["id"] == "relay":
            return dict(ok=False, error="'relay' is reserved for the main relay")
        if b.get("_delete"):
            cfg.update({"inputs": items}); return dict(ok=True, deleted=spec["id"])
        old = next((i for i, x in enumerate(cfg["inputs"]) if x["id"] == spec["id"]), None)
        if old is None: items.append(spec)
        else: items.insert(old, spec)
        cfg.update({"inputs": items}); return dict(ok=True, input=spec)
    def test(q, b):
        ch = (cfg.enabled() or ["virtual"])[0].replace("-", " ")
        text = b.get("text") or f"This is a Sanket PTT test announcement. New message on {ch}."
        threading.Thread(target=app.speaker.say, args=([text],), daemon=True).start(); return dict(ok=True, text=text)
    def replay(q, b):
        fp = app.store.path(b.get("wav"))
        if not fp:
            return 404, dict(error="no such clip")
        threading.Thread(target=app.speaker.say, args=([], fp), daemon=True).start(); return dict(ok=True)
    def wifi_join(q, b):
        ssid, pw = b.get("ssid", ""), b.get("password", "")
        if not ssid:
            return 400, dict(error="ssid required")
        r = subprocess.run(["sudo", "-n", "nmcli", "dev", "wifi", "connect", ssid] + (["password", pw] if pw else []), capture_output=True, text=True, timeout=60)
        return dict(ok=r.returncode == 0, result=(r.stdout or r.stderr).strip())
    def restart_(q, b):
        from .app import restart
        threading.Timer(1, restart, args=(app,)).start(); return dict(ok=True)
    def update_(q, b):
        from .app import update_app, restart
        r = update_app()
        if r.get("ok"):
            threading.Timer(1, restart, args=(app,)).start()
        return r
    P = {
        "/api/config": save_cfg, "/api/inputs": input_save, "/api/test": test, "/api/replay": replay,
        "/api/test_email": lambda q, b: (lambda r: dict(ok=r == "sent", result=r))(alerts.send(cfg, dict(channel="test", speaker=app.name(),
                            time=dt.datetime.now().isoformat(timespec="seconds"), text="Test email from the Sanket PTT Pi listener.", keywords=[]), None, app.name())),
        "/api/bt/scan": lambda q, b: bluetooth.scan(int(b.get("seconds", 10))),
        "/api/bt/action": lambda q, b: bluetooth.action(b.get("action"), b.get("mac")),
        "/api/wifi": wifi_join, "/api/restart": restart_, "/api/update": update_,
        "/api/clear_feed": lambda q, b: (app.store.clear(), dict(ok=True))[1],
    }
    return G, P


def dash_config(app):
    c = app.cfg; outs = {d["id"]: d["label"] for d in audio_io.output_devices_cached()}
    return dict(device_name=app.name(), channels=c.enabled(), broker=app.status()["broker"], listen_all=c["listen_all"],
                audio_out=outs.get(c["audio_device"], c["audio_device"]), volume=c["volume"],
                audio_in=[dict(name=i["name"], type=i["type"], device=i.get("device", ""), enabled=i["enabled"]) for i in c["inputs"]],
                model=app.hw["model"], profile=app.hw["profile"], whisper=c["whisper_model"] if c["transcribe"] else "off",
                tts=c["tts_engine"], sstv=("decode" if c["sstv_decode"] else "detect") if c["sstv"] else "off", version=app.version)


def make_handler(app):
    G, P = routes(app)

    class H(BaseHTTPRequestHandler):
        server_version = "SanketPTT"

        def log_message(self, *a):
            pass

        def send(self, code, body, ctype="application/json", extra=None):
            if not isinstance(body, (bytes, bytearray)):
                body = json.dumps(body, ensure_ascii=False, default=str).encode()
            self.send_response(code); self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers(); self.wfile.write(body)

        def static(self, root, name):
            f = os.path.basename(unquote(name)); fp = os.path.join(root, f)
            if f and os.path.isfile(fp):
                return self.send(200, open(fp, "rb").read(), CTYPES.get(os.path.splitext(f)[1], "application/octet-stream"))
            self.send(404, {"error": "not found"})

        def do_GET(self):
            u = urlparse(self.path); p = u.path; q = parse_qs(u.query)
            if p in ("/", "/index.html", "/kiosk"):
                return self.static(WEB, "index.html")
            if p.startswith("/web/"):
                return self.static(WEB, p[5:])
            if p.startswith("/clips/"):
                return self.static(app.store.dir, p[7:])
            if p == "/api/logs":
                n = int(q.get("n", ["300"])[0])
                return self.send(200, "\n".join(list(LOG_RING)[-n:]).encode(), "text/plain; charset=utf-8")
            fn = G.get(p)
            if fn:
                try:
                    return self.send(200, fn(q, {}))
                except Exception as e:
                    log.exception("GET %s", p); return self.send(500, {"error": str(e)})
            self.send(404, {"error": "not found"})

        def do_POST(self):
            p = urlparse(self.path).path
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                body = {}
            if p == "/api/login":
                tok = app.auth.login(body.get("pin"))
                if not tok:
                    return self.send(403, {"error": "wrong PIN"})
                return self.send(200, {"ok": True, "token": tok}, extra={"Set-Cookie": f"sanket_token={tok}; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200"})
            if p == "/api/logout":
                app.auth.logout(self.headers.get("X-Token", "")); return self.send(200, {"ok": True})
            if not app.auth.ok(self.headers):
                return self.send(403, {"error": "login required"})
            fn = P.get(p)
            if not fn:
                return self.send(404, {"error": "not found"})
            try:
                r = fn({}, body)
                code, r = r if isinstance(r, tuple) else (200, r)
                self.send(code, r)
            except Exception as e:
                log.exception("POST %s", p); self.send(500, {"error": str(e)})
    return H


def serve(app, port):
    app.port = port
    srv = ThreadingHTTPServer(("0.0.0.0", port), make_handler(app))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
