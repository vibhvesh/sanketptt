import argparse, logging, os
from .config import Config
from .ingest import Ingest
from .store import Store
from .stt import STT
from .mixer import Mixer
from .web import serve
from .retention import Retention
from .e2e import KeyStore
from . import VERSION

class App:
    def __init__(self, cfg_path):
        self.cfg = Config(cfg_path)
        os.makedirs(self.cfg["data_dir"], exist_ok=True)
        self.store = Store(self.cfg["data_dir"], self.cfg["rate"])
        self.stt = STT(self.cfg, self.store)
        self.mixer = Mixer(self.cfg)
        self.retention = Retention(self.cfg, self.store)
        self.keys = KeyStore(os.path.join(self.cfg["data_dir"], "keys.json"))
        self.ingest = Ingest(self.cfg, self.on_segment, self.mixer.feed, self.keys)
    def on_segment(self, st):
        sid, pcm, dur = self.store.save(st)
        logging.info("segment %s %s/%s %.1fs", sid, st.ch, st.name, dur)
        self.stt.submit(sid, st.ch, pcm)
    def run(self):
        logging.info("SuperPTT control room %s on :%s", VERSION, self.cfg["http_port"])
        self.stt.start(); self.retention.start(); self.mixer.start(); self.ingest.start()
        srv = serve(self)
        import threading, time as _t
        def _tun():
            while True: self.tunnel.get(); _t.sleep(30)     # logs the public URL when it appears
        threading.Thread(target=_tun, daemon=True).start()
        srv.serve_forever()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-c", "--config", default="config.json")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    App(a.config).run()
