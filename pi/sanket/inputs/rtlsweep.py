"""RTL-SDR spectrum sweep / activity monitor (rtl_power). No demodulation, no audio, no content is
recorded: it only measures power per frequency bin, learns a noise floor per bin and logs signals that
rise above floor + threshold and are not on the allowlist (time, frequency, peak dB, duration), for
reporting to the WPC monitoring service. Uses the dongle exclusively, so it cannot share a device with an
'rtl-sdr' (rtl_fm) input on the same dongle index."""
import csv, io, subprocess, threading, time
import numpy as np
from .registry import InputBase, register
from ..util import log

DONGLE_TYPES = ("rtl-sdr", "rtl-sweep")
SWEEPS = {}          # id -> running RtlSweep (for /api/sweep)
MAX_EVENTS = 500


def device_conflict(inputs, spec):
    """Return the other enabled input that already uses this dongle index, or None."""
    if spec.get("type") not in DONGLE_TYPES or not spec.get("enabled", True):
        return None
    idx = int(float(spec.get("device_index") or 0))
    for i in inputs:
        if i.get("id") != spec.get("id") and i.get("type") in DONGLE_TYPES and i.get("enabled", True) \
                and int(float(i.get("device_index") or 0)) == idx:
            return i
    return None


def parse_bands(s):
    out = []
    for p in str(s or "").replace(";", ",").split(","):
        a = p.replace(" ", "").split("-")
        try:
            lo, hi = float(a[0]), float(a[1])
        except (ValueError, IndexError):
            continue
        if 24 <= lo < hi <= 1766:
            out.append((lo, hi))
    return out


def parse_allow(s):
    out = []
    for p in str(s or "").replace(";", ",").replace(" ", ",").split(","):
        try:
            out.append(float(p))
        except ValueError:
            pass
    return out


def parse_csv(text):
    """rtl_power CSV rows: date, time, Hz low, Hz high, Hz step, samples, dB, dB, ... -> (freqs_hz, dbs)."""
    fs, ds = [], []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 7:
            continue
        try:
            lo, step = float(row[2]), float(row[4]); vals = [float(x) for x in row[6:] if x.strip() not in ("", "nan", "-nan")]
        except ValueError:
            continue
        fs += [lo + step * (k + 0.5) for k in range(len(vals))]; ds += vals
    if not fs:
        return np.zeros(0), np.zeros(0)
    o = np.argsort(fs)
    return np.asarray(fs)[o], np.asarray(ds)[o]


class Detector:
    """Per-bin noise floor (slow average of quiet readings) + suspicious-activity events."""
    def __init__(self, threshold_db=10.0, allow=(), allow_tol_khz=12.5, alpha=0.2):
        self.th, self.allow, self.tol, self.alpha = float(threshold_db), list(allow), float(allow_tol_khz) / 1000, alpha
        self.floor, self.open, self.events = {}, {}, []

    def allowed(self, mhz):
        return any(abs(mhz - a) <= self.tol for a in self.allow)

    def feed(self, freqs_hz, dbs, t=None):
        """Returns the list of events opened by this sweep."""
        t = t or time.time(); new = []
        if not len(freqs_hz):
            return new
        med = float(np.median(dbs)); hot = []
        for f, d in zip(freqs_hz, dbs):
            k = int(round(f)); fl = self.floor.get(k, med)
            if d > fl + self.th:
                hot.append((f, d))
            else:
                self.floor[k] = fl + self.alpha * (d - fl)   # learn only from quiet readings
        # group adjacent hot bins into one signal at its peak
        step = float(np.median(np.diff(freqs_hz))) if len(freqs_hz) > 1 else 1e4
        groups, cur = [], []
        for f, d in hot:
            if cur and f - cur[-1][0] > step * 1.5:
                groups.append(cur); cur = []
            cur.append((f, d))
        if cur:
            groups.append(cur)
        seen = set()
        for g in groups:
            f, d = max(g, key=lambda x: x[1]); mhz = round(f / 1e6, 4)
            if self.allowed(mhz):
                continue
            key = next((k for k in self.open if abs(k - mhz) <= max(step * 2 / 1e6, 0.005)), None)
            if key is None:
                ev = dict(t=t, last=t, freq_mhz=mhz, peak_db=round(d, 1), floor_db=round(self.floor.get(int(round(f)), med), 1), duration_s=0.0)
                self.open[mhz] = ev; self.events.append(ev); new.append(ev); seen.add(mhz)
            else:
                ev = self.open[key]; ev["last"] = t; ev["duration_s"] = round(t - ev["t"], 1)
                ev["peak_db"] = max(ev["peak_db"], round(d, 1)); seen.add(key)
        for k in list(self.open):
            if k not in seen:
                del self.open[k]
        del self.events[:-MAX_EVENTS]
        return new

    def floor_for(self, freqs_hz, default):
        return [round(self.floor.get(int(round(f)), default), 1) for f in freqs_hz]


def events_csv(events):
    b = io.StringIO(); w = csv.writer(b)
    w.writerow(["time_local", "frequency_mhz", "peak_db", "floor_db", "duration_s", "monitor"])
    for e in events:
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e["t"])), e["freq_mhz"], e["peak_db"], e["floor_db"], e["duration_s"], e.get("monitor", "")])
    return b.getvalue()


@register
class RtlSweep(InputBase):
    TYPE, LABEL, LOCAL, KINDS = "rtl-sweep", "RTL-SDR spectrum sweep (activity monitor)", False, []
    FIELDS = [dict(k="name", label="Name", type="text"),
              dict(k="bands", label="Bands MHz (start-end, comma separated)", type="text"),
              dict(k="bin_khz", label="Bin size (kHz)", type="number", min=1, max=1000, step=0.5),
              dict(k="interval_s", label="Sweep every (s)", type="number", min=2, max=3600, step=1),
              dict(k="threshold_db", label="Alert above noise floor by (dB)", type="number", min=3, max=40, step=1),
              dict(k="allowlist", label="Allowlist MHz (expected signals, comma separated)", type="text"),
              dict(k="allow_tol_khz", label="Allowlist tolerance (kHz)", type="number", min=1, max=200, step=0.5),
              dict(k="speak_alerts", label="Speak alert for unknown signals", type="check"),
              dict(k="rf_gain", label="Tuner gain (auto or dB)", type="text"),
              dict(k="ppm", label="PPM correction", type="number", min=-200, max=200, step=1),
              dict(k="device_index", label="Dongle index", type="number", min=0, max=8, step=1)]
    popen = staticmethod(subprocess.Popen)

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        s = self.spec
        self.det = Detector(float(s.get("threshold_db") or 10), parse_allow(s.get("allowlist")), float(s.get("allow_tol_khz") or 12.5))
        self.last = dict(t=None, freqs=[], db=[], floor=[]); self.sweeps = 0

    def cmd(self, lo, hi):
        s = self.spec; c = ["rtl_power", "-d", str(int(float(s.get("device_index") or 0))),
                            "-f", f"{lo}M:{hi}M:{float(s.get('bin_khz') or 12.5)}k", "-i", "1", "-1"]
        g = str(s.get("rf_gain", "auto")).strip().lower()
        if g and g != "auto":
            c += ["-g", str(float(g))]
        if int(float(s.get("ppm") or 0)):
            c += ["-p", str(int(float(s.get("ppm"))))]
        return c + ["-"]

    def sweep_once(self):
        text = ""
        for lo, hi in parse_bands(self.spec.get("bands")) or [(430.0, 440.0)]:
            p = self.popen(self.cmd(lo, hi), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                out, err = p.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                p.kill(); raise RuntimeError("rtl_power timed out")
            if not out:
                raise RuntimeError("rtl_power gave no data (dongle unplugged or busy?): " + (err or b"").decode(errors="ignore")[-200:])
            text += out.decode(errors="ignore")
        f, d = parse_csv(text)
        if not len(f):
            raise RuntimeError("rtl_power output not understood")
        now = time.time(); new = self.det.feed(f, d, now); self.sweeps += 1
        med = float(np.median(d)); self.set_level(float(d.max()))
        k = max(1, len(f) // 400)                                 # keep the page light
        self.last = dict(t=now, freqs=[round(x / 1e6, 4) for x in f[::k]], db=[round(float(x), 1) for x in d[::k]],
                         floor=self.det.floor_for(f[::k], med))
        for e in new:
            e["monitor"] = self.spec.get("name") or self.id
            log.warning("sweep %s: unknown signal %.4f MHz peak %.1f dB", self.id, e["freq_mhz"], e["peak_db"])
            if self.spec.get("speak_alerts") and getattr(self.ctx, "speaker", None):
                threading.Thread(target=self.ctx.speaker.say, args=([f"Unknown signal at {e['freq_mhz']:.1f} megahertz"],), daemon=True).start()
        self.error = ""
        return new

    def run(self):
        SWEEPS[self.id] = self
        every = float(self.spec.get("interval_s") or 10)
        while not self.stop_ev.is_set():
            t0 = time.time(); self.sweep_once()
            self.stop_ev.wait(max(0.0, every - (time.time() - t0)))

    def snapshot(self):
        return dict(id=self.id, name=self.spec.get("name"), state=self.state, error=self.error, sweeps=self.sweeps,
                    threshold_db=self.det.th, allowlist=self.det.allow, latest=self.last, events=self.det.events[-100:][::-1])


def snapshot():
    return [s.snapshot() for s in SWEEPS.values() if not s.stop_ev.is_set()]


def all_events_csv():
    ev = sorted((e for s in SWEEPS.values() for e in s.det.events), key=lambda e: e["t"])
    return events_csv(ev)
