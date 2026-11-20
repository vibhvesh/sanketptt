// Offline crypto unit test + JS<->Python interop (no broker needed). usage: node test/crypto.js
const { E2E } = require('../superptt.js'), { execFileSync } = require('child_process'), path = require('path');
const res = []; const check = (n, ok, i) => { res.push(ok); console.log((ok ? 'PASS ' : 'FAIL ') + n + (i ? '  ' + i : '')); };
(async () => {
  const sec = E2E.newSecret(), K = await E2E.deriveKeys('ops', sec, 3, true), K2 = await E2E.deriveKeys('ops', E2E.newSecret(), 3, true);
  const pt = new TextEncoder().encode('{"id":"abc","t":"claim"}');
  const pk = await E2E.seal(K, 'ops', 'floor', 'abc', 7, Date.now(), pt);
  const ok = await E2E.open(K, 'ops', 'floor', pk, new E2E.Replay()).catch(e => e);
  check('c1 round-trip', ok.data && new TextDecoder().decode(ok.data) === new TextDecoder().decode(pt));
  check('c2 wrong key rejected', (await E2E.open(K2, 'ops', 'floor', pk).catch(e => e)) === 'auth');
  const t = pk.slice(); t[t.length - 20] ^= 1; check('c3 tampered ciphertext rejected', (await E2E.open(K, 'ops', 'floor', t).catch(e => e)) === 'auth');
  const h = pk.slice(); h[8] ^= 1; check('c4 tampered header (seq) rejected', (await E2E.open(K, 'ops', 'floor', h).catch(e => e)) === 'auth');
  check('c5 cross-topic (floor packet as audio) rejected', (await E2E.open(K, 'ops', 'audio', pk).catch(e => e)) === 'auth');
  const R = new E2E.Replay(); await E2E.open(K, 'ops', 'floor', pk, R);
  check('c6 replay rejected', (await E2E.open(K, 'ops', 'floor', pk, R).catch(e => e)) === 'replay');
  const old = await E2E.seal(K, 'ops', 'floor', 'abc', 8, Date.now() - 60000, pt);
  check('c7 stale timestamp rejected', (await E2E.open(K, 'ops', 'floor', old, new E2E.Replay()).catch(e => e)) === 'stale');
  check('c8 hidden topic hides channel name', K.topic !== 'ops' && /^h[0-9a-f]{24}$/.test(K.topic), K.topic);
  const inv = E2E.parseInvite('#k=ops.3.' + sec + '.h,news.1.' + sec);
  check('c9 invite parse', inv.keys.length === 2 && inv.keys[0].hide && inv.keys[0].kid === 3 && !inv.keys[1].hide);
  // interop with control-room/superptt/e2e.py
  const py = `import sys,json;sys.path.insert(0,${JSON.stringify([path.resolve(__dirname, '../../control-room'), path.resolve(__dirname, '../pi')].find(d => require('fs').existsSync(d + '/superptt/e2e.py')))})
from superptt import e2e
K=e2e.ChanKey('ops',sys.argv[1],3,True);sid,pt=e2e.open_(K,'floor',bytes.fromhex(sys.argv[2]))
out=e2e.seal(K,'audio','pyid',1,b'\\x04pyid'+b'\\x01\\x02')
print(json.dumps({'topic':K.topic,'sid':sid,'pt':pt.decode(),'out':out.hex()}))`;
  const o = JSON.parse(execFileSync('python3', ['-c', py, sec, Buffer.from(pk).toString('hex')]).toString());
  check('c10 JS -> Python decrypt', o.sid === 'abc' && o.pt === new TextDecoder().decode(pt) && o.topic === K.topic);
  const back = await E2E.open(K, 'ops', 'audio', new Uint8Array(Buffer.from(o.out, 'hex'))).catch(e => e);
  check('c11 Python -> JS decrypt', back.id === 'pyid' && back.data.length === 7);
  console.log(res.filter(Boolean).length + '/' + res.length + ' passed'); process.exit(res.every(Boolean) ? 0 : 1);
})();
