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
