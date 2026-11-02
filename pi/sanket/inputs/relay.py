"""Relay inputs: the main Sanket PTT relay (channels list on the Channels tab) and any number of extra
PTT web-relay channels, each with an editable https link (…?ch=name) and/or broker URL."""
import re, threading
from urllib.parse import urlparse, parse_qs
from .registry import InputBase, register
from ..config import BROKERS
from ..mqtt_relay import RelayClient
from ..util import clean_ch, log


def parse_link(url, broker="", channel=""):
    """Accepts https://…/sanketptt/?ch=foo[&broker=wss://…] or wss://broker… ; returns (broker, channel)."""
    url = (url or "").strip()
    if url.startswith(("ws://", "wss://", "mqtt://", "mqtts://")):
        return url, clean_ch(channel)
    if url:
        q = parse_qs(urlparse(url).query)
        channel = channel or (q.get("ch") or q.get("channel") or [""])[0]
        broker = broker or (q.get("broker") or [""])[0]
    return broker or BROKERS[0], clean_ch(channel)


@register
class RelayInput(InputBase):
    TYPE, LABEL = "relay", "PTT web relay channel"
    FIELDS = [dict(k="name", label="Name", type="text"),
              dict(k="url", label="PTT link (https://…/?ch=name)", type="text"),
              dict(k="broker_url", label="Relay broker (wss://…)", type="broker"),
              dict(k="channel", label="Channel name", type="text")]

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.main = bool(spec.get("main"))
        self.client = RelayClient(self.opts, self._clip, ctx.name, self._discover if self.main else None)

    def opts(self):
        if self.main:
            c = self.ctx.cfg
            return dict(broker_url=c["broker_url"], channels=c.enabled(), listen_all=c["listen_all"], discover=c["auto_add_discovered"])
        b, ch = parse_link(self.spec.get("url"), self.spec.get("broker_url"), self.spec.get("channel"))
        return dict(broker_url=b, channels=[ch] if ch else [], listen_all=False, discover=False)

    def _discover(self, ch):
        c = self.ctx.cfg
        if c["auto_add_discovered"] and ch not in {x["name"] for x in c["channels"]}:
            c.update({"channels": c["channels"] + [{"name": ch, "enabled": True}]}); log.info("discovered channel '%s' - added", ch)

    def _clip(self, k):
        self.set_level(self.client.level)
        self.emit(k["i16"], k["rate"], speaker=k["speaker"], channel=k["channel"], t=k["t"], sstv_meta=k["sstv_meta"])

    def run(self):
        self.client.connect(); n = 0
        while not self.stop_ev.wait(1):
            n += 1
            self.client.tick()
            if n % 5 == 0:
                self.client.beat()                       # retained presence heartbeat
            if any(S["floor"] for S in list(self.client.chs.values())):
                self.set_level(self.client.level)
            self.error = self.client.err
            self.state = "connected" if self.client.connected else "connecting"
        self.client.close()

    def status(self):
        s = super().status(); s.update(relay=self.client.status(), opts={k: v for k, v in self.opts().items()})
        s["opts"]["broker_url"] = re.sub(r"//.*@", "//", s["opts"]["broker_url"])
        return s
