"""SuperPTT end-to-end encryption, wire-compatible with app/superptt.js (E2E).
packet = [0xE5][ver=1][kid][n][id..n][seq u32 BE][ts u64 BE ms][nonce 12][ciphertext+tag 16]
AAD    = packet[:16+n] + b"superptt|<channel>|<kind>"     kind = presence|floor|audio|sstv
keys   = HKDF-SHA256(secret 32 B, salt=b"superptt-e2e-v1", info=b"aes|<ch>" / b"topic|<ch>")
Uses the `cryptography` package (OpenSSL). Not a FIPS-validated module (see SECURITY.md)."""
import base64, hashlib, hmac, json, os, secrets, struct, threading, time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
MAGIC, VER, MAX_SKEW_MS, WIN = 0xE5, 1, 30000, 64
SALT = b"superptt-e2e-v1"

def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def unb64u(s): s = str(s); return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
def new_secret(): return b64u(secrets.token_bytes(32))
def _hkdf(secret, info): return HKDF(hashes.SHA256(), 32, SALT, info).derive(secret)

class ChanKey:
    def __init__(self, ch, secret, kid=1, hide=False):
        raw = unb64u(secret) if isinstance(secret, str) else secret
        if len(raw) != 32: raise ValueError("secret must be 32 bytes")
        self.ch, self.kid, self.hide = ch, int(kid) & 255, bool(hide)
        self.aes = AESGCM(_hkdf(raw, b"aes|" + ch.encode()))
        tk = _hkdf(raw, b"topic|" + ch.encode())
        self.topic = "h" + hmac.new(tk, ch.encode(), hashlib.sha256).hexdigest()[:24] if hide else ch

def is_sealed(b): return len(b) > 4 and b[0] == MAGIC and b[1] == VER

def seal(K, kind, sid, seq, plain, ts=None):
    ts = int(time.time() * 1000) if ts is None else ts
    idb = sid.encode("latin1")
    hdr = bytes([MAGIC, VER, K.kid, len(idb)]) + idb + struct.pack(">IQ", seq & 0xFFFFFFFF, ts)
    iv = os.urandom(12)
    return hdr + iv + K.aes.encrypt(iv, plain, hdr + f"superptt|{K.ch}|{kind}".encode())

class Rejected(Exception): pass

class Replay:
    def __init__(self): self.w, self.lock = {}, threading.Lock()
    def check(self, k, seq, ts):
        now = time.time() * 1000
        if abs(now - ts) > MAX_SKEW_MS: raise Rejected("stale")
        with self.lock:
            W = self.w.get(k)
            if not W: self.w[k] = [seq, [seq], now]; return
            W[2] = now
            if seq > W[0]: W[0] = seq
            elif W[0] - seq >= WIN or seq in W[1]: raise Rejected("replay")
            W[1].append(seq); del W[1][:-WIN]
            if len(self.w) > 5000:
                for kk in [kk for kk, v in self.w.items() if now - v[2] > 120000]: self.w.pop(kk, None)

def open_(K, kind, b, replay=None):
    """returns (sender_id, plaintext) or raises Rejected(reason)"""
    if not is_sealed(b) or len(b) < 4 + b[3] + 40: raise Rejected("malformed")
    n = b[3]; sid = b[4:4 + n].decode("latin1"); seq, ts = struct.unpack(">IQ", b[4 + n:16 + n])
    if b[2] != K.kid: raise Rejected("wrongkey")
    hdr, iv, ct = b[:16 + n], b[16 + n:28 + n], b[28 + n:]
    try: pt = K.aes.decrypt(iv, ct, hdr + f"superptt|{K.ch}|{kind}".encode())
    except Exception: raise Rejected("auth")
    if replay: replay.check(f"{K.ch}|{kind}|{sid}", seq, ts)
    return sid, pt

class KeyStore:
    """Channel secrets, kept in <data_dir>/keys.json (mode 600). Never published to the broker or the directory."""
    def __init__(self, path):
        self.path, self.lock = path, threading.Lock(); self.d = {}
        if os.path.exists(path):
            with open(path) as f: self.d = json.load(f)
        self.cache = {}
    def _save(self):
        tmp = self.path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f: json.dump(self.d, f, indent=1)
        os.replace(tmp, self.path); os.chmod(self.path, 0o600)
    def get(self, ch):
        e = self.d.get(ch)
        if not e: return None
        c = self.cache.get(ch)
        if not c or c[0] != (e["kid"], e["secret"], e["hide"]):
            c = self.cache[ch] = ((e["kid"], e["secret"], e["hide"]), ChanKey(ch, e["secret"], e["kid"], e["hide"]))
        return c[1]
    def set(self, ch, hide=False, secret=None):
        with self.lock:
            old = self.d.get(ch); kid = ((old["kid"] % 255) + 1) if old else 1
            self.d[ch] = {"kid": kid, "secret": secret or new_secret(), "hide": bool(hide), "created": time.time()}
            self._save(); return kid
    def remove(self, ch):
        with self.lock:
            if self.d.pop(ch, None) is not None: self._save(); return True
        return False
    def channels(self): return sorted(self.d)
    def public(self):
        return [{"channel": ch, "kid": e["kid"], "hide": e["hide"], "created": e["created"],
                 "fingerprint": hashlib.sha256(unb64u(e["secret"])).hexdigest()[:8]} for ch, e in sorted(self.d.items())]
    def secret(self, ch): return self.d[ch]["secret"]
