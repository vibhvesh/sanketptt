"""Sanket PTT relay over MQTT/WSS, same topics as the web radio:
  ptt-radio-66ab9178/<channel>/{presence/<id>,floor,audio,sstv}
  audio = [n][id bytes][Int16LE PCM @ 12 kHz]; floor = {"t":"claim|hb|release","id","name"}.
Receive-only: publishes only retained presence, unless a local input explicitly forwards a clip (off by default).
Auto-reconnects forever (paho back-off + a watchdog that rebuilds the client if it stays down)."""
import json, os, random, string, threading, time
from urllib.parse import urlparse, unquote
import numpy as np
from .util import RATE, clean_ch, log

PREFIX = "ptt-radio-66ab9178/"
HB_S, EXPIRE_S, FLOOR_TIMEOUT_S = 5.0, 15.0, 2.5
MIN_CLIP_S, MAX_CLIP_S, SSTV_META_S = 0.4, 60.0, 180.0
STALE_RECONNECT_S = 60


class RelayClient:
    def __init__(self, get_opts, on_clip, name_fn, on_discover=None):
        """get_opts() -> dict(broker_url, channels:[names], listen_all, discover)"""
        self.get_opts, self.on_clip, self.name_fn, self.on_discover = get_opts, on_clip, name_fn, on_discover
        self.id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.lock = threading.RLock(); self.chs = {}
        self.c, self.subs, self.connected, self.err = None, set(), False, ""
        self.down_since, self.reconnects, self.level = time.time(), 0, -90.0
        self.broker = ""

    def T(self, ch, s):
        return f"{PREFIX}{ch}/{s}"

    def st(self, ch):
        return self.chs.setdefault(ch, dict(users={}, floor=None, clip=None, sstv={}, last=None))

    # ---- connection
    def connect(self):
        import paho.mqtt.client as mqtt
        self.close(quiet=True)
        o = self.get_opts(); self.broker = o["broker_url"]
        self.subs, self.connected = set(), False
        u = urlparse(self.broker)
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"ptt_{self.id}_{int(time.time()*1000)%1000000}",
                        transport="websockets" if u.scheme in ("ws", "wss") else "tcp", clean_session=True)
        if u.scheme in ("ws", "wss"):
            c.ws_set_options(path=u.path or "/")
        if u.scheme in ("wss", "mqtts"):
            c.tls_set()
        if u.username:
            c.username_pw_set(unquote(u.username), unquote(u.password or ""))
        c.reconnect_delay_set(1, 30)
        c.on_connect, c.on_message, c.on_disconnect = self._on_connect, self._on_message, self._on_disconnect
        self.c = c
        port = u.port or {"wss": 443, "ws": 80, "mqtts": 8883}.get(u.scheme, 1883)
        log.info("relay: connecting %s://%s:%d as %s", u.scheme, u.hostname, port, self.name_fn())
        try:
            c.connect_async(u.hostname, port, keepalive=20); c.loop_start()
        except Exception as e:
            self.err = str(e); log.error("relay: %s", e)

    def close(self, quiet=False):
        if not self.c:
            return
        try:
            for ch in self.subs:
                self.c.publish(self.T(ch, f"presence/{self.id}"), b"", retain=True)
            if not quiet:
                time.sleep(0.3)
            self.c.disconnect(); self.c.loop_stop()
        except Exception:
            pass
        self.c, self.connected = None, False

    def _on_connect(self, c, ud, flags, rc, props=None):
        if rc != 0:
            self.err = str(rc); log.error("relay refused: %s", rc); return
        self.connected, self.err, self.subs, self.down_since = True, "", set(), None
        o = self.get_opts()
        if o.get("listen_all") or o.get("discover"):
            c.subscribe(PREFIX + "+/presence/+", 0)
        self.sync_subs(); log.info("relay connected; monitoring %s", ", ".join(sorted(self.subs)) or "(none)")

    def _on_disconnect(self, c, ud, flags, rc, props=None):
        if self.connected:
            log.warning("relay disconnected (%s) - auto-reconnecting", rc)
        self.connected = False; self.down_since = self.down_since or time.time()

    def wanted(self):
        o = self.get_opts(); w = set(o["channels"])
        if o.get("listen_all"):
            w |= {ch for ch, s in self.chs.items() if s["users"]}
        return w

    def sync_subs(self):
        if not self.connected or not self.c:
            return
        want = self.wanted()
        for ch in want - self.subs:
            self.c.subscribe([(self.T(ch, s), 0) for s in ("presence/+", "floor", "audio", "sstv")])
        for ch in self.subs - want:
            self.c.publish(self.T(ch, f"presence/{self.id}"), b"", retain=True)
            self.c.unsubscribe([self.T(ch, s) for s in ("presence/+", "floor", "audio", "sstv")])
        self.subs = want; self.beat()

    def beat(self):
        if self.connected and self.c:
            for ch in self.get_opts()["channels"]:
                self.c.publish(self.T(ch, f"presence/{self.id}"),
                               json.dumps({"id": self.id, "name": self.name_fn(), "ts": int(time.time() * 1000)}), retain=True)

    # ---- receive
    def _on_message(self, c, ud, msg):
        try:
            self.handle(msg.topic, msg.payload)
        except Exception as e:
            log.exception("relay message error: %s", e)

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
                if self.on_discover:
                    self.on_discover(ch)
                o = self.get_opts()
                if ch not in self.subs and (o.get("listen_all") or ch in o["channels"]):
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
                if len(i16):
                    self.level = float(20 * np.log10(np.sqrt(np.mean((i16 / 32768.0) ** 2)) + 1e-9))
                if not S["clip"]:
                    S["clip"] = dict(id=uid, name=f["name"], t=now, chunks=[], n=0)
                S["clip"]["chunks"].append(i16); S["clip"]["n"] += len(i16)
                if S["clip"]["n"] >= MAX_CLIP_S * RATE:
                    self.end_clip(ch, "60 s limit")

    def end_clip(self, ch, why):
        S = self.st(ch)
        k, S["clip"] = S["clip"], None
        if not k or not k["n"] or k["n"] / RATE < MIN_CLIP_S:
            return
        sm = S["sstv"].pop(k["id"], None)
        sm = sm if sm and time.time() - sm["_rx"] < SSTV_META_S else None
        S["last"] = time.time()
        self.on_clip(dict(channel=ch, speaker=k["name"], t=k["t"], i16=np.concatenate(k["chunks"]), rate=RATE, sstv_meta=sm))

    def tick(self):
        """Called every second: heartbeat, expire users, end silent clips, rebuild a dead client."""
        now = time.time()
        with self.lock:
            for ch, S in self.chs.items():
                for k in [k for k, v in S["users"].items() if now - v["seen"] > EXPIRE_S]:
                    del S["users"][k]
                if S["floor"] and now - S["floor"]["seen"] > FLOOR_TIMEOUT_S:
                    S["floor"] = None; self.end_clip(ch, "silence")
        if not self.connected and self.down_since and now - self.down_since > STALE_RECONNECT_S:
            self.reconnects += 1; self.down_since = now
            log.warning("relay down >%ds - rebuilding connection", STALE_RECONNECT_S)
            threading.Thread(target=self.connect, daemon=True).start()
        if self.get_opts()["broker_url"] != self.broker:
            threading.Thread(target=self.connect, daemon=True).start(); self.broker = self.get_opts()["broker_url"]

    # ---- optional transmit (only used when a local input has forward=True)
    def send_clip(self, ch, i16, rate):
        from .util import resample
        if not self.connected:
            return False
        x = resample(i16, rate, RATE).astype(np.int16) if rate != RATE else i16
        idb = self.id.encode("latin-1"); head = bytes([len(idb)]) + idb
        fl = lambda t: self.c.publish(self.T(ch, "floor"), json.dumps({"t": t, "id": self.id, "name": self.name_fn()}))
        fl("claim"); step = RATE // 10; t0 = time.time()
        for i in range(0, len(x), step):
            self.c.publish(self.T(ch, "audio"), head + x[i:i + step].astype("<i2").tobytes())
            if (i // step) % 10 == 0:
                fl("hb")
            time.sleep(max(0, t0 + (i + step) / RATE - time.time()))
        fl("release"); log.info("forwarded %.1fs clip to relay channel %s", len(x) / RATE, ch); return True

    def status(self):
        now = time.time()
        with self.lock:
            return dict(connected=self.connected, error=self.err, reconnects=self.reconnects,
                        channels={ch: dict(online=sorted(u["name"] for u in S["users"].values()),
                                           talking=(S.get("floor") or {}).get("name"), last=S.get("last"))
                                  for ch, S in self.chs.items()}, subs=sorted(self.subs), now=now)
