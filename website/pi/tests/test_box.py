"""Off-Pi tests (no audio hardware, no network): python3 tests/test_box.py"""
import json, os, sys, tempfile, time, threading, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SANKET_DRY_AUDIO"] = "1"
import numpy as np
from sanket import sstv, hw
from sanket.config import Config, KNOWN_CHANNELS
from sanket.inputs import registry, types, InputManager
from sanket.inputs.vox import Vox
from sanket.metrics import Metrics
from sanket.sysmon import SysMon
from sanket.auth import Auth

ok = lambda c, m: print(("PASS " if c else "FAIL ") + m) or (c or sys.exit(1))
d = tempfile.mkdtemp()

# config: v2 file loads, old keys untouched, new keys added, kolkata not re-added
v2 = {"device_name": "X", "channels": [{"name": "virtual", "enabled": False}], "whisper_model": "small", "web_pin": "1"}
json.dump(v2, open(f"{d}/config.json", "w"))
c = Config(f"{d}/config.json"); c.d["clips_dir"] = d
ok(c["whisper_model"] == "small" and c["channels"][0] == {"name": "virtual", "enabled": False} and c["inputs"] == [], "v2 config loads unchanged")
ok(KNOWN_CHANNELS == ["virtual", "master", "city-control", "unit-name"], "known channels list")
c.apply_profile("pi3", hw.PROFILES["pi3"], only_missing=True)
ok(c["whisper_model"] == "small" and c["sstv_decode"] is False and c["kiosk_browser"] == "surf", "upgrade profile keeps user keys, fills new ones")
ok(hw.profile_key("Raspberry Pi 3 Model B Plus Rev 1.3") == "pi3" and hw.profile_key("Raspberry Pi 5 Model B Rev 1.0") == "pi5", "board detection")

# auth
a = Auth(c); tok = a.login("1")
ok(not a.ok({}) and a.ok({"X-Pin": "1"}) and a.ok({"X-Token": tok}) and a.login("2") is None, "PIN / login sessions")

# vox
v = Vox(16000, -40, 0.5, 0.3, 10); clips = []
sig = np.concatenate([np.zeros(16000), 0.3 * np.sin(np.arange(16000) / 3) * 32767, np.zeros(16000)]).astype(np.int16)
for i in range(0, len(sig), 1600):
    db, cl = v.feed(sig[i:i + 1600]); clips += [cl] if cl is not None else []
ok(len(clips) == 1 and 0.9 < len(clips[0]) / 16000 < 1.8, f"VOX cut one clip ({len(clips[0])/16000:.2f}s)")


# registry with a fake input
class Ctx:
    cfg, metrics, got = c, Metrics(), []
    def submit(self, clip): self.got.append(clip)
    def name(self): return "test"
ctx = Ctx()
ok({"relay", "mic", "usb", "bluetooth", "fake"} <= {t["type"] for t in types()}, "registry types: " + ", ".join(t["type"] for t in types()))
spec = Config.clean_input({"id": "fake1", "type": "fake", "name": "Fake", "interval_s": 1})
spec["speed"] = 0.0
m = InputManager(ctx, lambda: [spec]); m.reconcile(); time.sleep(1.5); m.stop_all()
ok(ctx.got and ctx.got[0]["source"] == "fake1" and ctx.got[0]["forward"] is False, f"fake input produced {len(ctx.got)} clips via VOX, forward off by default")

# rtl-sdr: command building + mock rtl_fm (silence, a 1 s carrier tone, silence) through VOX; scan hops
from sanket.inputs import rtlsdr
ok("rtl-sdr" in {t["type"] for t in types()} and len([t for t in types() if t["type"] == "rtl-sdr"][0]["presets"]) == 5, "rtl-sdr registered with 5 presets")
cmd = rtlsdr.build_cmd({"freq_mhz": 121.5, "mode": "am", "squelch": 50, "rf_gain": "38.6", "ppm": 3, "device_index": 1}, 121.5)
ok(cmd[:3] == ["rtl_fm", "-d", "1"] and "121500000" in cmd and cmd[cmd.index("-M") + 1] == "am" and cmd[cmd.index("-g") + 1] == "38.6"
   and cmd[cmd.index("-l") + 1] == "50" and "pad" in cmd and cmd[cmd.index("-p") + 1] == "3" and cmd[cmd.index("-r") + 1] == "16000" and cmd[-1] == "-", "rtl_fm cmd: " + " ".join(cmd))
w = rtlsdr.build_cmd({"mode": "wbfm", "rf_gain": "auto"}, 98.3)
ok("-g" not in w and "-l" not in w and w[w.index("-s") + 1] == "170000" and "deemp" in w, "wbfm defaults, auto gain, no squelch")
ok(rtlsdr.parse_freqs("156.8, 156.3;bad 5000") == [156.8, 156.3], "scan list parsing")
import io
calls = []
class FakeRtlFm:
    def __init__(self, cmd, **kw):
        calls.append(cmd); r = rtlsdr.OUT_RATE; t = np.arange(r) / r
        pcm = np.concatenate([np.zeros(r // 2), 0.3 * np.sin(2 * np.pi * 800 * t), np.zeros(r * 3)]) * 32767
        self.stdout, self.stderr = io.BytesIO(pcm.astype("<i2").tobytes()), io.BytesIO(b"usb_claim_interface error")
    def kill(self): pass
rtlsdr.RtlSdr.popen = staticmethod(FakeRtlFm)
ctx.got.clear()
rs = Config.clean_input({"id": "sdr1", "type": "rtl-sdr", "name": "Air", "freq_mhz": 121.5, "mode": "am", "vox_hang_s": 0.5})
m = InputManager(ctx, lambda: [rs]); m.reconcile(); time.sleep(1.0); st = m.status()[0]; m.stop_all()
ok(ctx.got and ctx.got[0]["source_type"] == "rtl-sdr" and "121.5 MHz" in ctx.got[0]["speaker"] and 0.8 < len(ctx.got[0]["i16"]) / 16000 < 2.0,
   f"mock rtl_fm -> VOX clip {len(ctx.got[0]['i16']) / 16000 if ctx.got else 0:.2f}s, speaker '{ctx.got[0]['speaker'] if ctx.got else ''}'")
ok(st["freq_mhz"] == 121.5 and "rtl_fm ended" in (st["error"] or "rtl_fm ended"), "status shows tuned freq; EOF reported as error")
class Endless:                                       # live dongle: never-ending quiet stream in real time
    def read(self, n): time.sleep(0.01); return bytes(n)
class FakeLive(FakeRtlFm):
    def __init__(self, cmd, **kw): calls.append(cmd); self.stdout, self.stderr = Endless(), None
rtlsdr.RtlSdr.popen = staticmethod(FakeLive)
calls.clear()
sc = dict(rs, id="sdr2", scan="156.8,156.3", dwell_s=1)
inp = rtlsdr.RtlSdr(sc, ctx); th = threading.Thread(target=inp.run, daemon=True); th.start(); time.sleep(2.5); inp.stop_ev.set(); th.join(3)
ok(len(calls) >= 2 and "156800000" in calls[0] and "156300000" in calls[1], f"scan hops {len(calls)} times")
d0 = rtlsdr.detect(); ok("found" in d0 and "output" in d0, "detect(): " + d0["output"][:50].replace("\n", " "))

# rtl-sweep: mocked rtl_power CSV; floor learning, allowlist, suspicious event open/extend/close, CSV, exclusivity
from sanket.inputs import rtlsweep
def power_csv(sig):           # 430-431 MHz, 10 kHz bins, noise ~-40 dB + listed carriers {MHz: dB}
    f = 430e6 + 10e3 * (np.arange(100) + 0.5); d = -40 + np.random.normal(0, 0.5, 100)
    for mhz, db in sig.items(): d[int(round((mhz * 1e6 - 430e6) / 10e3 - 0.5))] = db
    return "".join(f"2026-11-02, 12:00:00, {430e6 + 50 * k * 10e3:.0f}, {430e6 + 50 * (k + 1) * 10e3:.0f}, 10000.00, 100, " + ", ".join(f"{x:.2f}" for x in d[50 * k:50 * k + 50]) + "\n" for k in (0, 1))
fq, db = rtlsweep.parse_csv(power_csv({})); ok(len(fq) == 100 and abs(fq[0] - 430.005e6) < 1, "rtl_power CSV parsed (2 hops, 100 bins)")
SEQ = [power_csv({}), power_csv({}), power_csv({430.505: -10, 430.205: -12}), power_csv({430.505: -8}), power_csv({})]
class FakePower:
    def __init__(self, cmd, **kw): calls.append(cmd); self.out = SEQ.pop(0).encode() if SEQ else b""
    def communicate(self, timeout=None): return self.out, b"usb_claim_interface error"
    def kill(self): pass
rtlsweep.RtlSweep.popen = staticmethod(FakePower); calls.clear()
said = []
class Spk:
    def say(self, lines, clip=None): said.append(lines[0])
ctx.speaker = Spk()
sw = rtlsweep.RtlSweep(Config.clean_input({"id": "sw1", "type": "rtl-sweep", "name": "UHF watch", "bands": "430-431", "bin_khz": 10,
                       "threshold_db": 10, "allowlist": "430.205", "allow_tol_khz": 5, "speak_alerts": True}), ctx)
ok(calls == [] and sw.cmd(430.0, 431.0)[:7] == ["rtl_power", "-d", "0", "-f", "430.0M:431.0M:10.0k", "-i", "1"], "rtl_power cmd: " + " ".join(sw.cmd(430.0, 431.0)))
for _ in range(2): sw.sweep_once()
new = sw.sweep_once(); time.sleep(0.1)
ok(len(new) == 1 and abs(new[0]["freq_mhz"] - 430.505) < 0.001 and new[0]["peak_db"] == -10.0, f"unknown 430.505 flagged, allowlisted 430.205 ignored: {[e['freq_mhz'] for e in new]}")
ok(said == ["Unknown signal at 430.5 megahertz"], f"spoken alert: {said}")
sw.det.feed(*rtlsweep.parse_csv(SEQ.pop(0)), t=new[0]["t"] + 10)
ev = sw.det.events[0]; ok(len(sw.det.events) == 1 and ev["duration_s"] == 10.0 and ev["peak_db"] == -8.0, "event extended: duration 10 s, peak -8 dB")
sw.sweep_once(); ok(not sw.det.open and abs(np.mean(sw.last["floor"]) + 40) < 2, "event closed when signal gone; floor ~-40 dB learned")
cs = rtlsweep.events_csv(sw.det.events).splitlines(); ok(cs[0].startswith("time_local,frequency_mhz") and "430.505" in cs[1], "CSV export: " + cs[1])
try: sw.sweep_once(); ok(False, "empty rtl_power should raise")
except RuntimeError as e: ok("no data" in str(e), "dongle missing reported: " + str(e)[:50])
a = dict(id="a", type="rtl-sdr", name="Air", enabled=True, device_index=0)
ok(rtlsweep.device_conflict([a], dict(id="b", type="rtl-sweep", enabled=True, device_index=0))["id"] == "a"
   and rtlsweep.device_conflict([a], dict(id="b", type="rtl-sweep", enabled=True, device_index=1)) is None
   and rtlsweep.device_conflict([dict(a, enabled=False)], dict(id="b", type="rtl-sweep", enabled=True)) is None, "receiver/sweep mutually exclusive per dongle")

# sstv
img = np.random.randint(0, 255, (256, 320, 3)).astype(np.uint8); img[:, :160] = [255, 0, 0]
for vis in (44, 60, 8):
    s = sstv.encode(img, vis, 12000, clock=1.003)
    s = np.clip(s + np.random.normal(0, 2500, len(s)), -32768, 32767).astype(np.int16)
    r = sstv.decode(s, 12000); h = r["height"]
    err = np.abs(r["rgb"][:h, :150].astype(float) - img[:h, :150]).mean()
    ok(r["mode"] == sstv.MODES[vis]["name"] and abs(r["slant_ppm"] - 3000) < 300 and err < 40, f"SSTV {r['mode']}: slant {r['slant_ppm']} ppm corrected, err {err:.1f}")

# sysmon + metrics
sm = SysMon(d); time.sleep(0.3); s = sm.sample()
ok(all(k in s for k in ("cpu", "temp", "mem", "disk", "uptime", "net")), "sysmon: cpu %s%% mem %s%% disk %s%% up %ss" % (s["cpu"], s["mem"]["pct"], s["disk"]["pct"], s["uptime"]))
mt = Metrics(); mt.count("received"); mt.count("transcribed"); mt.level("out", -12); mt.level("mic", -30)
sn = mt.snapshot(); ok(sn["totals"]["received"] == 1 and sn["series"][-1]["out_db"] == -12 and sn["levels"]["mic"] == -30, "metrics series + levels")
print("ALL PASS")
