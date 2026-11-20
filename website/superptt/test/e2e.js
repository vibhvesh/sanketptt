// Live-broker E2E: 3 SuperPTT clients + 1 legacy Sanket PTT client + control room (Python), on an isolated test prefix.
// usage: node test/e2e.js <prefix> <controlRoomUrl> <cookieFile>
const mqtt = require(process.env.MQTT_PATH || 'mqtt'), fs = require('fs'), http = require('http');
const { Client, Mixer } = require('../superptt.js');
const PREFIX = process.argv[2], CR = process.argv[3], COOKIE = fs.readFileSync(process.argv[4], 'utf8').trim();
const BROKER = ['wss://public:public@public.cloud.shiftr.io'];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const results = []; const check = (name, ok, info) => { results.push({ name, ok }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (info ? '  ' + info : '')); };
function mk(name, o) {
  const rx = {}, pre = [], rej = [], disc = [], st = { rx, pre, rej, disc };
  st.c = new Client(mqtt, Object.assign({ name, prefix: PREFIX, brokers: BROKER, on: (t, v) => {
    if (t === 'reject') rej.push(v);
    if (t === 'discover') disc.push(v);
    if (t === 'audio') { const k = v.ch + '|' + v.name; (rx[k] = rx[k] || []).push(...v.pcm); st.mix && st.mix.feed(v); }
    if (t === 'preempted') pre.push(v);
  } }, o || {}));
  return st;
}
async function talk(st, chs, val, ms, opts) {
  const r = await new Promise(res => st.c.claim(chs, opts || {}, res));
  if (r.ok.length) for (let t = 0; t < ms; t += 50) { st.c.sendAudio(new Int16Array(600).fill(val)); await sleep(50); }
  st.c.release(); return r;
}
const pure = (arr, v) => arr && arr.length > 0 && arr.every(x => x === v);
function crPost(path, body, raw) {
  return new Promise((res, rej) => {
    const u = new URL(CR + path), data = raw || Buffer.from(JSON.stringify(body || {}));
    const q = http.request({ hostname: u.hostname, port: u.port, path: u.pathname, method: 'POST', headers: { Cookie: COOKIE, 'X-Requested-With': 'superptt',
      'Content-Type': raw ? 'application/octet-stream' : 'application/json', 'Content-Length': data.length } }, r => { let s = ''; r.on('data', d => s += d); r.on('end', () => res(JSON.parse(s))); });
    q.on('error', rej); q.end(data);
  });
}
function crGet(path) {
  return new Promise((res, rej) => { const u = new URL(CR + path);
    http.get({ hostname: u.hostname, port: u.port, path: u.pathname + u.search, headers: { Cookie: COOKIE } }, r => { let s = ''; r.on('data', d => s += d); r.on('end', () => res(JSON.parse(s))); }).on('error', rej); });
}
function legacy() {
  const html = fs.readFileSync('/workspace/sanketptt/index.html', 'utf8');
  let core = html.match(/<script id=core>([\s\S]*?)<\/script>/)[1].replace("var PTT_PREFIX='ptt-radio-66ab9178/'", "var PTT_PREFIX='" + PREFIX + "'");
  const m = { exports: {} }; new Function('module', 'require', 'Buffer', core)(m, require, Buffer);
  const L = { rx: {}, floorName: null };
  L.r = new m.exports.Radio(mqtt, { ch: 't1', brokers: BROKER, on: (t, v) => {
    if (t === 'audio') { const k = (L.r.floor && L.r.floor.name) || '?'; (L.rx[k] = L.rx[k] || []).push(...v); }
    if (t === 'state') L.floorName = v.floor ? v.floor.name : null;
  } });
  L.r.join('LegacyUser'); return L;
}
(async () => {
  const A = mk('Alpha'), B = mk('Bravo'), C = mk('Charlie'), L = legacy();
  ['t1', 't2', 't3'].forEach(c => { A.c.join(c); C.c.join(c); }); B.c.join('t1'); B.c.join('t2');
  C.mix = new Mixer({ prebuf: 0 });
  await sleep(6000);
  check('all connected', [A, B, C].every(x => x.c.c.connected) && L.r.c.connected);
  // 1 multi-listen
  await talk(B, 't1', 1000, 800); await sleep(800); await talk(B, 't2', 2000, 800); await sleep(1200);
  check('1 multi-listen: Alpha hears Bravo on t1 and t2', pure(A.rx['t1|Bravo'], 1000) && pure(A.rx['t2|Bravo'], 2000),
    `t1=${(A.rx['t1|Bravo'] || []).length} t2=${(A.rx['t2|Bravo'] || []).length} samples`);
  check('1b legacy client on t1 hears SuperPTT Bravo', pure(L.rx['Bravo'], 1000), `${(L.rx['Bravo'] || []).length} samples`);
  // 2 switch TX channel
  await talk(A, 't2', 3000, 800); await sleep(1200);
  check('2 switch: Alpha TX on t2 heard by Bravo', pure(B.rx['t2|Alpha'], 3000) && !B.rx['t1|Alpha']);
  // 3 all-call
  const r3 = await talk(A, ['t1', 't2', 't3'], 4000, 800); await sleep(1500);
  check('3 all-call t1+t2+t3', r3.ok.length === 3 && (B.rx['t1|Alpha'] || []).includes(4000) && (B.rx['t2|Alpha'] || []).filter(x => x === 4000).length > 0 && pure(C.rx['t3|Alpha'], 4000),
    'claimed ' + r3.ok.join(','));
  // 4 cross-channel overlap: Alpha t1 + Bravo t2 at the same time
  ['t1|Alpha', 't2|Bravo'].forEach(k => delete C.rx[k]);
  await Promise.all([talk(A, 't1', 5000, 1500), talk(B, 't2', 6000, 1500)]); await sleep(1500);
  check('4 overlap: separate un-garbled streams per sender', pure(C.rx['t1|Alpha'], 5000) && pure(C.rx['t2|Bravo'], 6000),
    `alpha=${(C.rx['t1|Alpha'] || []).length} bravo=${(C.rx['t2|Bravo'] || []).length}`);
  // mixer: both streams feed concurrently -> summed output, priority ducking
  const M = new Mixer({ prebuf: 0, chanInfo: ch => ({ vol: 1, prio: ch === 't1' ? 5 : 0 }) });
  M.feed({ ch: 't1', id: 'a', pcm: new Int16Array(3000).fill(8000) }); M.feed({ ch: 't2', id: 'b', pcm: new Int16Array(3000).fill(8000) });
  const o = M.render(3000); const lvl = o[2900];
  check('4b mixer ducks lower-priority channel', lvl > 0.24 && lvl < 0.36, 'sum level ' + lvl.toFixed(3) + ' (undu cked would be ~0.47)');
  // 5 same-channel collision
  const [ra, rb] = await Promise.all([talk(A, 't1', 1, 300), talk(B, 't1', 2, 300)]); await sleep(1000);
  check('5 same-channel race: exactly one wins', (ra.ok.length + rb.ok.length) === 1, `alpha=${ra.ok} bravo=${rb.ok}`);
  // 6 control-room cut-in while Bravo talks on t1
  delete A.rx['t1|Control Room']; delete L.rx['Control Room'];
  const bTalk = talk(B, 't1', 7000, 3000); await sleep(1000);
  const s6 = await crPost('/api/tx/start', { channels: ['t1'], cutin: true });
  for (let i = 0; i < 20; i++) { await crPost('/api/tx/audio', null, Buffer.from(new Int16Array(600).fill(8000).buffer)); await sleep(50); }
  await crPost('/api/tx/stop'); await bTalk; await sleep(1500);
  check('6 cut-in: Bravo preempted', B.pre.some(p => p.ch === 't1' && p.by === 'Control Room'), JSON.stringify(s6));
  check('6b Alpha hears control room on t1', pure(A.rx['t1|Control Room'], 8000), `${(A.rx['t1|Control Room'] || []).length} samples`);
  check('6c legacy client switched floor to control room', (L.rx['Control Room'] || []).includes(8000));
  // 7 control-room talk-back to ALL (non cut-in)
  delete B.rx['t2|Control Room']; delete C.rx['t3|Control Room'];
  const s7 = await crPost('/api/tx/start', { channels: 'all' });
  for (let i = 0; i < 16; i++) { await crPost('/api/tx/audio', null, Buffer.from(new Int16Array(600).fill(9000).buffer)); await sleep(50); }
  await crPost('/api/tx/stop'); await sleep(1500);
  check('7 control room all-channel talk-back', pure(B.rx['t2|Control Room'], 9000) && pure(C.rx['t3|Control Room'], 9000), 'ok=' + s7.ok.join(','));
  // ---------- 8. E2E encryption ----------
  const { E2E } = require('../superptt.js');
  const D = mk('Delta', { discover: true });
  const sniff = mqtt.connect(BROKER[0], { clientId: 'sniff_' + Date.now() % 1e6 }), wire = [];
  sniff.on('message', (t, p) => wire.push({ t, p: Buffer.from(p) })); sniff.on('connect', () => sniff.subscribe(PREFIX + '#'));
  await crPost('/api/keys', { channel: 'e1', action: 'remove' }); await crPost('/api/keys', { channel: 'e2', action: 'remove' });
  const k1 = await crPost('/api/keys', { channel: 'e1', action: 'add', hide: true });
  await crPost('/api/keys', { channel: 'e2', action: 'add', hide: false });
  const iv = await crPost('/api/keys/invite', { channels: ['e1', 'e2'] });
  const frag = iv.link.split('#')[1], inv = E2E.parseInvite('#' + frag);
  check('8a admin adds keys, invite carries keys only in the URL fragment', inv.keys.length === 2 && !iv.link.split('#')[0].includes(inv.keys[0].secret) && !!iv.qr_svg,
    'keys=' + k1.map(k => k.channel + '#' + k.kid).join(','));
  const dir = await crGet('/api/directory');
  check('8a2 directory lists e1/e2 as encrypted but never serves a key', JSON.stringify(dir).indexOf(inv.keys[0].secret) < 0 && dir.channels.some(c => c.id === 'e1' && c.encrypted));
  for (const x of [A, B]) for (const k of inv.keys) { await x.c.setKey(k.ch, k.secret, k.kid, k.hide); x.c.join(k.ch); }
  const wrong = inv.keys.find(k => k.ch === 'e2'); await C.c.setKey('e2', E2E.newSecret(), wrong.kid, false); C.c.join('e2');
  await sleep(3000);
  const cut = wire.length;
  await talk(A, 'e1', 1111, 1000); await sleep(1500);
  check('8b encrypted channel round-trips (Alpha -> Bravo on hidden e1)', pure(B.rx['e1|Alpha'], 1111), `${(B.rx['e1|Alpha'] || []).length} samples`);
  const w8 = wire.slice(cut), hid = A.c.keys.e1.topic, onHid = w8.filter(m => m.t.indexOf('/' + hid + '/') > 0);
  const pcmPat = Buffer.from(new Int16Array(16).fill(1111).buffer);
  check('8c on the wire: hidden topic, all payloads sealed, no plaintext audio', onHid.length > 5 && !w8.some(m => m.t.indexOf('/e1/') >= 0) &&
    onHid.every(m => !m.p.length || m.p[0] === 0xE5) && !w8.some(m => m.p.includes(pcmPat)), `${onHid.length} packets on ${hid}`);
  const st8 = await crGet('/api/status');
  check('8d Pi decrypts (sees Alpha on e1) and marks e1 locked', st8.e2e.ok > 0 && st8.channels.some(c => c.channel === 'e1' && c.encrypted && c.encrypted.hide), JSON.stringify(st8.e2e));
  delete A.rx['e1|Control Room'];
  await crPost('/api/tx/start', { channels: ['e1'] });
  for (let i = 0; i < 16; i++) { await crPost('/api/tx/audio', null, Buffer.from(new Int16Array(600).fill(4321).buffer)); await sleep(50); }
  await crPost('/api/tx/stop'); await sleep(1500);
  check('8e control-room talk-back encrypted by the Pi, decrypted by phone', pure(A.rx['e1|Control Room'], 4321), `${(A.rx['e1|Control Room'] || []).length} samples`);
  // wrong key
  const cut2 = wire.length; C.rej.length = 0;
  await talk(A, 'e2', 2222, 1000); await sleep(1500);
  check('8f wrong key rejected (Charlie hears nothing on e2, Bravo does)', !C.rx['e2|Alpha'] && C.rej.some(r => r.ch === 'e2' && r.reason === 'auth') && pure(B.rx['e2|Alpha'], 2222),
    'charlie rejects=' + C.rej.filter(r => r.ch === 'e2').length);
  // tamper + replay (captured from the wire, re-published within the 30 s window)
  const cap = wire.slice(cut2).find(m => m.t.endsWith('/e2/audio'));
  const before = (B.rx['e2|Alpha'] || []).length; B.rej.length = 0; const crBefore = (await crGet('/api/status')).e2e;
  const tam = Buffer.from(cap.p); tam[tam.length - 30] ^= 0x40; sniff.publish(cap.t, tam);
  const tamH = Buffer.from(cap.p); tamH[4 + tamH[3] + 3] ^= 1; sniff.publish(cap.t, tamH);    // seq changed in header (AAD)
  await sleep(1200);
  check('8g tampered packets rejected (ciphertext and header)', B.rej.filter(r => r.reason === 'auth').length >= 2 && (B.rx['e2|Alpha'] || []).length === before);
  sniff.publish(cap.t, cap.p); await sleep(1200);
  check('8h replayed packet rejected', B.rej.some(r => r.reason === 'replay') && (B.rx['e2|Alpha'] || []).length === before);
  const legacyFrame = Buffer.concat([Buffer.from([4]), Buffer.from('evil'), Buffer.from(new Int16Array(600).fill(5).buffer)]);
  sniff.publish(cap.t, legacyFrame); await sleep(1000);
  check('8i plaintext injection on encrypted channel rejected', B.rej.some(r => r.reason === 'plain') && !B.rx['e2|evil']);
  const cr = (await crGet('/api/status')).e2e;
  check('8j Pi also rejects tamper + replay', cr.auth >= crBefore.auth + 2 && cr.replay > crBefore.replay && cr.plain > crBefore.plain, JSON.stringify(cr));
  const snapA = A.c.snapshot();
  check('8k legacy channel t1 marked not encrypted, e1 locked', snapA.find(c => c.name === 't1').enc === null && !!snapA.find(c => c.name === 'e1').enc);
  check('8l auto-discovery still finds legacy channels, never hidden encrypted ones', D.disc.includes('t1') && !D.disc.some(c => c === hid || c === 'e1'), 'discovered ' + D.disc.join(','));
  const aud = await crGet('/api/audit?limit=50'), audS = JSON.stringify(aud);
  check('8m security log has key add/invite, no secrets', ['key_add', 'key_invite'].every(a => aud.some(x => x.action === a)) && !inv.keys.some(k => audS.includes(k.secret)),
    aud.slice(0, 4).map(x => x.action).join(','));
  await sleep(2000);
  const tl = await crGet('/api/timeline?since=' + (Date.now() / 1000 - 600) + '&channels=e1');
  check('8n Pi records the encrypted transmission (decrypted at rest on the Pi)', tl.some(x => x.speaker === 'Alpha'));
  sniff.end(true); D.c.close();
  [A, B, C].forEach(x => x.c.close()); L.r.leave(); await sleep(800);
  fs.writeFileSync('/tmp/e2e_results.json', JSON.stringify(results));
  console.log(results.filter(r => r.ok).length + '/' + results.length + ' passed'); process.exit(0);
})();
