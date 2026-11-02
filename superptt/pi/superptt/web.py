"""Console + API. Safe to expose through Cloudflare Tunnel:
- only "/" (static console shell), /api/login, /api/session and LAN-only /api/setup are unauthenticated
- PIN stored as PBKDF2 hash; per-IP + global lockout; HttpOnly SameSite=Strict session cookie (Secure via tunnel)
- via tunnel: HTTPS enforced (redirect + HSTS); workers and setup are LAN-only
- /api/directory needs a session or the read-only directory token"""
import base64, hashlib, hmac, ipaddress, json, logging, os, secrets, threading, time, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
HERE = os.path.dirname(__file__); log = logging.getLogger("web")
CH_OK = __import__("re").compile(r"^[a-z0-9_-]{1,40}$")

def qr_svg(text):
    """QR code as inline SVG markup (needs the `qrcode` package; None if missing)"""
    try:
        import qrcode
        q = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M); q.add_data(text); q.make(fit=True)
        m = q.get_matrix(); n = len(m)
        path = "".join(f"M{x},{y}h1v1h-1z" for y, row in enumerate(m) for x, v in enumerate(row) if v)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" width="240" height="240" shape-rendering="crispEdges">'
                f'<rect width="{n}" height="{n}" fill="#fff"/><path d="{path}" fill="#000"/></svg>')
    except Exception: return None

def strip_userinfo(url):
    u = urlparse(url or "")
    if not u.password or (u.username == "public" and u.password == "public"): return url   # shiftr public login is not a secret
    return u._replace(netloc=u.hostname + (f":{u.port}" if u.port else "")).geturl()

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
    btun = Tunnel({"public_url": "", "tunnel_metrics": "http://127.0.0.1:20242"})   # private-broker quick tunnel (if any)
    def client_broker():
        if cfg["client_broker_url"]: return cfg["client_broker_url"]
        if cfg["broker_user"]:                     # private broker behind a quick tunnel
            h = btun.get(); return h.replace("https://", "wss://") if h else ""
        return strip_userinfo(cfg["broker_url"])
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
                # key material is NEVER served here: phones get keys out-of-band (QR / invite link fragment)
                return self.js({"broker_url": client_broker(), "broker_auth": bool(cfg["broker_user"]), "prefix": cfg["prefix"],
                                "channels": [{"id": c["channel"], "priority": c["priority"], "encrypted": c["encrypted"]}
                                             for c in app.ingest.snapshot()]})
            if not self.sess(): return self.js({"error": "auth"}, 401)
            if u.path == "/api/status":
                self.js({"connected": app.ingest.connected, "channels": app.ingest.snapshot(),
                         "stt_queue": app.stt.qlen(), "stt_busy": app.stt.busy, "stt_stats": app.stt.stats,
                         "leased": len(app.stt.leased), "output": cfg["output"], "config": cfg.public(),
                         "public_url": tunnel.get(), "tx": app.ingest.tx_state(), "via_tunnel": self.via_tunnel(), "time": time.time(),
                         "e2e": app.ingest.stats, "keys": app.keys.public(), "client_broker_url": client_broker()})
            elif u.path == "/api/audit":
                self.js(app.store.audit_log(int((q.get("limit") or [200])[0])))
            elif u.path == "/api/keys":
                self.js(app.keys.public())
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
                app.store.audit(ip, "setup", "admin PIN set, tokens issued")
                return self.js({"ok": 1, "worker_token": cfg["worker_token"], "directory_token": cfg["directory_token"]},
                               cookie=self.new_session())
            if self.path == "/api/login":
                if not cfg["admin_pin"]: return self.js({"error": "setup"}, 428)
                w = guard.blocked(ip)
                if w > 0: return self.js({"error": "locked", "retry_s": int(w)}, 429)
                if check_pin(str(b.get("pin") or ""), cfg["admin_pin"]):
                    guard.ok(ip)
                    if not cfg["admin_pin"].startswith("pbkdf2$"): cfg.update({"admin_pin": hash_pin(str(b["pin"]))})
                    app.store.audit(ip, "login", "ok" + (" via tunnel" if self.via_tunnel() else " LAN"))
                    return self.js({"ok": 1}, cookie=self.new_session())
                guard.fail(ip); app.store.audit(ip, "login_failed", "locked" if guard.blocked(ip) > 0 else "bad pin")
                time.sleep(0.5); return self.js({"error": "bad pin"}, 403)
            s = self.sess()
            if not s: return self.js({"error": "auth"}, 401)
            if self.headers.get("X-Requested-With") != "superptt": return self.js({"error": "csrf"}, 403)
            if self.path == "/api/tx/start":
                chs = b.get("channels") or "all"
                if b.get("cutin"): app.store.audit(ip, "tx_cutin", f"channels={chs if chs == 'all' else ','.join(map(str, chs))[:200]}")
                return self.js(app.ingest.tx_start(chs if chs == "all" else [str(c) for c in chs][:200], bool(b.get("cutin")),
                                                   str(b.get("name") or "Control Room")[:40]))
            if self.path == "/api/tx/stop":
                app.ingest.tx_stop(); return self.js({"ok": 1})
            if self.path == "/api/logout":
                sessions.pop(s, None); app.store.audit(ip, "logout"); return self.js({"ok": 1}, cookie="")
            if self.path == "/api/pin":
                if not check_pin(str(b.get("old") or ""), cfg["admin_pin"]):
                    guard.fail(ip); app.store.audit(ip, "pin_change_failed"); return self.js({"error": "bad pin"}, 403)
                p = str(b.get("new") or "")
                if len(p) < 6 or not p.isdigit() or len(set(p)) < 3: return self.js({"error": "weak"}, 400)
                cfg.update({"admin_pin": hash_pin(p)}); sessions.clear(); app.store.audit(ip, "pin_changed", "all sessions logged out")
                return self.js({"ok": 1}, cookie="")
            if self.path == "/api/tokens":     # reveal / rotate tokens (logged-in only)
                if b.get("rotate") not in (None, "worker_token", "directory_token"): return self.js({"error": "token"}, 400)
                app.store.audit(ip, "token_rotate" if b.get("rotate") else "token_reveal", b.get("rotate") or "")
                if b.get("rotate"):
                    cfg.update({b["rotate"]: secrets.token_hex(16) if b["rotate"] == "worker_token" else secrets.token_urlsafe(16)})
                return self.js({"worker_token": cfg["worker_token"], "directory_token": cfg["directory_token"]})
            if self.path == "/api/retention":
                r = {k: float(b[k]) for k in ("audio_days", "transcript_days", "min_free_pct") if k in b}
                if any(v < 0 for v in r.values()) or r.get("min_free_pct", 10) > 50: return self.js({"error": "range"}, 400)
                cfg.update({"retention": r}); app.store.audit(ip, "retention", json.dumps(r) + (" +cleanup" if b.get("run_now") else ""))
                if b.get("run_now"): app.retention.run_once()
                return self.js(app.retention.info())
            if self.path == "/api/cloud":      # set provider/key; key never returned
                c = {k: b[k] for k in ("enabled", "provider", "api_key", "model", "url", "langs", "when_queue_over",
                                       "min_avg_logprob") if k in b}
                if c.get("api_key") in ("***", None, ""): c.pop("api_key", None)
                if c.get("provider") not in (None, "openai", "elevenlabs", "google"): return self.js({"error": "provider"}, 400)
                cfg.update({"cloud": c})
                app.store.audit(ip, "cloud_stt", "provider=%s key=%s" % (c.get("provider", cfg["cloud"]["provider"]), "changed" if c.get("api_key") else "unchanged"))
                return self.js(cfg.public()["cloud"])
            if self.path == "/api/output": cfg.update({"output": b}); return self.js(cfg["output"])
            if self.path == "/api/config":
                for k in ("admin_pin", "worker_token", "directory_token", "tunnel_metrics", "data_dir",
                          "broker_url", "broker_user", "broker_pass", "client_broker_url"): b.pop(k, None)   # broker: use /api/broker
                app.store.audit(ip, "config", ",".join(sorted(b))[:200])
                if isinstance(b.get("cloud"), dict) and b["cloud"].get("api_key") == "***": b["cloud"].pop("api_key")
                cfg.update(b)
                for ch in cfg["channels"]: app.ingest.watch(ch)
                return self.js(cfg.public())
            if self.path == "/api/broker":     # custom / private broker; password never returned
                url = str(b.get("broker_url") or "").strip()
                if not url.startswith(("ws://", "wss://")): return self.js({"error": "broker_url must be ws:// or wss://"}, 400)
                upd = {"broker_url": url, "broker_user": str(b.get("broker_user") or "")[:64],
                       "client_broker_url": str(b.get("client_broker_url") or "").strip()}
                if b.get("broker_pass") not in (None, "", "***"): upd["broker_pass"] = str(b["broker_pass"])[:128]
                if not upd["broker_user"]: upd["broker_pass"] = ""
                cfg.update(upd); app.ingest.reconnect()
                app.store.audit(ip, "broker", "url=%s user=%s password=%s" % (strip_userinfo(url), upd["broker_user"] or "-",
                                "changed" if "broker_pass" in upd and upd["broker_pass"] else "unchanged"))
                return self.js({"ok": 1, "client_broker_url": client_broker()})
            if self.path == "/api/keys":       # add | rotate | remove a channel key
                ch, act = str(b.get("channel") or "").lower(), b.get("action")
                if not CH_OK.match(ch): return self.js({"error": "channel"}, 400)
                if act in ("add", "rotate"):
                    if act == "add" and ch in app.keys.d: return self.js({"error": "exists, use rotate"}, 409)
                    hide = bool(b.get("hide")) if "hide" in b else bool((app.keys.d.get(ch) or {}).get("hide"))
                    kid = app.keys.set(ch, hide)
                    if ch not in cfg["channels"]: cfg.update({"channels": cfg["channels"] + [ch]})
                    app.store.audit(ip, "key_" + act, f"{ch} kid={kid} hidden_topic={hide} fp={app.keys.public()[app.keys.channels().index(ch)]['fingerprint']}")
                elif act == "remove":
                    if not app.keys.remove(ch): return self.js({"error": "nf"}, 404)
                    app.store.audit(ip, "key_remove", f"{ch} -> channel is now NOT encrypted")
                else: return self.js({"error": "action"}, 400)
                app.ingest.rekey(ch)
                return self.js(app.keys.public())
            if self.path == "/api/keys/invite":   # secret goes only into the URL fragment (#), shown to the logged-in admin
                chs = [str(c).lower() for c in (b.get("channels") or [])][:50]
                chs = [c for c in chs if c in app.keys.d]
                if not chs: return self.js({"error": "no encrypted channel selected"}, 400)
                frag = "k=" + ",".join(f"{c}.{app.keys.d[c]['kid']}.{app.keys.secret(c)}" + (".h" if app.keys.d[c]["hide"] else "") for c in chs)
                from urllib.parse import quote
                if b.get("broker", True) and cfg["broker_user"] and client_broker(): frag += "&b=" + quote(client_broker(), safe="")
                link = cfg["app_url"].split("#")[0] + "#" + frag
                app.store.audit(ip, "key_invite", "channels=" + ",".join(chs))
                return self.js({"link": link, "qr_svg": qr_svg(link)})
            self.js({"error": "nf"}, 404)
    s = ThreadingHTTPServer(("0.0.0.0", int(cfg["http_port"])), H); s.daemon_threads = True
    return s
