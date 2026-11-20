"""SuperPTT LAN STT worker: run on a second Pi 5 or a PC (CUDA used automatically if present).
Pulls jobs from the control room's queue and posts transcripts back.
  pip install faster-whisper numpy
  python worker.py --url http://superptt.local:8090 --token <worker token> [--model small] [--threads 4]
"""
import argparse, base64, json, logging, time, urllib.request
import numpy as np
from superptt.stt import Whisper, to16k

def call(url, token, path, body=None):
    r = urllib.request.Request(url + path, json.dumps(body or {}).encode(),
                               {"X-Worker": token, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=30).read())

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--url", required=True); ap.add_argument("--token", required=True)
    ap.add_argument("--model", default=None, help="override model (e.g. small / medium / large-v3 on a GPU)")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(); logging.basicConfig(level=logging.INFO)
    w = Whisper(a.threads)
    while True:
        try:
            j = call(a.url, a.token, "/api/jobs/claim")["job"]
            if not j: time.sleep(0.5); continue
            pcm = np.frombuffer(base64.b64decode(j["pcm"]), "<i2")
            name = a.model or j["model"]
            t, lang, _ = w.run(to16k(pcm, j["rate"]), name, j["language"], j["hints"])
            call(a.url, a.token, "/api/jobs/result", {"id": j["id"], "text": t, "language": lang, "engine": "remote-" + name})
            logging.info("job %s [%s] %s", j["id"], lang, t)
        except Exception as e:
            logging.warning("worker error: %s", e); time.sleep(3)

if __name__ == "__main__":
    main()
