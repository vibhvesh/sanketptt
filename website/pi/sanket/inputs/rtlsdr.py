"""RTL-SDR receiver input: tunes a cheap RTL2832U dongle with rtl_fm (rtl-sdr package) and reads raw
16 kHz mono s16le PCM from its stdout, then cuts clips with the same VOX as the mic inputs.
Lightweight (one rtl_fm process, numpy only) so it runs on Pi 3 and Pi 5.

Optional scan list: hop through frequencies, staying `dwell_s` on each and holding while a
transmission is in progress. Receive only; listen only to bands you are allowed to monitor."""
import shutil, subprocess, time
import numpy as np
from .registry import InputBase, register
from .vox import Vox
from ..util import log

OUT_RATE = 16000
MODES = {  # mode -> (rtl_fm -M, default -s sample rate, extra args)
    "wbfm": ("wbfm", 170000, ["-E", "deemp"]),
    "fm":   ("fm", 32000, []),
    "nfm":  ("fm", 24000, []),
    "am":   ("am", 24000, []),
}
PRESETS = [
    dict(k="fm_broadcast", label="FM broadcast 88-108 MHz (WBFM)", freq_mhz=98.3, mode="wbfm", squelch=0, scan=""),
    dict(k="airband", label="Airband 118-137 MHz (AM)", freq_mhz=121.5, mode="am", squelch=60, scan=""),
    dict(k="ham_2m", label="2 m ham 144-146 MHz (NFM)", freq_mhz=145.5, mode="nfm", squelch=60, scan=""),
    dict(k="ham_70cm", label="70 cm ham 430-440 MHz (NFM)", freq_mhz=433.5, mode="nfm", squelch=60, scan=""),
    dict(k="marine", label="Marine VHF 156-162 MHz (NFM)", freq_mhz=156.8, mode="nfm", squelch=60, scan="156.800,156.300,156.650"),
]


def parse_freqs(s):
    out = []
    for p in str(s or "").replace(";", ",").replace(" ", ",").split(","):
        try:
            f = float(p)
        except ValueError:
            continue
        if 24 <= f <= 1766:          # R820T tuning range in MHz
            out.append(f)
    return out


def build_cmd(spec, freq_mhz):
    mode = str(spec.get("mode") or "nfm").lower()
    m, sr_def, extra = MODES.get(mode, MODES["nfm"])
    try:
        sr = int(float(spec.get("sample_rate") or sr_def))
    except ValueError:
        sr = sr_def
    cmd = ["rtl_fm", "-d", str(int(spec.get("device_index") or 0)), "-f", f"{int(round(freq_mhz * 1e6))}",
           "-M", m, "-s", str(sr), "-r", str(OUT_RATE)] + extra
    g = str(spec.get("rf_gain", "auto")).strip().lower()
    if g and g != "auto":
        cmd += ["-g", str(float(g))]
    sq = int(float(spec.get("squelch") or 0))
    if sq > 0:
        cmd += ["-l", str(sq), "-E", "pad"]   # pad: keep streaming zeros while squelched
    ppm = int(float(spec.get("ppm") or 0))
    if ppm:
        cmd += ["-p", str(ppm)]
    return cmd + ["-"]


def detect(timeout=6):
    """Run rtl_test briefly and report the dongles it sees (for the web 'Detect dongle' button)."""
    if not shutil.which("rtl_test"):
        return dict(ok=False, found=0, output="rtl_test not installed (re-run the installer)")
    try:
        p = subprocess.run(["rtl_test", "-t"], capture_output=True, text=True, timeout=timeout)
        out = (p.stdout + p.stderr)
    except subprocess.TimeoutExpired as e:
        out = "".join(x.decode(errors="ignore") if isinstance(x, bytes) else (x or "") for x in (e.stdout, e.stderr))
    found = 0
    for line in out.splitlines():
        if line.startswith("Found ") and "device" in line:
            try:
                found = int(line.split()[1])
            except ValueError:
                pass
    return dict(ok=found > 0, found=found, output=out[-1500:])


@register
class RtlSdr(InputBase):
    TYPE, LABEL, LOCAL, KINDS = "rtl-sdr", "RTL-SDR receiver", True, []
    PRESETS = PRESETS
    FIELDS = [dict(k="name", label="Name / channel label", type="text"),
              dict(k="preset", label="Band preset", type="rtlpreset"),
              dict(k="freq_mhz", label="Frequency (MHz)", type="number", min=24, max=1766, step=0.0125),
              dict(k="mode", label="Mode", type="select", options=["nfm", "fm", "wbfm", "am"]),
              dict(k="squelch", label="Squelch (rtl_fm level, 0 = off)", type="number", min=0, max=500, step=1),
              dict(k="rf_gain", label="Tuner gain (auto or dB)", type="text"),
              dict(k="sample_rate", label="Sample rate (Hz, blank = mode default)", type="number", min=8000, max=2400000, step=1000),
              dict(k="ppm", label="PPM correction", type="number", min=-200, max=200, step=1),
              dict(k="device_index", label="Dongle index", type="number", min=0, max=8, step=1),
              dict(k="scan", label="Scan list MHz (comma separated, optional)", type="text"),
              dict(k="dwell_s", label="Dwell per frequency (s)", type="number", min=1, max=600, step=1),
              dict(k="vox_threshold", label="VOX threshold (dBFS)", type="range", min=-70, max=-5, step=1),
              dict(k="vox_hang_s", label="VOX hang time (s)", type="number", min=0.2, max=5, step=0.1),
              dict(k="gain", label="Audio gain (x)", type="number", min=0.1, max=10, step=0.1),
              dict(k="forward", label="Also forward to relay (transmit)", type="check"),
              dict(k="forward_channel", label="Forward to channel", type="text")]
    popen = staticmethod(subprocess.Popen)       # tests replace this with a mock rtl_fm

    def freqs(self):
        return parse_freqs(self.spec.get("scan")) or [float(self.spec.get("freq_mhz") or 145.5)]

    def run(self):
        s, fl = self.spec, self.freqs()
        dwell = float(s.get("dwell_s") or 5) if len(fl) > 1 else None
        gain = float(s.get("gain", 1.0)); blk = OUT_RATE // 10; i = 0
        vox = Vox(OUT_RATE, s.get("vox_threshold", -40), s.get("vox_hang_s", 1.2), s.get("min_clip_s", 0.6), s.get("max_clip_s", 60))
        while not self.stop_ev.is_set():
            f = fl[i % len(fl)]; i += 1; self.freq = f
            cmd = build_cmd(s, f); log.info("input %s tuning: %s", self.id, " ".join(cmd))
            p = self.popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            t0 = time.time()
            try:
                while not self.stop_ev.is_set():
                    raw = p.stdout.read(blk * 2)
                    if not raw:
                        err = p.stderr.read(400).decode(errors="ignore").strip() if p.stderr else ""
                        raise RuntimeError("rtl_fm ended (dongle unplugged or busy?): " + err)
                    x = np.frombuffer(raw[: len(raw) // 2 * 2], "<i2")
                    if gain != 1.0:
                        x = np.clip(x.astype(np.float32) * gain, -32768, 32767).astype(np.int16)
                    db, clip = vox.feed(x); self.set_level(db); self.error = ""
                    if clip is not None:
                        self.emit(clip, OUT_RATE, speaker=f"{s.get('name') or self.id} {f:g} MHz")
                    if dwell and not vox.active and time.time() - t0 >= dwell:
                        break                  # hop to next frequency (never mid-transmission)
            finally:
                p.kill()
            if not dwell:
                return

    def status(self):
        d = super().status(); d["freq_mhz"] = getattr(self, "freq", None); return d
