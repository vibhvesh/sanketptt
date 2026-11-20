"""Live system stats: CPU %, temperature, RAM, disk, uptime, network rates, Wi-Fi, throttling. Tiny history ring."""
import collections, os, shutil, socket, threading, time
from .util import sh


def ips():
    return [x for x in sh(["hostname", "-I"]).split() if ":" not in x]


class SysMon:
    def __init__(self, path="/"):
        self.path, self.hist = path, collections.deque(maxlen=360)
        self._cpu = self._read_cpu(); self._net = self._read_net(); self._t = time.time()
        self.last = {}; self.lock = threading.Lock()
        self.sample()

    @staticmethod
    def _read_cpu():
        try:
            v = [int(x) for x in open("/proc/stat").readline().split()[1:]]
            return sum(v), v[3] + (v[4] if len(v) > 4 else 0)
        except Exception:
            return 0, 0

    @staticmethod
    def _read_net():
        rx = tx = 0
        try:
            for line in open("/proc/net/dev").readlines()[2:]:
                name, data = line.split(":", 1)
                if name.strip() == "lo":
                    continue
                f = data.split(); rx += int(f[0]); tx += int(f[8])
        except Exception:
            pass
        return rx, tx

    @staticmethod
    def temp():
        for p in ("/sys/class/thermal/thermal_zone0/temp",):
            try:
                return round(int(open(p).read()) / 1000, 1)
            except Exception:
                pass
        out = sh(["vcgencmd", "measure_temp"], 3)
        try:
            return float(out.split("=")[1].split("'")[0])
        except Exception:
            return None

    @staticmethod
    def mem():
        m = {}
        try:
            for line in open("/proc/meminfo"):
                k, v = line.split(":"); m[k] = int(v.split()[0]) * 1024
        except Exception:
            return dict(total=0, used=0, pct=0)
        tot, av = m.get("MemTotal", 0), m.get("MemAvailable", m.get("MemFree", 0))
        return dict(total=tot, used=tot - av, pct=round(100 * (tot - av) / tot, 1) if tot else 0)

    @staticmethod
    def uptime():
        try:
            return int(float(open("/proc/uptime").read().split()[0]))
        except Exception:
            return 0

    @staticmethod
    def wifi():
        ssid = sh(["iwgetid", "-r"], 3); sig = None
        try:
            for line in open("/proc/net/wireless").readlines()[2:]:
                sig = int(float(line.split()[3].rstrip(".")))
        except Exception:
            pass
        return dict(ssid=ssid, signal_dbm=sig)

    def sample(self):
        now = time.time()
        tot, idle = self._read_cpu(); rx, tx = self._read_net()
        with self.lock:
            dt_ = max(now - self._t, 1e-3); dtot = tot - self._cpu[0]
            cpu = round(100 * (1 - (idle - self._cpu[1]) / dtot), 1) if dtot > 0 else 0.0
            rxr, txr = (rx - self._net[0]) / dt_, (tx - self._net[1]) / dt_
            self._cpu, self._net, self._t = (tot, idle), (rx, tx), now
            du = shutil.disk_usage(self.path)
            try:
                load = os.getloadavg()
            except Exception:
                load = (0, 0, 0)
            thr = sh(["vcgencmd", "get_throttled"], 3).split("=")[-1] if shutil.which("vcgencmd") else ""
            self.last = dict(t=int(now), cpu=cpu, cpus=os.cpu_count(), load=[round(x, 2) for x in load], temp=self.temp(),
                             mem=self.mem(), disk=dict(total=du.total, used=du.used, pct=round(100 * du.used / du.total, 1)),
                             uptime=self.uptime(), net=dict(rx_bps=int(max(rxr, 0)), tx_bps=int(max(txr, 0)), ips=ips(),
                                                             host=socket.gethostname(), **self.wifi()),
                             throttled=thr)
            self.hist.append(dict(t=int(now), cpu=cpu, temp=self.last["temp"], mem=self.last["mem"]["pct"]))
            return self.last

    def snapshot(self):
        with self.lock:
            return dict(now=self.last, history=list(self.hist))

    def loop(self, stop, every=5):
        while not stop.wait(every):
            try:
                self.sample()
            except Exception:
                pass
