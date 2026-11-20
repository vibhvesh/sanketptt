(function () {
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var LS = window.localStorage, cfg = JSON.parse(LS.superptt || '{}');
  var q = new URLSearchParams(location.search);            // deep link: ?admin=..&t=..&name=..
  if (q.get('admin')) { cfg.admin = q.get('admin'); cfg.dtok = q.get('t') || ''; }
  if (q.get('name')) cfg.name = q.get('name');
  // invite link: #k=<ch>.<kid>.<secret>[.h]&b=<broker>. The fragment never reaches any server; we store it locally and wipe it from the URL.
  cfg.keys = cfg.keys || {};
  var inv = SuperPTT.E2E.parseInvite(location.hash), invited = [];
  if (inv.keys.length) {
    inv.keys.forEach(function (k) { cfg.keys[k.ch] = { kid: k.kid, s: k.secret, hide: k.hide }; invited.push(k.ch);
      var m = (cfg.manual || '').split(/[\s,]+/).filter(Boolean); if (m.indexOf(k.ch) < 0) { m.push(k.ch); cfg.manual = m.join(', '); } });
    if (inv.broker) cfg.burl = inv.broker;
    history.replaceState(null, '', location.pathname + location.search);
  }
  var cl = null, mix = new SuperPTT.Mixer({ chanInfo: function (ch) { var C = cl && cl.ch[ch]; return C ? { vol: C.vol, muted: C.muted, prio: C.prio + (ch === cfg.tx ? 0.5 : 0) } : { vol: 1 }; } });
  var allSel = new Set(cfg.allsel || []), state = [], talking = false, ac, micStream, proc, outNode;
  var dirEnc = {}, rejects = {};
  function save() { cfg.allsel = Array.from(allSel); LS.superptt = JSON.stringify(cfg); }
  function log(s) { var li = document.createElement('li'); li.textContent = new Date().toLocaleTimeString() + '  ' + s; $('log').prepend(li); while ($('log').children.length > 40) $('log').lastChild.remove(); }

  // ---------- audio out: pull from mixer at 12 kHz, upsample to device rate ----------
  function audioInit() {
    if (ac) return; ac = new (window.AudioContext || window.webkitAudioContext)();
    var ratio = SuperPTT.RATE / ac.sampleRate, tail = 0, phase = 0;
    outNode = ac.createScriptProcessor(2048, 1, 1);
    outNode.onaudioprocess = function (e) {
      var o = e.outputBuffer.getChannelData(0), need = Math.ceil(o.length * ratio + phase) + 1, x = mix.render(need - 1), prev = tail;
      for (var i = 0; i < o.length; i++) { var p = phase + i * ratio, k = Math.floor(p), f = p - k, a = k === 0 ? prev : x[k - 1], b = x[k] == null ? a : x[k]; o[i] = a + (b - a) * f; }
      var used = phase + o.length * ratio; phase = used - Math.floor(used); tail = x[Math.floor(used) - 1] || 0;
    };
    outNode.connect(ac.destination);
  }
  // ---------- mic in: device rate -> 12 kHz Int16 frames ----------
  function micInit() {
    if (micStream) return Promise.resolve();
    return navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } }).then(function (s) {
      micStream = s; var src = ac.createMediaStreamSource(s); proc = ac.createScriptProcessor(2048, 1, 1);
      proc.onaudioprocess = function (e) {
        if (!talking) return; var i = e.inputBuffer.getChannelData(0), r = ac.sampleRate / SuperPTT.RATE, n = Math.floor(i.length / r), o = new Int16Array(n);
        for (var k = 0; k < n; k++) { var v = Math.max(-1, Math.min(1, i[Math.floor(k * r)])); o[k] = v < 0 ? v * 32768 : v * 32767; }
        cl.sendAudio(o);
      };
      src.connect(proc); var z = ac.createGain(); z.gain.value = 0; proc.connect(z); z.connect(ac.destination);
    });
  }
  // ---------- connect ----------
  function start(chs, brokerUrl, prefix, prioMap) {
    if (cl) cl.close();
    brokerUrl = cfg.burl || brokerUrl;
    var priv = !!(cfg.burl && cfg.buser);   // private broker with login: don't fall back to public brokers
    cl = new SuperPTT.Client(window.mqtt, { name: cfg.name, prefix: prefix, username: cfg.buser || undefined, password: cfg.bpass || undefined,
      brokers: brokerUrl ? (priv ? [brokerUrl] : [brokerUrl].concat(SuperPTT.BROKERS.filter(function (b) { return b !== brokerUrl; }))) : null,
      discover: !!cfg.disc, on: onEv });
    // keys first, then join (an encrypted channel never sends a plaintext packet)
    Promise.all(Object.keys(cfg.keys).map(function (c) { var k = cfg.keys[c]; return cl.setKey(c, k.s, k.kid, k.hide).catch(function () { log('bad key for ' + c); }); }))
      .then(function () { chs.forEach(function (c) { cl.join(c, { prio: (prioMap || {})[c] || 0 }); }); });
    if (!cfg.tx || chs.indexOf(cfg.tx) < 0) cfg.tx = chs[0]; save();
    $('me').textContent = cfg.name; $('setup').classList.add('hide'); render();
  }
  var online = false;
  function onEv(t, v) {
    if (t === 'state') { state = v; render(); }
    else if (t === 'audio') { mix.feed(v); }
    else if (t === 'reject') { var r = rejects[v.ch] = rejects[v.ch] || {}; r[v.reason] = (r[v.reason] || 0) + 1;
      if (r[v.reason] === 1) log('🔒 ' + v.ch + ': dropped ' + v.kind + ' packet (' + ({ nokey: 'encrypted, no key on this phone', wrongkey: 'key was rotated: ask for a new invite', auth: 'wrong key or tampered', replay: 'replayed', stale: 'too old / clock wrong', plain: 'unencrypted packet on encrypted channel' }[v.reason] || v.reason) + ')'); }
    else if (t === 'net') { online = !!v.connected; render(); $('net').textContent = v.connected ? '● ' + v.url.replace(/^wss:\/\/([^@]*@)?/, '').split('/')[0] : '○ reconnecting'; }
    else if (t === 'discover') { if (!cl.ch[v]) { cl.join(v, { muted: true }); log('discovered channel ' + v + ' (muted)'); } }
    else if (t === 'preempted') { log('⚠ ' + v.by + ' cut in on ' + v.ch); if (!cl.txSet.length) stopTx(); $('pst').textContent = 'Cut in by ' + v.by + ' on ' + v.ch; }
  }
  function connect() {
    cfg.name = ($('name').value || cfg.name || '').trim(); cfg.admin = $('admin').value.trim(); cfg.dtok = $('dtok').value.trim();
    cfg.manual = $('manual').value; cfg.disc = $('disc').checked;
    cfg.burl = $('burl').value.trim(); cfg.buser = $('buser').value.trim(); cfg.bpass = $('bpass').value; save();
    if (!cfg.name) { $('serr').textContent = 'Enter your name'; return; }
    var manual = (cfg.manual || '').split(/[\s,]+/).map(function (s) { return s.toLowerCase(); }).filter(Boolean);
    if (cfg.admin) {
      $('serr').textContent = 'Loading channels…';
      SuperPTT.fetchDirectory(cfg.admin, cfg.dtok).then(function (d) {
        var chs = d.channels.map(function (c) { return c.id; }), pm = {}; d.channels.forEach(function (c) { pm[c.id] = c.priority || 0; dirEnc[c.id] = c.encrypted; });
        manual.forEach(function (m) { if (chs.indexOf(m) < 0) chs.push(m); });
        log('control room: ' + chs.length + ' channels'); start(chs, d.broker_url, d.prefix, pm);
      }).catch(function (e) { $('serr').textContent = 'Control room unreachable (' + e.message + '), using manual list'; start(manual.length ? manual : ['virtual']); });
    } else start(manual.length ? manual : ['virtual']);
  }
  // ---------- UI ----------
  function render() {
    $('txname').textContent = $('allcall').checked ? 'ALL-CALL: ' + (Array.from(allSel).join(', ') || '(none checked)') : (cfg.tx || '–');
    $('chs').innerHTML = state.map(function (c) {
      var f = c.floor, cls = 'ch' + (c.name === cfg.tx ? ' tx' : '') + (f && !f.mine ? ' busy' : '') + (f && f.mine ? ' mine' : '');
      var who = c.talkers.length ? '<span class="' + (c.overlap ? 'ov' : 't') + '">🔊 ' + esc(c.talkers.join(' + ')) + (c.overlap ? ' (overlap)' : '') + '</span>'
        : f ? '<span class=t>' + (f.mine ? 'YOU' : esc(f.name)) + (f.prio >= SuperPTT.CUTIN_PRIO ? ' <span class="pill cut">CUT-IN</span>' : '') + '</span>' : c.users.length + ' online';
      return '<div class="' + cls + '" data-ch="' + esc(c.name) + '"><input type=checkbox class=sel data-sel="' + esc(c.name) + '"' + (allSel.has(c.name) ? ' checked' : '') + '>' +
        '<div><div class=nm>' + esc(c.name) + (c.prio ? ' <span class=pill>P' + c.prio + '</span>' : '') + ' ' + lockTag(c) + '</div><div class=who>' + who + '</div></div>' +
        '<button data-mute="' + esc(c.name) + '">' + (c.muted ? '🔇' : '🔈') + '</button><input type=range min=0 max=1.5 step=0.05 value="' + c.vol + '" data-vol="' + esc(c.name) + '"></div>';
    }).join('');
    var bc = state.filter(function (c) { return c.name === cfg.tx && c.floor && !c.floor.mine; })[0], anyBusy = !!bc && !$('allcall').checked;
    $('ptt').className = talking ? 'on' : anyBusy ? 'busy' : online ? '' : 'off';
    $('ptt').textContent = talking ? 'TALKING' : anyBusy ? 'BUSY' + (bc.floor.name ? ' · ' + bc.floor.name : '') : 'PUSH TO TALK';
  }
  function lockTag(c) {
    if (c.enc) { var r = rejects[c.name] || {}, bad = r.auth || r.wrongkey;
      return '<span class=lock title="end-to-end encrypted, AES-256-GCM">🔒 E2E' + (c.enc.hide ? ' · hidden' : '') + '</span>' + (bad ? ' <span class=nokey>key mismatch?</span>' : ''); }
    if (dirEnc[c.name] || (rejects[c.name] && rejects[c.name].nokey)) return '<span class=nokey>🔒 key needed – scan the invite QR</span>';
    return '<span class=open>⚠ not encrypted</span>';
  }
  $('chs').addEventListener('click', function (e) {
    var t = e.target;
    if (t.dataset.sel) { t.checked ? allSel.add(t.dataset.sel) : allSel.delete(t.dataset.sel); save(); render(); return; }
    if (t.dataset.mute) { var C = cl.ch[t.dataset.mute]; C.muted = !C.muted; cl.emit(); return; }
    if (t.dataset.vol) return;
    var row = t.closest('.ch'); if (row && !talking) { cfg.tx = row.dataset.ch; save(); render(); log('TX channel → ' + cfg.tx); }
  });
  $('chs').addEventListener('input', function (e) { if (e.target.dataset.vol) cl.ch[e.target.dataset.vol].vol = +e.target.value; });
  $('allcall').onchange = render;
  $('allsel').onclick = function () { state.forEach(function (c) { allSel.add(c.name); }); save(); render(); };
  $('nonesel').onclick = function () { allSel.clear(); save(); render(); };
  $('add').onkeydown = function (e) { if (e.key === 'Enter' && cl) { if (cl.join(this.value.trim())) log('joined ' + this.value); this.value = ''; } };
  $('gear').onclick = function () { $('setup').classList.toggle('hide'); };
  $('go').onclick = function () { audioInit(); connect(); };
  // keyboard: Space = PTT, 1-9 = switch TX channel
  document.addEventListener('keydown', function (e) {
    if (e.target.tagName === 'INPUT') return;
    if (e.code === 'Space' && !e.repeat) { e.preventDefault(); startTx(); }
    var n = +e.key; if (n >= 1 && n <= 9 && state[n - 1] && !talking) { cfg.tx = state[n - 1].name; save(); render(); }
  });
  document.addEventListener('keyup', function (e) { if (e.code === 'Space') stopTx(); });
  function startTx() {
    if (!cl || talking) return; audioInit(); if (ac.state === 'suspended') ac.resume();
    var targets = $('allcall').checked ? Array.from(allSel).filter(function (c) { return cl.ch[c]; }) : [cfg.tx];
    if (!targets.length) { $('pst').textContent = 'No channel selected'; return; }
    micInit().then(function () {
      cl.claim(targets, {}, function (r) {
        if (!r.ok.length) { $('pst').textContent = 'Busy: ' + r.busy.join(', '); return; }
        talking = true; render(); $('pst').textContent = 'On air: ' + r.ok.join(', ') + (r.busy.length ? ' · busy: ' + r.busy.join(', ') : '');
        if (navigator.vibrate) navigator.vibrate(40);
      });
    }).catch(function (e) { $('pst').textContent = 'Microphone blocked: ' + e.message; });
  }
  function stopTx() { if (!cl) return; talking = false; cl.release(); render(); }
  var b = $('ptt');
  b.addEventListener('pointerdown', function (e) { e.preventDefault(); b.setPointerCapture(e.pointerId); startTx(); });
  ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(function (ev) { b.addEventListener(ev, stopTx); });
  // Android wrapper hook: window.SuperPTTHardware.down()/up() from volume/PTT key
  window.SuperPTTHardware = { down: startTx, up: stopTx };
  // boot
  $('name').value = cfg.name || ''; $('admin').value = cfg.admin || ''; $('dtok').value = cfg.dtok || ''; $('manual').value = cfg.manual || ''; $('disc').checked = !!cfg.disc;
  $('burl').value = cfg.burl || ''; $('buser').value = cfg.buser || ''; $('bpass').value = cfg.bpass || '';
  $('keyinfo').textContent = Object.keys(cfg.keys).length ? '🔒 keys on this phone: ' + Object.keys(cfg.keys).join(', ') : 'No channel keys yet: open the invite link / scan the QR from the control room.';
  if (invited.length) { log('🔒 key added for ' + invited.join(', ') + ' (from invite link)'); save(); }
  if (cfg.name && (cfg.admin || cfg.manual)) { connect(); document.addEventListener('pointerdown', audioInit, { once: true }); }
  else $('setup').classList.remove('hide');
  window.addEventListener('beforeunload', function () { if (cl) cl.close(); });
})();
