"""Lightweight SSTV detector + decoder (numpy only).

Quality features, all cheap enough for a Pi:
  * FFT band-pass (1000-2500 Hz) before FM demodulation -> less noise
  * analytic-signal FM demod, pixel values averaged over each pixel's window (not point samples)
  * VIS header decode, with fallback to line-period detection when there is no VIS
  * per-line sync pulse detection + robust linear fit of sync times -> sync lock and slant (clock drift) correction
Modes: Martin M1/M2, Scottie S1/S2, Robot 36.
"""
import struct, zlib
import numpy as np

# offsets are ms from the start of the line's sync pulse
MODES = {
    44: dict(name="Martin M1", period=446.446, sync=4.862, lines=256, width=320, ch=[(5.434, 146.432, "G"), (152.438, 146.432, "B"), (299.442, 146.432, "R")]),
    40: dict(name="Martin M2", period=226.798, sync=4.862, lines=256, width=320, ch=[(5.434, 73.216, "G"), (79.222, 73.216, "B"), (153.010, 73.216, "R")]),
    60: dict(name="Scottie S1", period=428.220, sync=9.0, lines=256, width=320, ch=[(-277.98, 138.24, "G"), (-138.24, 138.24, "B"), (10.5, 138.24, "R")]),
    56: dict(name="Scottie S2", period=277.692, sync=9.0, lines=256, width=320, ch=[(-177.628, 88.064, "G"), (-88.064, 88.064, "B"), (10.5, 88.064, "R")]),
    8:  dict(name="Robot 36", period=150.0, sync=9.0, lines=240, width=320, ch=[(12.0, 88.0, "Y"), (106.0, 44.0, "C")]),
}
NAME2VIS = {m["name"].lower().replace(" ", ""): v for v, m in MODES.items()}


def _bandpass(x, rate, lo=1000, hi=2500):
    n = 1 << int(np.ceil(np.log2(len(x) + 1)))
    X = np.fft.rfft(x, n); f = np.fft.rfftfreq(n, 1 / rate)
    X[(f < lo) | (f > hi)] = 0
    return X, n


def demod(x, rate):
    """Instantaneous frequency (Hz) per sample via the analytic signal of the band-passed input."""
    x = np.asarray(x, np.float32)
    X, n = _bandpass(x, rate)
    full = np.zeros(n, complex); full[:len(X)] = X; full[1:len(X) - 1] *= 2   # analytic spectrum
    a = np.fft.ifft(full)[:len(x)]
    ph = np.unwrap(np.angle(a))
    f = np.empty(len(x), np.float32); f[1:] = np.diff(ph) * rate / (2 * np.pi); f[0] = f[1] if len(f) > 1 else 0
    return np.clip(f, 800, 2600)


def _smooth(f, n):
    if n <= 1:
        return f
    c = np.cumsum(np.concatenate([[0], f]))
    out = (c[n:] - c[:-n]) / n
    return np.concatenate([np.full(n // 2, out[0]), out, np.full(len(f) - len(out) - n // 2, out[-1])])


def find_vis(f, rate):
    """Returns (vis_code, sample index right after the VIS stop bit) or (None, 0)."""
    ms = rate / 1000.0
    s = _smooth(f, int(8 * ms))
    step = int(2 * ms)
    near = lambda a, b, tol=70: abs(a - b) < tol
    for t in range(int(200 * ms), len(s) - int(300 * ms), step):
        if not near(s[t + int(15 * ms)], 1200, 60):         # start bit centre
            continue
        if not (near(s[t - int(60 * ms)], 1900) and near(s[t - int(150 * ms)], 1900)):
            continue
        # refine start-bit edge to 1 ms
        best = None
        for d in range(-int(6 * ms), int(6 * ms) + 1, max(1, int(ms))):
            u = t + d
            bits = [s[u + int((30 * (i + 1) + 15) * ms)] for i in range(8)]
            if all(1050 < b < 1350 for b in bits):
                v = sum((1 if b < 1200 else 0) << i for i, b in enumerate(bits[:7]))
                par = 1 if bits[7] < 1200 else 0
                if bin(v).count("1") % 2 == par and v in MODES:
                    best = (v, u + int(300 * ms)); break
        if best:
            return best
    return None, 0


def _sync_starts(f, rate, sync_ms, start):
    ms = rate / 1000.0
    m = (_smooth(f, max(1, int(1.5 * ms))) < 1350).astype(np.int8)
    m[:start] = 0
    edges = np.flatnonzero(np.diff(m) == 1) + 1
    need = int(sync_ms * 0.6 * ms); out = []
    c = np.cumsum(np.concatenate([[0], m]))
    for e in edges:
        if e + need < len(m) and c[e + need] - c[e] >= need * 0.85 and (not out or e - out[-1] > need * 3):
            out.append(e)
    return np.asarray(out, float)


def _fit(starts, period):
    """Robust line fit t = a + p*i over detected syncs -> (a, p). Corrects timing offset and slant."""
    if len(starts) < 3:
        return (starts[0] if len(starts) else 0.0), period
    t0 = starts[0]
    d = np.diff(starts); one = d[np.abs(d / period - 1) < 0.03]
    p = float(np.median(one)) if len(one) >= 2 else period       # local line period first, then index lines
    k0 = next((i for i in range(len(d)) if abs(d[i] / p - 1) < 0.03), 0)   # skip a leading non-line sync (Scottie)
    t0 = starts[k0]; starts = starts[k0:]
    idx = np.round((starts - t0) / p)
    a = t0
    for _ in range(4):
        keep = np.abs(starts - (a + p * idx)) < max(0.004 * period * 50, period * 0.02)
        if keep.sum() < 3:
            break
        A = np.vstack([np.ones(keep.sum()), idx[keep]]).T
        a, p = np.linalg.lstsq(A, starts[keep], rcond=None)[0]
        p = float(np.clip(p, period * 0.98, period * 1.02))
        idx = np.round((starts - a) / p)
    return float(a), float(p)


def guess_mode(f, rate, start=0):
    best, score = None, 0
    for v, m in MODES.items():
        st = _sync_starts(f, rate, m["sync"], start)
        if len(st) < 5:
            continue
        d = np.diff(st) / (rate / 1000.0)
        hits = np.sum(np.abs(d / m["period"] - 1) < 0.03)
        sc = hits / len(d)
        if sc > score:
            best, score = v, sc
    return best if score > 0.6 else None


def decode(i16, rate, mode_hint=None):
    """Decode SSTV audio. Returns dict(mode, vis, width, height, rgb ndarray, slant_ppm, syncs) or None."""
    x = np.asarray(i16, np.float32) / 32768.0
    if len(x) < rate:
        return None
    f = demod(x, rate)
    vis, start = find_vis(f, rate)
    if vis is None and mode_hint:
        vis = NAME2VIS.get(str(mode_hint).lower().replace(" ", "").replace("-", ""))
    if vis is None:
        vis = guess_mode(f, rate)
    if vis is None:
        return None
    m = MODES[vis]; ms = rate / 1000.0
    period = m["period"] * ms
    starts = _sync_starts(f, rate, m["sync"], start)
    if len(starts) == 0:
        return None
    a, p = _fit(starts, period)
    k = p / period                                 # time scale (slant correction)
    while a - p > start - m["sync"] * ms and min(o for o, _, _ in m["ch"]) * ms * k + a - p >= 0:
        a -= p                                     # recover early lines whose syncs were missed
    lines = int(min(m["lines"], (len(f) - a) // p + 1))
    W = m["width"]; c = np.cumsum(np.concatenate([[0.0], f.astype(np.float64)]))
    val = lambda fr: np.clip((fr - 1500.0) / 800.0 * 255.0, 0, 255)
    planes = {}
    for o, d, col in m["ch"]:
        j = np.arange(W)
        t0 = a + (np.arange(lines)[:, None]) * p + k * ms * (o + d * j[None, :] / W)
        t1 = t0 + k * ms * d / W
        t0 = np.clip(t0, 0, len(f) - 1); t1 = np.clip(np.maximum(t1, t0 + 1), 1, len(f))
        planes[col] = val((np.interp(t1, np.arange(len(c)), c) - np.interp(t0, np.arange(len(c)), c)) / (t1 - t0))
    if "Y" in planes:   # Robot 36: chroma alternates R-Y (even) / B-Y (odd) lines
        Y, C = planes["Y"], planes["C"]
        V = np.repeat(C[0::2], 2, axis=0)[:lines]; U = np.repeat(C[1::2], 2, axis=0)[:lines]
        if U.shape[0] < lines:
            U = np.vstack([U, U[-1:]])
        R = Y + 1.402 * (V - 128); G = Y - 0.344 * (U - 128) - 0.714 * (V - 128); B = Y + 1.772 * (U - 128)
    else:
        R, G, B = planes["R"], planes["G"], planes["B"]
    rgb = np.clip(np.dstack([R, G, B]), 0, 255).astype(np.uint8)
    return dict(mode=m["name"], vis=vis, width=W, height=lines, rgb=rgb, syncs=int(len(starts)),
                slant_ppm=round((k - 1) * 1e6))


def looks_like_sstv(i16, rate):
    """Cheap test used before ASR: a steady 1900 Hz leader tone (>= 0.45 s within the first 2 s)."""
    x = np.asarray(i16[: rate * 2], np.float32) / 32768
    if len(x) < int(rate * 0.6):
        return False
    hits, run, k, w = 0, 0, 2 * np.pi * 1900 / rate, int(rate * 0.05)
    ref = np.exp(-1j * k * np.arange(w))
    for s in range(0, len(x) - w + 1, w):
        b = x[s:s + w]; e = np.sqrt(np.mean(b ** 2)) + 1e-9
        if e > 1e-3 and abs(np.dot(b, ref)) / w / e > 0.5:
            run += 1; hits = max(hits, run)
        elif hits < 9:
            run = 0
    return hits >= 9


def png(rgb):
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")


def encode(rgb, vis=44, rate=12000, clock=1.0):
    """Test signal generator (Martin/Scottie/Robot). clock != 1 simulates a sender with a drifting clock (slant)."""
    m = MODES[vis]; segs = []
    tone = lambda fr, ms_: segs.append((fr, ms_))
    tone(1900, 300); tone(1200, 10); tone(1900, 300); tone(1200, 30)
    bits = [(vis >> i) & 1 for i in range(7)]; bits.append(sum(bits) % 2)
    for b in bits:
        tone(1100 if b else 1300, 30)
    tone(1200, 30)
    H, W = rgb.shape[0], m["width"]
    fr = lambda v: 1500 + 800 * float(v) / 255.0
    for y in range(min(H, m["lines"])):
        row = rgb[y].astype(float)
        if vis in (44, 40):
            px = m["ch"][0][1] / W
            tone(1200, m["sync"]); tone(1500, 0.572)
            for ci in (1, 2, 0):
                for v in row[:, ci]: tone(fr(v), px)
                tone(1500, 0.572)
        elif vis in (60, 56):
            px = m["ch"][0][1] / W
            if y == 0: tone(1200, 9.0)
            tone(1500, 1.5)
            for v in row[:, 1]: tone(fr(v), px)
            tone(1500, 1.5)
            for v in row[:, 2]: tone(fr(v), px)
            tone(1200, 9.0); tone(1500, 1.5)
            for v in row[:, 0]: tone(fr(v), px)
        else:
            Y = 16 + (65.7 * row[:, 0] + 129.1 * row[:, 1] + 25.1 * row[:, 2]) / 256
            Ry = 128 + (112.4 * row[:, 0] - 94.1 * row[:, 1] - 18.3 * row[:, 2]) / 256
            By = 128 + (-37.9 * row[:, 0] - 74.5 * row[:, 1] + 112.4 * row[:, 2]) / 256
            tone(1200, 9.0); tone(1500, 3.0)
            for v in Y: tone(fr(v), 88.0 / W)
            tone(1500 if y % 2 == 0 else 2300, 4.5); tone(1900, 1.5)
            C = Ry if y % 2 == 0 else By
            for v in C.reshape(-1, 2).mean(1): tone(fr(v), 44.0 / (W / 2))
    durs = np.array([d for _, d in segs]) * clock * rate / 1000.0
    edges = np.concatenate([[0], np.cumsum(durs)]); n = int(edges[-1])
    idx = np.searchsorted(edges, np.arange(n), side="right") - 1
    freq = np.array([f for f, _ in segs])[np.clip(idx, 0, len(segs) - 1)]
    phase = np.cumsum(2 * np.pi * freq / rate)
    return (np.sin(phase) * 0.6 * 32767).astype(np.int16)
