"""Console + API. Safe to expose through Cloudflare Tunnel:
- only "/" (static console shell), /api/login, /api/session and LAN-only /api/setup are unauthenticated
- PIN stored as PBKDF2 hash; per-IP + global lockout; HttpOnly SameSite=Strict session cookie (Secure via tunnel)
- via tunnel: HTTPS enforced (redirect + HSTS); workers and setup are LAN-only
- /api/directory needs a session or the read-only directory token"""
import base64, hashlib, hmac, ipaddress, json, logging, os, secrets, threading, time, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
HERE = os.path.dirname(__file__); log = logging.getLogger("web")

def hash_pin(pin, salt=None):
    salt = salt or secrets.token_hex(8)
    return "pbkdf2$%s$%s" % (salt, hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 200000).hex())
def check_pin(pin, stored):
    if not stored: return False
    if not stored.startswith("pbkdf2$"): return hmac.compare_digest(pin, stored)   # legacy plain
    _, salt, _h = stored.split("$"); return hmac.compare_digest(hash_pin(pin, salt), stored)

class Guard:
    def __init__(self, cfg): self.cfg, self.fails, self.locked, self.lock = cfg, {}, {}, threading.Lock()
    def blocked(self, ip):
        now = time.time()
        with self.lock:
            return max(self.locked.get(ip, 0), self.locked.get("*", 0)) - now
    def fail(self, ip):
        L = self.cfg["lockout"]; now = time.time()
        with self.lock:
            for k in (ip, "*"):
                f = [t for t in self.fails.get(k, []) if now - t < L["window_s"]] + [now]; self.fails[k] = f
            if len(self.fails[ip]) >= L["max_fail"]:
                n = len(self.fails[ip]) - L["max_fail"]
                self.locked[ip] = now + L["lock_s"] * (2 ** min(n, 5)); log.warning("login lockout %s", ip)
            if len(self.fails["*"]) >= L["global_max_fail"]:
                self.locked["*"] = now + 300; log.warning("global login lockout")
    def ok(self, ip):
        with self.lock: self.fails.pop(ip, None)

class Tunnel:
    """Reads the quick-tunnel hostname from cloudflared's metrics server."""
    def __init__(self, cfg): self.cfg, self.url, self.at = cfg, "", 0
    def get(self):
        if self.cfg["public_url"]: return self.cfg["public_url"]
        if time.time() - self.at > 30:
            self.at = time.time()
            try:
                j = json.loads(urllib.request.urlopen(self.cfg["tunnel_metrics"] + "/quicktunnel", timeout=1).read())
                h = j.get("hostname"); new = "https://" + h if h else ""
                if new and new != self.url: log.info("public console URL: %s", new)
                self.url = new
            except Exception: pass
        return self.url

def serve(app):
    cfg = app.cfg; sessions = {}; guard = Guard(cfg); tunnel = Tunnel(cfg); app.tunnel = tunnel
    class H(BaseHTTPRequestHandler):
        server_version = "SuperPTT"; sys_version = ""
        def log_message(self, *a): pass
        # ---- request context ----
        def via_tunnel(self):
            return "Cf-Connecting-Ip" in self.headers or "Cf-Ray" in self.headers
        def ip(self):
            if self.via_tunnel() and self.client_address[0] in ("127.0.0.1", "::1"):
                return self.headers.get("Cf-Connecting-Ip", "?")
            return self.client_address[0]
        def is_lan(self):
            if self.via_tunnel(): return False
            try: a = ipaddress.ip_address(self.client_address[0]); return a.is_private or a.is_loopback
            except ValueError: return False
        def sess(self):
            c = self.headers.get("Cookie") or ""
            for part in c.split(";"):
                k, _, v = part.strip().partition("=")
                if k == "sptsid" and v in sessions and sessions[v] > time.time(): return v
            return None
        def hdrs(self):
            self.send_header("X-Content-Type-Options", "nosniff"); self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer"); self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                             "style-src 'self' 'unsafe-inline'; media-src 'self'; frame-ancestors 'none'")
            if self.via_tunnel(): self.send_header("Strict-Transport-Security", "max-age=31536000")
        def js(self, o, code=200, cookie=None):
            b = json.dumps(o).encode(); self.send_response(code)
            self.send_header("Content-Type", "application/json"); self.hdrs()
            if getattr(self, "_cors", False): self.send_header("Access-Control-Allow-Origin", "*")
            if cookie is not None:
                sec = "; Secure" if self.via_tunnel() else ""
                age = int(cfg["session_hours"] * 3600) if cookie else 0
                self.send_header("Set-Cookie", f"sptsid={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age={age}{sec}")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def https_redirect(self):
            if self.via_tunnel() and self.headers.get("X-Forwarded-Proto", "https") != "https":
                self.send_response(301); self.send_header("Location", "https://" + (self.headers.get("Host") or "") + self.path)
                self.end_headers(); return True
            return False
        def new_session(self):
            t = secrets.token_urlsafe(32); sessions[t] = time.time() + cfg["session_hours"] * 3600
            for k in [k for k, v in sessions.items() if v < time.time()]: sessions.pop(k, None)
            return t
        def do_OPTIONS(self):
            self.send_response(204); self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET"); self.send_header("Access-Control-Allow-Headers", "X-Directory-Token")
            self.end_headers()
        # ---- GET ----
        def do_GET(self):
            if self.https_redirect(): return
            u = urlparse(self.path); q = parse_qs(u.query)
            if u.path == "/":
                b = open(os.path.join(HERE, "console.html"), "rb").read()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.hdrs()
                self.send_header("Content-Length", str(len(b))); self.end_headers(); return self.wfile.write(b)
            if u.path == "/api/session":
                return self.js({"auth": bool(self.sess()), "pin_set": bool(cfg["admin_pin"]),
                                "setup_allowed": not cfg["admin_pin"] and self.is_lan()})
            if u.path == "/api/directory":
                self._cors = True
                t = (q.get("t") or [""])[0] or self.headers.get("X-Directory-Token", "")
                if not (self.sess() or (cfg["directory_token"] and hmac.compare_digest(t, cfg["directory_token"]))):
                    return self.js({"error": "auth"}, 401)
                self._cors = True
                return self.js({"broker_url": cfg["broker_url"], "prefix": cfg["prefix"],
                                "channels": [{"id": c["channel"], "priority": c["priority"]} for c in app.ingest.snapshot()]})
            if not self.sess(): return self.js({"error": "auth"}, 401)
            if u.path == "/api/status":
                self.js({"connected": app.ingest.connected, "channels": app.ingest.snapshot(),
                         "stt_queue": app.stt.qlen(), "stt_busy": app.stt.busy, "stt_stats": app.stt.stats,
                         "leased": len(app.stt.leased), "output": cfg["output"], "config": cfg.public(),
                         "public_url": tunnel.get(), "tx": app.ingest.tx_state(), "via_tunnel": self.via_tunnel(), "time": time.time()})
            elif u.path == "/api/storage":
                self.js(app.retention.info())
            elif u.path == "/api/timeline":
                ch = q.get("channels", [""])[0]
                self.js(app.store.timeline(float(q.get("since", [0])[0]), ch.split(",") if ch else None))
            elif u.path.startswith("/rec/"):
                root = os.path.realpath(os.path.join(cfg["data_dir"], "rec"))
                p = os.path.realpath(os.path.join(root, u.path[5:]))
                if not p.startswith(root + os.sep) or not os.path.isfile(p): return self.js({"error": "nf"}, 404)
                b = open(p, "rb").read(); self.send_response(200); self.send_header("Content-Type", "audio/wav"); self.hdrs()
                self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            else: self.js({"error": "nf"}, 404)
        # ---- POST ----
        def do_POST(self):
            if self.https_redirect(): return
            n = min(int(self.headers.get("Content-Length") or 0), 256 * 1024)
            raw = self.rfile.read(n)
            if self.path == "/api/tx/audio":           # raw Int16LE 12 kHz from console mic
                if not self.sess() or self.headers.get("X-Requested-With") != "superptt": return self.js({"error": "auth"}, 401)
                return self.js({"sent": app.ingest.tx_audio(raw)})
            try: b = json.loads(raw or b"{}")
            except Exception: b = {}
            if not isinstance(b, dict): b = {}
            ip = self.ip()
            if self.path.startswith("/api/jobs/"):   # LAN offload workers only
                if not self.is_lan() or not cfg["remote_workers"] or not cfg["worker_token"] or \
                   not hmac.compare_digest(self.headers.get("X-Worker", ""), cfg["worker_token"]):
                    return self.js({"error": "worker auth"}, 403)
                if self.path == "/api/jobs/claim":
                    j = app.stt.claim()
                    if not j: return self.js({"job": None})
                    j["pcm"] = base64.b64encode(j["pcm"].tobytes()).decode(); return self.js({"job": j})
                if self.path == "/api/jobs/result":
                    return self.js({"ok": app.stt.result(int(b["id"]), b.get("text", ""), b.get("language"), b.get("engine", "remote"))})
                return self.js({"error": "nf"}, 404)
            if self.path == "/api/setup":      # forced first-run PIN, LAN only
                if cfg["admin_pin"]: return self.js({"error": "already set"}, 409)
                if not self.is_lan(): return self.js({"error": "first-run setup only from the local network"}, 403)
                pin = str(b.get("pin") or "")
                if len(pin) < 6 or not pin.isdigit() or len(set(pin)) < 3 or pin in "0123456789" or pin in "9876543210":
                    return self.js({"error": "PIN must be 6+ digits, not trivial"}, 400)
                cfg.update({"admin_pin": hash_pin(pin), "worker_token": secrets.token_hex(16),
                            "directory_token": secrets.token_urlsafe(16)})
                return self.js({"ok": 1, "worker_token": cfg["worker_token"], "directory_token": cfg["directory_token"]},
                               cookie=self.new_session())
            if self.path == "/api/login":
                if not cfg["admin_pin"]: return self.js({"error": "setup"}, 428)
                w = guard.blocked(ip)
                if w > 0: return self.js({"error": "locked", "retry_s": int(w)}, 429)
                if check_pin(str(b.get("pin") or ""), cfg["admin_pin"]):
                    guard.ok(ip)
                    if not cfg["admin_pin"].startswith("pbkdf2$"): cfg.update({"admin_pin": hash_pin(str(b["pin"]))})
                    return self.js({"ok": 1}, cookie=self.new_session())
                guard.fail(ip); time.sleep(0.5); return self.js({"error": "bad pin"}, 403)
            s = self.sess()
            if not s: return self.js({"error": "auth"}, 401)
            if self.headers.get("X-Requested-With") != "superptt": return self.js({"error": "csrf"}, 403)
            if self.path == "/api/tx/start":
                chs = b.get("channels") or "all"
                return self.js(app.ingest.tx_start(chs if chs == "all" else [str(c) for c in chs][:200], bool(b.get("cutin")),
                                                   str(b.get("name") or "Control Room")[:40]))
            if self.path == "/api/tx/stop":
                app.ingest.tx_stop(); return self.js({"ok": 1})
            if self.path == "/api/logout":
                sessions.pop(s, None); return self.js({"ok": 1}, cookie="")
            if self.path == "/api/pin":
                if not check_pin(str(b.get("old") or ""), cfg["admin_pin"]): guard.fail(ip); return self.js({"error": "bad pin"}, 403)
                p = str(b.get("new") or "")
                if len(p) < 6 or not p.isdigit() or len(set(p)) < 3: return self.js({"error": "weak"}, 400)
                cfg.update({"admin_pin": hash_pin(p)}); sessions.clear(); return self.js({"ok": 1}, cookie="")
            if self.path == "/api/tokens":     # reveal / rotate tokens (logged-in only)
                if b.get("rotate"):
                    cfg.update({b["rotate"]: secrets.token_hex(16) if b["rotate"] == "worker_token" else secrets.token_urlsafe(16)})
                return self.js({"worker_token": cfg["worker_token"], "directory_token": cfg["directory_token"]})
            if self.path == "/api/retention":
                r = {k: float(b[k]) for k in ("audio_days", "transcript_days", "min_free_pct") if k in b}
                if any(v < 0 for v in r.values()) or r.get("min_free_pct", 10) > 50: return self.js({"error": "range"}, 400)
                cfg.update({"retention": r})
                if b.get("run_now"): app.retention.run_once()
                return self.js(app.retention.info())
            if self.path == "/api/cloud":      # set provider/key; key never returned
                c = {k: b[k] for k in ("enabled", "provider", "api_key", "model", "url", "langs", "when_queue_over",
                                       "min_avg_logprob") if k in b}
                if c.get("api_key") in ("***", None, ""): c.pop("api_key", None)
                if c.get("provider") not in (None, "openai", "elevenlabs", "google"): return self.js({"error": "provider"}, 400)
                cfg.update({"cloud": c}); return self.js(cfg.public()["cloud"])
            if self.path == "/api/output": cfg.update({"output": b}); return self.js(cfg["output"])
            if self.path == "/api/config":
                for k in ("admin_pin", "worker_token", "directory_token", "tunnel_metrics", "data_dir"): b.pop(k, None)
                if isinstance(b.get("cloud"), dict) and b["cloud"].get("api_key") == "***": b["cloud"].pop("api_key")
                cfg.update(b)
                for ch in cfg["channels"]: app.ingest.watch(ch)
                return self.js(cfg.public())
            self.js({"error": "nf"}, 404)
    s = ThreadingHTTPServer(("0.0.0.0", int(cfg["http_port"])), H); s.daemon_threads = True
    return s
