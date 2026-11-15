"""Independent multi-device audio router for Sanket Broadcast."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
import logging
import threading
from typing import Any
import numpy as np
import sounddevice as sd

log = logging.getLogger("sanket_broadcast.audio")


def discover_output_devices() -> list[dict[str, Any]]:
    devices = []
    hostapis = sd.query_hostapis()
    for index, dev in enumerate(sd.query_devices()):
        if int(dev.get("max_output_channels", 0)) < 1:
            continue
        devices.append({
            "runtime_index": index,
            "name": str(dev["name"]),
            "hostapi": str(hostapis[int(dev["hostapi"])]["name"]),
            "max_output_channels": int(dev["max_output_channels"]),
            "default_samplerate": int(dev["default_samplerate"]),
        })
    return devices


def resolve_device(selector: dict[str, str]) -> tuple[int, dict[str, Any]]:
    name = selector.get("name_contains", "").strip().casefold()
    host = selector.get("hostapi_contains", "").strip().casefold()
    if not name:
        raise ValueError("device.name_contains is required; numeric indexes are not stable")
    matches = [
        d for d in discover_output_devices()
        if name in d["name"].casefold()
        and (not host or host in d["hostapi"].casefold())
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Audio selector matched {len(matches)} devices; make it more specific")
    return matches[0]["runtime_index"], matches[0]


@dataclass
class _ChannelFIFO:
    chunks: deque[np.ndarray] = field(default_factory=deque)
    offset: int = 0

    def append(self, samples: np.ndarray, max_chunks: int = 100) -> None:
        if len(samples):
            self.chunks.append(np.asarray(samples, dtype=np.float32))
            while len(self.chunks) > max_chunks:
                self.chunks.popleft()
                self.offset = 0

    def read_into(self, target: np.ndarray) -> None:
        pos = 0
        while pos < len(target) and self.chunks:
            head = self.chunks[0]
            count = min(len(target) - pos, len(head) - self.offset)
            target[pos:pos + count] += head[self.offset:self.offset + count]
            pos += count
            self.offset += count
            if self.offset >= len(head):
                self.chunks.popleft()
                self.offset = 0


@dataclass
class _Output:
    config: dict[str, Any]
    device_index: int
    device_info: dict[str, Any]
    samplerate: int
    channels: int
    stream: Any = None
    fifos: dict[str, _ChannelFIFO] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
    state: str = "stopped"
    last_error: str = ""


class AudioRouter:
    """Fan out mono channel frames to independent physical output devices."""

    def __init__(self, config: dict[str, Any], input_rate: int = 12000):
        self.config = config
        self.input_rate = int(input_rate)
        self.outputs: dict[str, _Output] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _resample(pcm: np.ndarray, in_rate: int, out_rate: int) -> np.ndarray:
        src = np.asarray(pcm, dtype=np.float32).reshape(-1)
        if not len(src) or in_rate == out_rate:
            return src
        out_len = max(1, round(len(src) * out_rate / in_rate))
        old_x = np.arange(len(src), dtype=np.float64)
        new_x = np.arange(out_len, dtype=np.float64) * in_rate / out_rate
        return np.interp(new_x, old_x, src).astype(np.float32)

    def start(self) -> dict[str, Any]:
        results = {}
        with self._lock:
            for output_id, cfg in self.config.get("outputs", {}).items():
                try:
                    device_index, info = resolve_device(cfg["device"])
                    rate = int(cfg.get("samplerate") or info["default_samplerate"])
                    out_channels = min(int(cfg.get("output_channels", 2)), info["max_output_channels"])
                    if out_channels < 1:
                        raise RuntimeError("Selected device has no output channels")
                    state = _Output(cfg, device_index, info, rate, out_channels)

                    def callback(outdata, frames, time_info, status, state=state, cfg=cfg, oid=output_id):
                        if status:
                            log.debug("%s callback: %s", oid, status)
                        mix = np.zeros(frames, dtype=np.float32)
                        with state.lock:
                            for channel in cfg.get("channels", []):
                                fifo = state.fifos.get(channel)
                                if fifo is not None:
                                    fifo.read_into(mix)
                        gain = 0.0 if cfg.get("muted", False) else max(0.0, float(cfg.get("volume", 1.0)))
                        np.clip(mix * gain, -1.0, 1.0, out=mix)
                        outdata[:] = mix[:, None]

                    stream = sd.OutputStream(device=device_index, samplerate=rate,
                        channels=out_channels, dtype="float32", callback=callback,
                        blocksize=int(cfg.get("blocksize", 0)))
                    state.stream = stream
                    stream.start()
                    state.state = "running"
                    self.outputs[output_id] = state
                    results[output_id] = {"state": "running", "device": info}
                except Exception as exc:
                    log.exception("Unable to start output %s", output_id)
                    results[output_id] = {"state": "error", "error": str(exc)}
        return results

    def push(self, channel: str, pcm: np.ndarray, sample_rate: int | None = None) -> int:
        rate = int(sample_rate or self.input_rate)
        routed = 0
        with self._lock:
            for state in self.outputs.values():
                if state.state != "running" or channel not in state.config.get("channels", []):
                    continue
                samples = self._resample(pcm, rate, state.samplerate)
                if np.issubdtype(np.asarray(pcm).dtype, np.integer):
                    samples = samples / 32768.0
                with state.lock:
                    state.fifos.setdefault(channel, _ChannelFIFO()).append(samples)
                routed += 1
        return routed

    def set_output(self, output_id: str, *, volume: float | None = None,
                   muted: bool | None = None, channels: list[str] | None = None) -> None:
        with self._lock:
            state = self.outputs[output_id]
            if volume is not None:
                state.config["volume"] = min(2.0, max(0.0, float(volume)))
            if muted is not None:
                state.config["muted"] = bool(muted)
            if channels is not None:
                state.config["channels"] = list(dict.fromkeys(channels))

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {key: {
                "state": value.state, "device": value.device_info,
                "channels": list(value.config.get("channels", [])),
                "volume": value.config.get("volume", 1.0),
                "muted": value.config.get("muted", False),
                "last_error": value.last_error,
            } for key, value in self.outputs.items()}

    def stop(self) -> None:
        with self._lock:
            for state in self.outputs.values():
                try:
                    if state.stream:
                        state.stream.stop()
                        state.stream.close()
                except Exception:
                    log.exception("Error stopping output")
                state.state = "stopped"
            self.outputs.clear()
