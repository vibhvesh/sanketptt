"""MQTT ingest compatible with Sanket PTT. Splits audio into per-(channel,speaker) streams."""
import json, logging, re, threading, time, uuid
from urllib.parse import urlparse
import numpy as np
import paho.mqtt.client as mqtt
from . import e2e
log = logging.getLogger("ingest")
CH_RE = re.compile(r"^[a-z0-9_-]{1,40}$")

class Stream:
    def __init__(self, ch, sid, name):
        self.ch, self.sid, self.name = ch, sid, name
        self.t0 = time.time(); self.last = self.t0; self.chunks = []
    def add(self, pcm): self.chunks.append(pcm); self.last = time.time()
    def samples(self): return np.concatenate(self.chunks) if self.chunks else np.zeros(0, np.int16)

class Ingest:
    def __init__(self, cfg, on_segment, on_audio, keys=None):
        self.cfg, self.on_segment, self.on_audio = cfg, on_segment, on_audio
        self.keys = keys; self.replay = e2e.Replay(); self.seq = 0; self.tmap = {}; self.segs = {}
        self.stats = {k: 0 for k in ("ok", "nokey", "wrongkey", "auth", "replay", "stale", "plain", "malformed", "spoof")}
        self.id = "superptt-cr-" + uuid.uuid4().hex[:6]
        self.lock = threading.Lock()
        self.streams = {}        # (ch,sid) -> Stream
        self.channels = {}       # ch -> {"users":{id:{name,seen}}, "floor":..., "last":ts}
        self.subs = set(); self.connected = False
        self._mk()

    def _mk(self):
        cfg = self.cfg; u = urlparse(cfg["broker_url"])
        self.c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.id, transport="websockets")
        user, pw = cfg.get("broker_user") or u.username, cfg.get("broker_pass") or u.password
        if user: self.c.username_pw_set(user, pw)
        if u.scheme == "wss": self.c.tls_set()
        self.c.ws_set_options(path=u.path or "/")
        self.host, self.port = u.hostname, u.port or (443 if u.scheme == "wss" else 80)
        self.c.on_connect = self._conn; self.c.on_message = self._msg
        self.c.on_disconnect = lambda *a: setattr(self, "connected", False)

    # ---------- control-room talk-back ----------
    CUTIN_PRIO = 9
    def tx_start(self, channels, cutin=False, name="Control Room"):
        now = time.time(); ok, busy = [], []
        with self.lock:
            targets = sorted(self.subs) if channels == "all" else [c for c in channels if c in self.subs]
            for ch in targets:
                f = self.channels.get(ch, {}).get("floor")
                if f and f["id"] != self.id and now - f["ts"] < 2.5 and not cutin:
                    busy.append(ch); continue
                ok.append(ch)
            self.tx = {"chs": ok, "cutin": cutin, "name": name, "ts": 1 if cutin else int(now * 1000),
                       "prio": self.CUTIN_PRIO if cutin else 5, "last": now}
        for ch in ok:
            self.pub(ch, "presence", "presence/" + self.id, json.dumps({"id": self.id, "name": name, "ts": int(now * 1000), "sp": 1}), retain=True)
            self._floor(ch, "claim")
            if cutin: self._floor(ch, "hb")
        if not getattr(self, "_txt", None):
            self._txt = threading.Thread(target=self._tx_loop, daemon=True); self._txt.start()
        log.info("talk-back start %s cutin=%s busy=%s", ok, cutin, busy)
        return {"ok": ok, "busy": busy}
    def _floor(self, ch, t):
        x = self.tx; m = {"t": t, "id": self.id, "name": x["name"], "ts": x["ts"], "prio": x["prio"]}
        if len(x["chs"]) > 1: m["allcall"] = 1
        self.pub(ch, "floor", "floor", json.dumps(m))
    def tx_audio(self, raw):
        x = getattr(self, "tx", None)
        if not x or not x["chs"]: return 0
        x["last"] = time.time()
        if len(raw) % 2: raw = raw[:-1]
        hdr = bytes([len(self.id)]) + self.id.encode("latin1")
        for i in range(0, len(raw), 1200):            # 50 ms frames
            fr = hdr + raw[i:i + 1200]
            for ch in x["chs"]: self.pub(ch, "audio", "audio", fr)
        return len(x["chs"])
    def tx_stop(self):
        x = getattr(self, "tx", None); self.tx = None
        if not x: return
        for ch in x["chs"]:
            self.pub(ch, "floor", "floor", json.dumps({"t": "release", "id": self.id}))
            self.c.publish(self.T(ch, "presence/" + self.id), "", retain=True)
        log.info("talk-back stop")
    def _tx_loop(self):
        while True:
            time.sleep(1)
            x = getattr(self, "tx", None)
            if not x: continue
            if time.time() - x["last"] > 3: self.tx_stop(); continue   # safety: mic stream died
            for ch in x["chs"]: self._floor(ch, "hb")
    def tx_state(self):
        x = getattr(self, "tx", None); return {"active": bool(x), "channels": x["chs"] if x else [], "cutin": x["cutin"] if x else False}

    def start(self):
        self.c.connect_async(self.host, self.port, keepalive=20); self.c.loop_start()
        threading.Thread(target=self._reaper, daemon=True).start()
    def reconnect(self):
        """broker settings changed in the console"""
        try: self.c.loop_stop(); self.c.disconnect()
        except Exception: pass
        self.connected = False; self._mk(); self.c.connect_async(self.host, self.port, keepalive=20); self.c.loop_start()

    # ---------- E2E ----------
    def key(self, ch): return self.keys.get(ch) if self.keys else None
    def seg(self, ch): K = self.key(ch); return K.topic if K else ch
    def T(self, ch, s): return f'{self.cfg["prefix"]}{self.seg(ch)}/{s}'
    def pub(self, ch, kind, sub, data, retain=False):
        K = self.key(ch)
        if isinstance(data, str): data = data.encode()
        if K and data:
            with self.lock: self.seq += 1; seq = self.seq
            data = e2e.seal(K, kind, self.id, seq, data)
        self.c.publish(self.T(ch, sub), data, retain=retain)
    def rekey(self, ch):
        """call after a key was added / rotated / removed for ch"""
        old = self.segs.get(ch)
        if ch in self.subs and old is not None:
            self.c.unsubscribe([f'{self.cfg["prefix"]}{old}/{x}' for x in ("floor", "audio", "sstv")])
            self.subs.discard(ch)
        self.tmap = {self.seg(c): c for c in (self.keys.channels() if self.keys else [])}
        self.watch(ch)
    def _reject(self, reason): self.stats[reason] = self.stats.get(reason, 0) + 1

    def _conn(self, c, u, f, rc, p=None):
        self.connected = True; self.subs.clear()
        self.tmap = {self.seg(c): c for c in (self.keys.channels() if self.keys else [])}
        # presence wildcard = discovery of all channels
        c.subscribe(self.cfg["prefix"] + "+/presence/+")
        for ch in self.cfg["channels"]: self.watch(ch)
        for ch in (self.keys.channels() if self.keys else []): self.watch(ch)
        log.info("connected %s", self.host)

    def watch(self, ch):
        if ch in self.subs or not CH_RE.match(ch): return
        self.subs.add(ch); self.segs[ch] = self.seg(ch)
        self.c.subscribe([(self.T(ch, "floor"), 0), (self.T(ch, "audio"), 0), (self.T(ch, "sstv"), 0)])
        self.channels.setdefault(ch, {"users": {}, "floor": None, "last": 0})
        log.info("monitoring %s", ch)

    def _msg(self, c, u, m):
        t = m.topic
        if not t.startswith(self.cfg["prefix"]): return
        seg, _, s = t[len(self.cfg["prefix"]):].partition("/")
        ch = self.tmap.get(seg, seg)
        if not CH_RE.match(ch): return
        now = time.time(); K = self.key(ch); kind = "presence" if s.startswith("presence/") else s
        p = m.payload
        if K:
            if seg != K.topic: return                         # plaintext topic of an encrypted channel
            if p:
                if not e2e.is_sealed(p): return self._reject("plain")
                if p[4:4 + p[3]].decode("latin1", "replace") == self.id and kind != "floor": return
                try: sid, p = e2e.open_(K, kind, p, self.replay)
                except e2e.Rejected as ex: return self._reject(str(ex))
                try:
                    if kind == "presence": assert s[9:] == sid
                    elif kind == "audio": assert p[1:1 + p[0]].decode("latin1") == sid
                    else: assert json.loads(p).get("id") == sid
                except Exception: return self._reject("spoof")
                self.stats["ok"] += 1
        elif p and e2e.is_sealed(p): return self._reject("nokey")
        with self.lock:
            C = self.channels.setdefault(ch, {"users": {}, "floor": None, "last": 0})
            if s.startswith("presence/"):
                uid = s[9:]
                if not p: C["users"].pop(uid, None); return
                try:
                    j = json.loads(p)
                    if now * 1000 - j.get("ts", 0) < 60000:
                        C["users"][uid] = {"name": str(j.get("name"))[:40], "seen": now}
                except Exception: return
                if self.cfg["listen_all"] and ch not in self.subs:
                    self.watch(ch)
            elif s == "floor":
                try: j = json.loads(p)
                except Exception: return
                if j.get("t") in ("claim", "hb"):
                    C["floor"] = {"id": j.get("id"), "name": str(j.get("name"))[:40], "ts": now}
                    nm = str(j.get("name"))[:40]
                    for (c2, sid), st in self.streams.items():
                        if c2 == ch and sid == j.get("id"): st.name = nm
                elif j.get("t") == "release":
                    if C["floor"] and C["floor"]["id"] == j.get("id"): C["floor"] = None
                    self._close(ch, j.get("id"))
            elif s == "audio":
                if len(p) < 2: return
                n = p[0]; sid = p[1:1 + n].decode("latin1", "replace")
                raw = p[1 + n:]
                if len(raw) % 2: raw = raw[:-1]
                pcm = np.frombuffer(raw, "<i2").copy()
                key = (ch, sid)
                st = self.streams.get(key)
                if not st:
                    name = (C["users"].get(sid) or C["floor"] or {}).get("name") or sid
                    if sid == self.id: name = (getattr(self, "tx", None) or {}).get("name", "Control Room")
                    st = self.streams[key] = Stream(ch, sid, name)
                st.add(pcm); C["last"] = now
                if sid != self.id: self.on_audio(ch, sid, pcm)   # never play our own talk-back (feedback)

    def _close(self, ch, sid):
        st = self.streams.pop((ch, sid), None)
        if st and st.chunks: self.on_segment(st)

    def _reaper(self):
        while True:
            time.sleep(0.25); now = time.time()
            with self.lock:
                for k, st in list(self.streams.items()):
                    if now - st.last > self.cfg["segment_gap_s"]: self._close(*k)

    def snapshot(self):
        now = time.time()
        with self.lock:
            out = []
            for ch, C in sorted(self.channels.items()):
                talkers = [st.name for (c2, _), st in self.streams.items() if c2 == ch]
                out.append({"channel": ch, "monitored": ch in self.subs,
                            "users": [u["name"] for u in C["users"].values() if now - u["seen"] < 60],
                            "talking": talkers, "overlap": len(talkers) > 1,
                            "encrypted": ({"kid": self.key(ch).kid, "hide": self.key(ch).hide} if self.key(ch) else None),
                            "priority": self.cfg["priority"].get(ch, 0)})
            return out
