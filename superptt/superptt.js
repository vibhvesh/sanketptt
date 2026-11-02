/* SuperPTT core: multi-channel PTT over MQTT/WSS, wire-compatible with Sanket PTT.
   Topics: <prefix><channel>/{presence/<id>,floor,audio,sstv}; audio = [len][id][Int16LE PCM 12 kHz].
   Extensions (ignored by legacy clients): presence.sp=1, floor.prio (cut-in), floor.allcall.
   Works in browser (global SuperPTT) and Node (require). */
(function (root) {
  'use strict';
  var DEF_PREFIX = 'ptt-radio-66ab9178/';
  var BROKERS = ['wss://public:public@public.cloud.shiftr.io', 'wss://broker.emqx.io:8084/mqtt',
    'wss://broker.hivemq.com:8884/mqtt', 'wss://test.mosquitto.org:8081'];
  var RATE = 12000, HB_MS = 5000, EXPIRE_MS = 15000, FLOOR_TIMEOUT_MS = 2500, CLAIM_GRACE_MS = 700, CUTIN_PRIO = 9;
  var CH_RE = /^[a-z0-9_-]{1,40}$/;
  function noop() {}
  function rid() { return Math.random().toString(36).slice(2, 10); }
  function beats(a, b) { return a.ts < b.ts || (a.ts === b.ts && (a.name + a.id) < (b.name + b.id)); }

  function Client(mqttLib, o) {
    o = o || {}; var S = this;
    S.mqtt = mqttLib; S.prefix = o.prefix || DEF_PREFIX; S.brokers = o.brokers || BROKERS;
    S.id = o.id || rid(); S.name = String(o.name || 'Unit').slice(0, 40); S.prio = o.prio || 0;
    S.ch = {}; S.txSet = []; S.cb = o.on || noop; S.discover = !!o.discover; S.discovered = {};
    S.node = typeof window === 'undefined'; S.bi = 0; S.closed = false;
    S.connect(); S.timer = setInterval(function () { S.tick(); }, 1000);
  }
  var P = Client.prototype;
  P.T = function (ch, s) { return this.prefix + ch + '/' + s; };
  P.connect = function () {
    var S = this, url = S.brokers[S.bi % S.brokers.length], ok = false;
    var c = S.c = S.mqtt.connect(url, { clientId: 'sptt_' + S.id + '_' + Date.now() % 1e6, clean: true, keepalive: 20,
      reconnectPeriod: 0, connectTimeout: 8000 });
    c.on('connect', function () {
      ok = true; S.url = url; var subs = [];
      for (var k in S.ch) subs = subs.concat(S.subsFor(k));
      if (S.discover) subs.push(S.prefix + '+/presence/+');
      if (subs.length) c.subscribe(subs);
      for (var k2 in S.ch) S.beat(k2);
      S.cb('net', { connected: true, url: url });
    });
    c.on('message', function (t, p) { S.onMsg(t, p); });
    c.on('error', noop);
    c.on('close', function () {
      if (S.closed) return; S.cb('net', { connected: false }); if (!ok) S.bi++;
      setTimeout(function () { c.end(true); if (!S.closed) S.connect(); }, ok ? 1500 : 300);
    });
  };
  P.subsFor = function (ch) { return [this.T(ch, 'presence/+'), this.T(ch, 'floor'), this.T(ch, 'audio'), this.T(ch, 'sstv')]; };
  P.join = function (ch, opt) {
    ch = String(ch).toLowerCase(); if (!CH_RE.test(ch)) return false;
    opt = opt || {}; var C = this.ch[ch];
    if (!C) {
      C = this.ch[ch] = { name: ch, users: {}, floor: null, talking: false, active: {}, prio: opt.prio || 0,
        muted: !!opt.muted, vol: opt.vol == null ? 1 : opt.vol };
      if (this.c && this.c.connected) { this.c.subscribe(this.subsFor(ch)); this.beat(ch); }
    }
    this.emit(); return true;
  };
  P.leave = function (ch) {
    var C = this.ch[ch]; if (!C) return; if (C.talking) this.releaseCh(ch);
    if (this.c.connected) { this.c.publish(this.T(ch, 'presence/' + this.id), '', { retain: true }); this.c.unsubscribe(this.subsFor(ch)); }
    delete this.ch[ch]; this.txSet = this.txSet.filter(function (x) { return x !== ch; }); this.emit();
  };
  P.beat = function (ch) {
    var C = this.ch[ch]; if (!C || !this.c || !this.c.connected) return; C.lastBeat = Date.now();
    this.c.publish(this.T(ch, 'presence/' + this.id), JSON.stringify({ id: this.id, name: this.name, ts: Date.now(), sp: 1 }), { retain: true });
  };
  P.close = function () {
    var S = this; S.release();
    for (var k in S.ch) if (S.c.connected) S.c.publish(S.T(k, 'presence/' + S.id), '', { retain: true });
    S.closed = true; clearInterval(S.timer); var c = S.c; setTimeout(function () { c.end(); }, 300);
  };
  P.tick = function () {
    var S = this, now = Date.now(), ch = false;
    for (var k in S.ch) {
      var C = S.ch[k];
      if (!C.lastBeat || now - C.lastBeat >= HB_MS) S.beat(k);
      for (var u in C.users) if (now - C.users[u].seen > EXPIRE_MS) { delete C.users[u]; ch = true; }
      for (var a in C.active) if (now - C.active[a].t > 800) { delete C.active[a]; ch = true; }
      if (C.floor && C.floor.id !== S.id && now - C.floor.seen > FLOOR_TIMEOUT_MS) { C.floor = null; ch = true; }
      if (C.talking && C.floor && C.floor.id === S.id) S.pubFloor(k, 'hb');
    }
    if (ch) S.emit();
  };
  P.pubFloor = function (ch, t) {
    var C = this.ch[ch], f = C.floor, m = { t: t, id: this.id, name: this.name, ts: f ? f.ts : Date.now() };
    if (f && f.prio) m.prio = f.prio; if (f && f.allcall) m.allcall = 1;
    this.c.publish(this.T(ch, 'floor'), JSON.stringify(m));
  };
  P.onMsg = function (t, p) {
    var S = this, now = Date.now(); if (t.indexOf(S.prefix) !== 0) return;
    var rest = t.slice(S.prefix.length), i = rest.indexOf('/'), ch = rest.slice(0, i), s = rest.slice(i + 1), C = S.ch[ch];
    if (s.indexOf('presence/') === 0 && S.discover && p.length && CH_RE.test(ch) && !S.discovered[ch]) { S.discovered[ch] = now; S.cb('discover', ch); }
    if (!C) return;
    if (s.indexOf('presence/') === 0) {
      var uid = s.slice(9); if (uid === S.id) return;
      if (!p.length) { delete C.users[uid]; if (C.floor && C.floor.id === uid) C.floor = null; }
      else { try { var m = JSON.parse(p.toString()); if (now - m.ts < EXPIRE_MS * 4) C.users[uid] = { id: uid, name: String(m.name).slice(0, 40), seen: now, sp: !!m.sp }; } catch (e) {} }
      S.emit(); return;
    }
    if (s === 'floor') {
      var m2; try { m2 = JSON.parse(p.toString()); } catch (e) { return; }
      if (m2.id === S.id) { if (m2.t === 'claim' && S.echo && S.echo[ch] === 0) S.echo[ch] = now; return; }
      if (m2.t === 'claim' || m2.t === 'hb') {
        var f = C.floor, mp = +m2.prio || 0, fp = f ? (+f.prio || 0) : 0, take = false;
        if (!f || f.id === m2.id || mp > fp) take = true;
        else if (mp === fp && m2.t === 'claim' && now - f.got < CLAIM_GRACE_MS * 3 && beats(m2, f)) take = true;
        else if (mp === fp && m2.t === 'hb' && beats(m2, f)) take = true;
        if (take) {
          var prev = f;
          C.floor = { id: m2.id, name: String(m2.name).slice(0, 40), ts: m2.ts, prio: mp, allcall: !!m2.allcall, seen: now, got: f && f.id === m2.id ? f.got : now };
          if (prev && prev.id === S.id && C.talking) { C.talking = false; S.txSet = S.txSet.filter(function (x) { return x !== ch; });
            S.cb('preempted', { ch: ch, by: C.floor.name, prio: mp }); }
        }
        if (C.users[m2.id]) C.users[m2.id].seen = now;
      } else if (m2.t === 'release' && C.floor && C.floor.id === m2.id) C.floor = null;
      S.emit(); return;
    }
    if (s === 'sstv') { try { var q = JSON.parse(p.toString()); if (q && q.id !== S.id) S.cb('sstv', { ch: ch, msg: q }); } catch (e) {} return; }
    if (s === 'audio') {
      var b = p instanceof Uint8Array ? p : new Uint8Array(p), n = b[0], id = '';
      for (var j = 1; j <= n; j++) id += String.fromCharCode(b[j]);
      if (id === S.id) return;
      var holder = !!(C.floor && C.floor.id === id); if (holder) C.floor.seen = now;
      var pcmB = Uint8Array.prototype.slice.call(b, 1 + n), pcm = new Int16Array(pcmB.buffer, pcmB.byteOffset, pcmB.length >> 1);
      var u = C.users[id], nm = (holder && C.floor.name) || (u && u.name) || id;
      var was = Object.keys(C.active).length; C.active[id] = { t: now, name: nm, holder: holder };
      if (Object.keys(C.active).length !== was) S.emit();
      // every sender gets its own stream (no interleaving); non-holders are flagged as overlap
      S.cb('audio', { ch: ch, id: id, name: nm, pcm: pcm, holder: holder, prio: C.floor && holder ? C.floor.prio : 0 });
    }
  };
  /* Claim one or many channels. opts: {prio, cutin}. done({ok:[..], busy:[..]}) */
  P.claim = function (chs, opts, done) {
    var S = this; opts = opts || {}; chs = [].concat(chs).filter(function (c) { return S.ch[c]; });
    var prio = opts.cutin ? CUTIN_PRIO : (opts.prio || S.prio || 0), ok = [], busy = [], all = chs.length > 1;
    chs.forEach(function (ch) {
      var C = S.ch[ch], f = C.floor;
      if (f && f.id !== S.id && (+f.prio || 0) >= prio && !opts.cutin) { busy.push(ch); return; }
      if (f && f.id !== S.id && (+f.prio || 0) >= prio && opts.cutin && (+f.prio || 0) >= CUTIN_PRIO) { busy.push(ch); return; }
      var ts = prio >= CUTIN_PRIO ? 1 : Date.now();   // ts=1 also wins on legacy clients (earliest ts)
      C.floor = { id: S.id, name: S.name, ts: ts, prio: prio, allcall: all, seen: Date.now(), got: Date.now() };
      C.talking = true; S.pubFloor(ch, 'claim'); if (prio >= CUTIN_PRIO) S.pubFloor(ch, 'hb'); ok.push(ch);
    });
    S.emit();
    // Grace window adapts to broker latency: wait for our own claim to echo back (a rival claim sent at the
    // same moment arrives about as fast), plus a margin. Min CLAIM_GRACE_MS, max 2.5 s.
    S.echo = S.echo || {}; ok.forEach(function (ch) { S.echo[ch] = 0; });
    var t0 = Date.now(), margin = opts.cutin ? 100 : 250;
    (function wait() {
      var echoed = ok.every(function (ch) { return S.echo[ch] > 0; }), el = Date.now() - t0;
      var last = Math.max.apply(null, ok.map(function (ch) { return S.echo[ch] || 0; }).concat([0]));
      if (!ok.length || el >= 2500 || (echoed && Date.now() - last >= margin && el >= (opts.cutin ? 150 : CLAIM_GRACE_MS))) return fin();
      setTimeout(wait, 25);
    })();
    function fin() {
      var won = ok.filter(function (ch) { var C = S.ch[ch]; var w = C && C.talking && C.floor && C.floor.id === S.id; if (C && !w) C.talking = false; return w; });
      busy = busy.concat(ok.filter(function (c) { return won.indexOf(c) < 0; }));
      S.txSet = won; S.emit(); if (done) done({ ok: won, busy: busy });
    }
  };
  P.releaseCh = function (ch) {
    var C = this.ch[ch]; if (!C) return; C.talking = false;
    if (C.floor && C.floor.id === this.id) { this.c.publish(this.T(ch, 'floor'), JSON.stringify({ t: 'release', id: this.id })); C.floor = null; }
  };
  P.release = function () { for (var k in this.ch) if (this.ch[k].talking || (this.ch[k].floor && this.ch[k].floor.id === this.id)) this.releaseCh(k); this.txSet = []; this.emit(); };
  P.sendAudio = function (i16) {
    var S = this, sent = 0; if (!S.c.connected) return 0;
    var n = S.id.length, b = new Uint8Array(1 + n + i16.byteLength); b[0] = n;
    for (var i = 0; i < n; i++) b[1 + i] = S.id.charCodeAt(i);
    b.set(new Uint8Array(i16.buffer, i16.byteOffset, i16.byteLength), 1 + n);
    var payload = S.node && typeof Buffer !== 'undefined' ? Buffer.from(b) : b;
    S.txSet.forEach(function (ch) { var C = S.ch[ch]; if (C && C.talking && C.floor && C.floor.id === S.id) { S.c.publish(S.T(ch, 'audio'), payload); sent++; } });
    return sent;
  };
  P.snapshot = function () {
    var S = this, out = [];
    Object.keys(S.ch).sort().forEach(function (k) {
      var C = S.ch[k], talkers = Object.keys(C.active).map(function (a) { return C.active[a].name; });
      out.push({ name: k, prio: C.prio, muted: C.muted, vol: C.vol, users: Object.keys(C.users).map(function (u) { return C.users[u].name; }),
        floor: C.floor ? { id: C.floor.id, name: C.floor.name, prio: C.floor.prio, mine: C.floor.id === S.id, allcall: C.floor.allcall } : null,
        talkers: talkers, overlap: talkers.length > 1 || (talkers.length === 1 && C.floor && C.floor.id === S.id), tx: S.txSet.indexOf(k) >= 0 });
    });
    return out;
  };
  P.emit = function () { this.cb('state', this.snapshot()); };

  /* Mixer: one jitter buffer per (channel,sender) -> never interleaves two talkers; priority ducking; soft limit.
     render(n) returns Float32 at 12 kHz. Browser upsamples to the AudioContext rate. */
  function Mixer(o) { o = o || {}; this.bufs = {}; this.gain = {}; this.prebuf = o.prebuf || 960; this.duckDb = o.duckDb == null ? -12 : o.duckDb; this.master = 1; this.chanInfo = o.chanInfo || function () { return { vol: 1, muted: false, prio: 0 }; }; this.lastActive = {}; }
  Mixer.prototype.feed = function (ev) {
    var k = ev.ch + '|' + ev.id, B = this.bufs[k], f = new Float32Array(ev.pcm.length);
    for (var i = 0; i < f.length; i++) f[i] = ev.pcm[i] / 32768;
    if (!B) B = this.bufs[k] = { ch: ev.ch, q: [], n: 0, started: false, prio: ev.prio || 0 };
    B.q.push(f); B.n += f.length; B.prio = ev.prio || 0; B.t = Date.now();
    if (B.n > RATE * 4) { while (B.n > RATE * 2) B.n -= B.q.shift().length; } // cap latency
  };
  Mixer.prototype.render = function (n) {
    var out = new Float32Array(n), now = Date.now(), self = this, top = -1e9, live = {};
    Object.keys(this.bufs).forEach(function (k) { var B = self.bufs[k]; if (B.n > 0 && (B.started || B.n >= self.prebuf)) {
      var ci = self.chanInfo(B.ch), p = (ci.prio || 0) + (B.prio || 0); live[k] = p; if (p > top) top = p; } });
    var duck = Math.pow(10, this.duckDb / 20);
    Object.keys(this.bufs).forEach(function (k) {
      var B = self.bufs[k];
      if (!(k in live)) { if (B.n === 0 && now - (B.t || 0) > 3000) delete self.bufs[k]; else if (B.n === 0) B.started = false; return; }
      B.started = true; var ci = self.chanInfo(B.ch), target = ci.muted ? 0 : (ci.vol == null ? 1 : ci.vol) * (live[k] >= top ? 1 : duck);
      var g = self.gain[k] == null ? target : self.gain[k], i = 0;
      while (i < n && B.q.length) {
        var f = B.q[0], take = Math.min(f.length, n - i);
        for (var j = 0; j < take; j++) { g += (target - g) * (target < g ? 0.02 : 0.004); out[i + j] += f[j] * g; }
        i += take; B.n -= take; if (take === f.length) B.q.shift(); else B.q[0] = f.subarray(take);
      }
      self.gain[k] = g;
    });
    for (var x = 0; x < n; x++) out[x] = Math.tanh(out[x] * this.master * 1.2) / 1.2;
    return out;
  };
  Mixer.prototype.streams = function () { var self = this; return Object.keys(this.bufs).filter(function (k) { return self.bufs[k].n > 0; }); };

  function fetchDirectory(adminUrl, token) {
    var u = adminUrl.replace(/\/+$/, '') + '/api/directory?t=' + encodeURIComponent(token || '');
    return fetch(u, { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error('directory ' + r.status); return r.json(); });
  }

  var api = { Client: Client, Mixer: Mixer, fetchDirectory: fetchDirectory, RATE: RATE, BROKERS: BROKERS, DEF_PREFIX: DEF_PREFIX, CUTIN_PRIO: CUTIN_PRIO };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.SuperPTT = api;
})(this);
