"""Local audio inputs: the Pi's attached mic, USB mics / sound cards (any number, one channel each), Bluetooth mics.
Each streams raw PCM from arecord/parec, shows a level meter, and cuts clips with VOX."""
import subprocess
import numpy as np
from .registry import InputBase, register
from .vox import Vox
from ..audio_io import capture_cmd
from ..util import log

CAP_RATE = 16000
COMMON = [dict(k="name", label="Name / channel label", type="text"),
          dict(k="device", label="Input device", type="device"),
          dict(k="vox_threshold", label="VOX threshold (dBFS)", type="range", min=-70, max=-5, step=1),
          dict(k="vox_hang_s", label="VOX hang time (s)", type="number", min=0.2, max=5, step=0.1),
          dict(k="gain", label="Gain (x)", type="number", min=0.1, max=10, step=0.1),
          dict(k="forward", label="Also forward to relay (transmit)", type="check"),
          dict(k="forward_channel", label="Forward to channel", type="text")]


class LocalAudio(InputBase):
    LOCAL, FIELDS = True, COMMON

    def run(self):
        s = self.spec
        vox = Vox(CAP_RATE, s.get("vox_threshold", -40), s.get("vox_hang_s", 1.2), s.get("min_clip_s", 0.6), s.get("max_clip_s", 60))
        cmd = capture_cmd(s.get("device") or "default", CAP_RATE)
        log.info("input %s capturing: %s", self.id, " ".join(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        blk = CAP_RATE // 10; gain = float(s.get("gain", 1.0))
        try:
            while not self.stop_ev.is_set():
                raw = p.stdout.read(blk * 2)
                if not raw:
                    raise RuntimeError("capture ended: " + p.stderr.read(400).decode(errors="ignore").strip())
                x = np.frombuffer(raw[: len(raw) // 2 * 2], "<i2")
                if gain != 1.0:
                    x = np.clip(x.astype(np.float32) * gain, -32768, 32767).astype(np.int16)
                db, clip = vox.feed(x); self.set_level(db); self.error = ""
                if clip is not None:
                    self.emit(clip, CAP_RATE)
        finally:
            p.kill()


@register
class PiMic(LocalAudio):
    TYPE, LABEL, KINDS = "mic", "Pi attached mic", ["default", "other", "jack"]


@register
class UsbMic(LocalAudio):
    TYPE, LABEL, KINDS = "usb", "USB mic / sound card", ["usb"]


@register
class BluetoothMic(LocalAudio):
    TYPE, LABEL, KINDS = "bluetooth", "Bluetooth mic", ["bluetooth"]
