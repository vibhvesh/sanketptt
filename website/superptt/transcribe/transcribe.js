/* SuperPTT Transcribe: listen-only web client. Reuses ../superptt.js (MQTT client + AES-256-GCM/HKDF E2E + invite parsing). */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var LS = localStorage, cfg = JSON.parse(LS.sptt_transcribe || '{}'), RATE = SuperPTT.RATE, GAP_MS = 1200;
  cfg.keys = cfg.keys || {};
  function save() { LS.sptt_transcribe = JSON.stringify(cfg); }
  // keys already imported into the SuperPTT app on this origin are reused (read-only)
  function allKeys() { var o = {}, a = {}; try { a = JSON.parse(LS.superptt || '{}').keys || {}; } catch (e) {}
    Object.keys(a).forEach(function (k) { o[k] = a[k]; }); Object.keys(cfg.keys).forEach(function (k) { o[k] = cfg.keys[k]; }); return o; }
  function importInvite(s) {
    var i = String(s || '').indexOf('#'), inv = SuperPTT.E2E.parseInvite(i >= 0 ? s.slice(i) : s), chs = chanList();
    inv.keys.forEach(function (k) { cfg.keys[k.ch] = { kid: k.kid, s: k.secret, hide: k.hide }; if (chs.indexOf(k.ch) < 0) chs.push(k.ch); });
    if (inv.broker) cfg.burl = inv.broker; cfg.chans = chs.join(', '); save(); return inv.keys.map(function (k) { return k.ch; });
  }
  function chanList() { return String(cfg.chans || '').split(/[\s,]+/).map(function (s) { return s.toLowerCase(); }).filter(Boolean); }
  if (location.hash.indexOf('k=') >= 0) { importInvite(location.hash); history.replaceState(null, '', location.pathname + location.search); }

  var segs = [], live = {}, cl = null, tab = 'all', state = [], rejects = {}, seq = 0, crTok = sessionStorage.sptt_crtok || cfg.crtok || '', crSince = 0, crTimer = null;

  // ---------- clip assembly from live MQTT audio ----------
  function onEv(t, v) {
    if (t === 'state') { state = v; renderTabs(); }
    else if (t === 'net') $('net').textContent = v.connected ? '● ' + v.url.replace(/^wss:\/\/([^@]*@)?/, '').split('/')[0] : '○ reconnecting';
    else if (t === 'reject') { var r = rejects[v.ch] = rejects[v.ch] || {}; r[v.reason] = (r[v.reason] || 0) + 1; renderTabs(); }
    else if (t === 'discover') { if (!cl.ch[v]) cl.join(v); }
    else if (t === 'audio') {
      var k = v.ch + '|' + v.id, L = live[k];
      if (!L) L = live[k] = { ch: v.ch, name: v.name, t0: Date.now(), parts: [], n: 0 };
      L.parts.push(new Int16Array(v.pcm)); L.n += v.pcm.length; L.last = Date.now(); if (v.name !== v.id) L.name = v.name;
    }
  }
  setInterval(function () {
    var now = Date.now();
    Object.keys(live).forEach(function (k) { var L = live[k]; if (now - L.last > GAP_MS || L.n > RATE * 60) { delete live[k]; closeClip(L); } });
    renderTabs();
  }, 300);
  function closeClip(L) {
    if (L.n < RATE * 0.3) return;                         // ignore blips < 0.3 s
    var pcm = new Int16Array(L.n), o = 0; L.parts.forEach(function (p) { pcm.set(p, o); o += p.length; });
    var s = { id: ++seq, ch: L.ch, name: L.name, t0: L.t0, t1: L.last, dur: L.n / RATE, url: URL.createObjectURL(wav(pcm)), pcm: pcm, status: 'wait', text: '', lang: '', engine: '' };
    segs.push(s); if (segs.length > 500) { var x = segs.shift(); if (x.url) URL.revokeObjectURL(x.url); }
    render(); if (!cfg.cr) queue(s);
  }
  function wav(pcm) {
    var b = new ArrayBuffer(44 + pcm.length * 2), d = new DataView(b), w = function (o, s) { for (var i = 0; i < s.length; i++) d.setUint8(o + i, s.charCodeAt(i)); };
    w(0, 'RIFF'); d.setUint32(4, 36 + pcm.length * 2, true); w(8, 'WAVEfmt '); d.setUint32(16, 16, true); d.setUint16(20, 1, true); d.setUint16(22, 1, true);
    d.setUint32(24, RATE, true); d.setUint32(28, RATE * 2, true); d.setUint16(32, 2, true); d.setUint16(34, 16, true); w(36, 'data'); d.setUint32(40, pcm.length * 2, true);
    new Int16Array(b, 44).set(pcm); return new Blob([b], { type: 'audio/wav' });
  }
  function to16k(pcm) {                                   // 12 kHz Int16 -> 16 kHz Float32 (linear)
    var n = Math.floor(pcm.length * 16000 / RATE), o = new Float32Array(n), r = RATE / 16000;
    for (var i = 0; i < n; i++) { var p = i * r, k = Math.floor(p), f = p - k, a = pcm[k] || 0, b = pcm[k + 1] == null ? a : pcm[k + 1]; o[i] = (a + (b - a) * f) / 32768; }
    return o;
  }
  function guessLang(t) { if (/[\u0A80-\u0AFF]/.test(t)) return 'gu'; if (/[\u0900-\u097F]/.test(t)) return 'hi'; if (/[\u0980-\u09FF]/.test(t)) return 'bn';
    if (/[\u0B80-\u0BFF]/.test(t)) return 'ta'; if (/[\u0C00-\u0C7F]/.test(t)) return 'te'; if (/[\u0A00-\u0A7F]/.test(t)) return 'pa'; if (/[\u0600-\u06FF]/.test(t)) return 'ur';
    return /[a-z]/i.test(t) ? 'en' : ''; }

  // ---------- browser STT: local Whisper worker or ElevenLabs ----------
  var Q = [], busy = false, worker = null, pend = {};
  function queue(s) { Q.push(s); pump(); }
  function pump() {
    if (busy || !Q.length) return; busy = true; var s = Q.shift(); s.status = 'run'; render();
    (cfg.eng === 'eleven' && LS.sptt_xi_key ? eleven(s) : whisper(s)).then(function (r) {
      s.text = r.text || '(no speech)'; s.lang = r.lang || (cfg.lang !== 'auto' ? cfg.lang : guessLang(s.text)); s.engine = r.engine; s.status = 'done';
    }, function (e) { s.status = 'err'; s.text = 'transcription failed: ' + (e && e.message || e); }).then(function () { s.pcm = null; busy = false; render(); pump(); });
  }
  function getWorker() {
    if (worker) return worker;
    worker = new Worker('whisper-worker.js', { type: 'module' });
    worker.onmessage = function (e) {
      var m = e.data;
      if (m.t === 'progress') { var p = m.p; if (p.status === 'progress' && p.file && /onnx/.test(p.file)) $('mode').textContent = 'loading model ' + Math.round(p.progress || 0) + '% (' + p.file.split('/').pop() + ')'; }
      else if (m.t === 'ready') setMode();
      else if (pend[m.id]) { var P = pend[m.id]; delete pend[m.id]; m.t === 'result' ? P.ok(m.text) : P.no(new Error(m.error)); }
    };
    return worker;
  }
  function whisper(s) {
    return new Promise(function (ok, no) { pend[s.id] = { ok: ok, no: no }; getWorker().postMessage({ t: 'run', id: s.id, model: cfg.model, lang: cfg.lang, audio: to16k(s.pcm) }); })
      .then(function (t) { return { text: t, engine: cfg.model.split('/').pop() }; });
  }
  function eleven(s) {
    var fd = new FormData(); fd.append('model_id', 'scribe_v1'); fd.append('file', wav(s.pcm), 'clip.wav');
    if (cfg.lang && cfg.lang !== 'auto') fd.append('language_code', cfg.lang);
    return fetch('https://api.elevenlabs.io/v1/speech-to-text', { method: 'POST', headers: { 'xi-api-key': LS.sptt_xi_key }, body: fd })
      .then(function (r) { if (!r.ok) throw new Error('ElevenLabs ' + r.status); return r.json(); })
      .then(function (j) { return { text: (j.text || '').trim(), lang: ({ eng: 'en', hin: 'hi', guj: 'gu' }[j.language_code] || j.language_code || ''), engine: 'elevenlabs' }; });
  }

  // ---------- control room (Pi) transcripts ----------
  function crBase() { return String(cfg.cr || '').replace(/\/+$/, ''); }
  function crFetch(p, o) { o = o || {}; o.headers = o.headers || {}; if (crTok) o.headers.Authorization = 'Bearer ' + crTok; o.credentials = 'omit'; return fetch(crBase() + p, o); }
  function crLogin() {
    cfg.cr = $('cr').value.trim(); save(); if (!cfg.cr) { setMode(); return; }
    $('serr').textContent = 'logging in…';
    fetch(crBase() + '/api/login', { method: 'POST', credentials: 'omit', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pin: $('pin').value }) })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || r.status); return j; }); })
      .then(function (j) { if (!j.token) throw new Error('control room is too old: update the Pi (needs cors_origins)'); crTok = sessionStorage.sptt_crtok = j.token; $('pin').value = ''; $('serr').textContent = '✓ logged in to control room'; crStart(); })
      .catch(function (e) { $('serr').textContent = 'login failed: ' + (e.message === 'Failed to fetch' ? 'unreachable or CORS blocked (update the Pi)' : e.message); });
  }
  function crStart() { clearInterval(crTimer); if (!cfg.cr || !crTok) return setMode(); crPoll(); crTimer = setInterval(crPoll, 4000); setMode(); }
  function crPoll() {
    var chs = chanList();
    crFetch('/api/timeline?since=' + crSince + (chs.length && !cfg.disc ? '&channels=' + encodeURIComponent(chs.join(',')) : '')).then(function (r) {
      if (r.status === 401) { crTok = ''; sessionStorage.removeItem('sptt_crtok'); clearInterval(crTimer); $('serr').textContent = 'control-room session expired, log in again'; setMode(); throw 0; }
      return r.json();
    }).then(function (rows) {
      rows.forEach(function (r) {
        var s = segs.filter(function (x) { return x.crid === r.id; })[0];
        if (!s) { s = { id: ++seq, crid: r.id, ch: r.channel, name: r.speaker, t0: r.t_start * 1000, t1: r.t_end * 1000, dur: r.t_end - r.t_start, wav: r.wav }; segs.push(s); }
        s.text = r.text || r.local_text || ''; s.lang = r.lang || guessLang(s.text); s.engine = r.engine || ''; s.status = r.status === 'done' || s.text ? 'done' : 'wait';
        if (s.status === 'done' && r.t_start > crSince - 600) crSince = Math.max(crSince, r.t_start - 120);   // keep re-reading the last 2 min for late results
      });
      segs.sort(function (a, b) { return a.t0 - b.t0; }); render();
    }).catch(function () {});
  }
  function crAudio(s, btn) {
    btn.textContent = '…';
    crFetch('/rec/' + s.wav.split('/').map(encodeURIComponent).join('/')).then(function (r) { if (!r.ok) throw new Error(r.status); return r.blob(); })
      .then(function (b) { s.url = URL.createObjectURL(b); render(); }).catch(function (e) { btn.textContent = 'audio ' + e.message; });
  }

  // ---------- UI ----------
  function setMode() {
    $('mode').textContent = cfg.cr && crTok ? 'transcripts: control room' : cfg.eng === 'eleven' && LS.sptt_xi_key ? 'transcripts: ElevenLabs (this browser)' : 'transcripts: ' + (cfg.model || '').split('/').pop() + ' in this browser';
  }
  function lockTag(c) {
    if (c.enc) return '🔒'; if (rejects[c.name] && rejects[c.name].nokey) return '<span class=nokey>🔒 key needed</span>'; return '';
  }
  function renderTabs() {
    var talk = {}; Object.keys(live).forEach(function (k) { talk[live[k].ch] = live[k].name; });
    $('tabs').innerHTML = '<button data-tab=all class="' + (tab === 'all' ? 'on' : '') + '">All</button>' + state.map(function (c) {
      return '<button data-tab="' + esc(c.name) + '" class="' + (tab === c.name ? 'on' : '') + '">' + esc(c.name) + ' ' + lockTag(c) + (talk[c.name] ? ' <span style=color:#ff6b6b>🔊 ' + esc(talk[c.name]) + '</span>' : '') + '</button>';
    }).join('');
  }
  function visible() {
    var q = $('q').value.trim().toLowerCase();
    return segs.filter(function (s) { return (tab === 'all' || s.ch === tab) && (!q || (s.text + ' ' + s.name + ' ' + s.ch).toLowerCase().indexOf(q) >= 0); });
  }
  function hl(t) { var q = $('q').value.trim(); if (!q) return esc(t); var i = t.toLowerCase().indexOf(q.toLowerCase()); return i < 0 ? esc(t) : esc(t.slice(0, i)) + '<mark>' + esc(t.slice(i, i + q.length)) + '</mark>' + esc(t.slice(i + q.length)); }
  function render() {
    var v = visible().slice().reverse();
    $('empty').classList.toggle('hide', v.length > 0);
    $('feed').innerHTML = v.slice(0, 300).map(function (s) {
      var tx = s.status === 'done' ? hl(s.text) : s.status === 'run' ? 'transcribing…' : s.status === 'err' ? esc(s.text) : 'queued…';
      return '<div class="seg ' + (s.status === 'done' ? '' : 'wait') + '"><div class=h><b>' + esc(s.name) + '</b><span class=pill>' + esc(s.ch) + '</span><span>' + new Date(s.t0).toLocaleString() + '</span><span>' + s.dur.toFixed(1) + ' s</span>' +
        (s.lang ? '<span class="pill lang">' + esc(s.lang.toUpperCase()) + '</span>' : '') + (s.engine ? '<span>' + esc(s.engine) + '</span>' : '') + '</div>' +
        '<div class=tx>' + tx + '</div>' + (s.url ? '<audio controls preload=none src="' + s.url + '"></audio>' : s.wav ? '<button data-audio="' + s.id + '">▶ load audio</button>' : '') + '</div>';
    }).join('');
  }
  $('feed').addEventListener('click', function (e) { var id = e.target.dataset.audio; if (id) crAudio(segs.filter(function (s) { return s.id === +id; })[0], e.target); });
  $('tabs').addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) { tab = b.dataset.tab; renderTabs(); render(); } });
  $('q').oninput = render;
  function stamp(t) { var d = new Date(t), p = function (n) { return ('0' + n).slice(-2); }; return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds()); }
  function download(name, text, type) { var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(['\ufeff' + text], { type: type })); a.download = name; a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000); }
  var fname = function (ext) { return 'superptt-transcript-' + stamp(Date.now()).replace(/[: ]/g, '-') + '.' + ext; };
  $('csv').onclick = function () {
    var c = function (x) { return '"' + String(x == null ? '' : x).replace(/"/g, '""') + '"'; };
    download(fname('csv'), ['time,channel,sender,duration_s,language,engine,text'].concat(visible().map(function (s) { return [stamp(s.t0), s.ch, s.name, s.dur.toFixed(1), s.lang, s.engine, s.text].map(c).join(','); })).join('\r\n'), 'text/csv');
  };
  $('txt').onclick = function () { download(fname('txt'), visible().map(function (s) { return '[' + stamp(s.t0) + '] #' + s.ch + ' ' + s.name + (s.lang ? ' (' + s.lang + ')' : '') + ': ' + s.text; }).join('\n'), 'text/plain'); };

  function start() {
    cfg.chans = $('chans').value; cfg.disc = $('disc').checked; cfg.burl = $('burl').value.trim(); cfg.buser = $('buser').value.trim(); cfg.bpass = $('bpass').value;
    cfg.eng = $('eng').value; cfg.model = $('model').value; cfg.lang = $('lang').value; cfg.cr = $('cr').value.trim();
    if ($('xik').value.trim()) { LS.sptt_xi_key = $('xik').value.trim(); $('xik').value = ''; $('xik').placeholder = 'ElevenLabs key saved in this browser'; }
    save(); var chs = chanList(); if (!chs.length && !cfg.disc) { $('serr').textContent = 'Enter at least one channel'; return; }
    if (cl) cl.close();
    var priv = !!(cfg.burl && cfg.buser);
    cl = new SuperPTT.Client(window.mqtt, { name: 'Transcribe', username: cfg.buser || undefined, password: cfg.bpass || undefined, discover: cfg.disc, on: onEv,
      brokers: cfg.burl ? (priv ? [cfg.burl] : [cfg.burl].concat(SuperPTT.BROKERS.filter(function (b) { return b !== cfg.burl; }))) : null });
    var K = allKeys();
    Promise.all(Object.keys(K).map(function (c) { return cl.setKey(c, K[c].s, K[c].kid, K[c].hide).catch(function () {}); }))
      .then(function () { chs.forEach(function (c) { cl.join(c); }); });
    $('setup').classList.add('hide'); setMode(); crStart();
    if (!cfg.cr && cfg.eng !== 'eleven') getWorker().postMessage({ t: 'load', model: cfg.model });   // warm the model
  }
  function keyInfo() { var k = Object.keys(allKeys()); $('keyinfo').textContent = k.length ? '🔒 keys in this browser: ' + k.join(', ') : 'No channel keys: paste the invite link or open it on this device.'; }
  $('addkey').onclick = function () { var got = importInvite($('invite').value); $('invite').value = ''; $('chans').value = cfg.chans; keyInfo(); $('serr').textContent = got.length ? '🔒 key added for ' + got.join(', ') : 'no key found in that text'; };
  $('login').onclick = crLogin;
  $('xiclr').onclick = function () { LS.removeItem('sptt_xi_key'); $('xik').placeholder = 'ElevenLabs API key (kept only in this browser)'; setMode(); };
  $('gear').onclick = function () { $('setup').classList.toggle('hide'); };
  $('go').onclick = start;
  // boot
  cfg.model = cfg.model || 'onnx-community/whisper-tiny'; cfg.lang = cfg.lang || 'auto'; cfg.eng = cfg.eng || 'whisper';
  $('chans').value = cfg.chans || ''; $('disc').checked = !!cfg.disc; $('burl').value = cfg.burl || ''; $('buser').value = cfg.buser || ''; $('bpass').value = cfg.bpass || '';
  $('eng').value = cfg.eng; $('model').value = cfg.model; $('lang').value = cfg.lang; $('cr').value = cfg.cr || '';
  if (LS.sptt_xi_key) $('xik').placeholder = 'ElevenLabs key saved in this browser';
  keyInfo(); renderTabs(); render(); setMode();
  if (chanList().length || cfg.disc) start(); else $('setup').classList.remove('hide');
  window.SPTTx = { segs: segs, onEv: onEv };   // test hook
})();
