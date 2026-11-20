"""Offline TTS (piper or espeak-ng) + the speaker queue: clip audio, beep, spoken announcement."""
import datetime as dt, os, shutil, subprocess, threading
import numpy as np
from .util import APP_DIR, RATE, log, write_wav


def synth(cfg, text, path):
    if cfg["tts_engine"] == "piper" and cfg["piper_model"] and os.path.exists(os.path.expanduser(cfg["piper_model"])):
        exe = shutil.which("piper") or os.path.join(APP_DIR, "venv/bin/piper")
        if os.path.exists(exe):
            subprocess.run([exe, "--model", os.path.expanduser(cfg["piper_model"]), "--output_file", path],
                           input=text.encode(), check=True, capture_output=True, timeout=120)
            return "piper"
    for exe in ("espeak-ng", "espeak"):
        if shutil.which(exe):
            subprocess.run([exe, "-v", cfg["espeak_voice"] or "en", "-s", str(int(cfg["tts_speed"])), "-w", path, text],
                           check=True, capture_output=True, timeout=60)
            return exe
    raise RuntimeError("no offline TTS engine installed (espeak-ng / piper)")


def beep(path):
    t = np.arange(int(RATE * 0.15)) / RATE
    b = (0.35 * np.sin(2 * np.pi * 1000 * t) * 32767).astype(np.int16)
    write_wav(path, np.concatenate([b, np.zeros(int(RATE * .08), np.int16), b]))


def lines_for(cfg, meta):
    if not cfg["announce"]:
        return []
    chn = meta["channel"].replace("-", " ").replace("_", " ")
    if meta["type"] == "sstv":
        return [f"New SSTV picture on {chn} from {meta['speaker']}"]
    tpl = cfg["announce_template"] if cfg["announce_speaker"] else "New message on {channel}"
    try:
        out = [tpl.format(channel=chn, name=meta["speaker"])]
    except Exception:
        out = [f"New message on {chn}"]
    if meta.get("keywords"):
        out.insert(0, "Alert! Alert!")
    if cfg["announce_transcript"] and meta.get("text"):
        out.append(meta["text"])
    return out


class Speaker:
    """Serialises everything that comes out of the speaker."""
    def __init__(self, cfg, tmp, player):
        self.cfg, self.tmp, self.player, self.lock = cfg, tmp, player, threading.Lock()
        self.busy = False

    def say(self, lines, clip=None):
        with self.lock:
            self.busy = True
            stamp = dt.datetime.now().strftime("%H%M%S%f")
            try:
                if clip and self.cfg["play_audio"]:
                    self.player.play(clip)
                if self.cfg["beep"] and lines:
                    p = os.path.join(self.tmp, f"beep_{stamp}.wav"); beep(p); self.player.play(p)
                for i, text in enumerate(l for l in lines if l):
                    p = os.path.join(self.tmp, f"tts_{stamp}_{i}.wav")
                    eng = synth(self.cfg, text, p); log.info("TTS (%s): %s", eng, text); self.player.play(p)
                return True
            except Exception as e:
                log.error("announcement failed: %s", e); return False
            finally:
                self.busy = False
