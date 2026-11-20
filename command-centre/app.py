import json, queue, threading, time
from pathlib import Path
from urllib.parse import urlparse, unquote
import numpy as np
import sounddevice as sd
import paho.mqtt.client as mqtt
import tkinter as tk
from tkinter import ttk

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / "config.json").read_text()) if (BASE / "config.json").exists() else json.loads((BASE / "config.example.json").read_text())
PREFIX = CFG.get("prefix", "ptt-radio-66ab9178").strip("/")
RATE = 12000
LOCK = threading.RLock()
FLOOR = {}
AUDIO = queue.Queue(maxsize=100)
MIC = queue.Queue(maxsize=100)
STOP = threading.Event()
STATE = {"connected": False, "selected": CFG["channels"][0], "scan": False, "volume": float(CFG.get("volume", .8)), "speaker": "", "emergency": False, "last": "Ready", "error": ""}

def topic(ch, suffix):
    return PREFIX + "/" + ch + "/" + suffix

def select_line(ch):
    if ch not in CFG["channels"]:
        return
    with LOCK:
        STATE.update(selected=ch, emergency=False, speaker=FLOOR.get(ch, {}).get("name", ""))
        STATE["last"] = "Selected " + ch
    while not AUDIO.empty():
        try: AUDIO.get_nowait()
        except queue.Empty: break

def set_scan(enabled):
    with LOCK:
        STATE["scan"] = enabled
        STATE["last"] = "Scanning started" if enabled else "Scanning stopped"

def on_connect(client, userdata, flags, reason_code, properties=None):
    with LOCK: STATE["connected"] = int(reason_code) == 0
    for ch in CFG["channels"]:
        client.subscribe([(topic(ch, "floor"), 0), (topic(ch, "audio"), 0)])

def on_disconnect(client, userdata, flags, reason_code, properties=None):
    with LOCK: STATE["connected"] = False

def on_message(client, userdata, msg):
    try:
        _, ch, suffix = msg.topic.split("/", 2)
        if suffix == "floor":
            item = json.loads(msg.payload.decode("utf-8"))
            with LOCK:
                if item.get("t") in ("claim", "hb"):
                    FLOOR[ch] = {"id": item.get("id"), "name": item.get("name", "Unknown"), "seen": time.monotonic()}
                elif item.get("t") == "release" and FLOOR.get(ch, {}).get("id") == item.get("id"):
                    FLOOR.pop(ch, None)
            return
        if suffix != "audio" or not msg.payload:
            return
        size = msg.payload[0]
        sender = msg.payload[1:1+size].decode("latin-1")
        end = len(msg.payload) - ((len(msg.payload) - 1 - size) % 2)
        pcm = np.frombuffer(msg.payload[1+size:end], dtype="<i2")
        if not len(pcm):
            return
        with LOCK:
            floor = FLOOR.get(ch)
            if not floor or floor["id"] != sender:
                return
            floor["seen"] = time.monotonic()
            if ch in CFG.get("emergency_channels", []):
                STATE.update(selected=ch, emergency=True, speaker=floor["name"])
                play = True
            else:
                play = ch == STATE["selected"] and not STATE["emergency"]
                if play:
                    STATE["speaker"] = floor["name"]
        if play:
            try:
                AUDIO.put_nowait(pcm.copy())
            except queue.Full:
                try:
                    AUDIO.get_nowait()
                    AUDIO.put_nowait(pcm.copy())
                except queue.Empty:
                    pass
    except Exception as exc:
        with LOCK: STATE["error"] = str(exc)

def output_callback(outdata, frames, timing, status):
    outdata.fill(0)
    try:
        pcm = AUDIO.get_nowait()
        count = min(frames, len(pcm))
        outdata[:count, 0] = (pcm[:count].astype(np.float32) * STATE["volume"]).astype(np.int16)
    except queue.Empty:
        pass

def command(text):
    words = text.lower().replace(",", " ").split()
    wake = CFG.get("wake_phrase", "alpha romeo").lower().split()
    try:
        pos = next(i for i in range(len(words)) if words[i:i+len(wake)] == wake)
    except StopIteration:
        return
    args = words[pos+len(wake):]
    if not args:
        return
    if "scan" in args or "scanning" in args or "rotate" in args:
        if "stop" in args:
            set_scan(False)
        else:
            set_scan(True)
        return
    if "next" in args or "previous" in args:
        index = CFG["channels"].index(STATE["selected"])
        index = (index + (1 if "next" in args else -1)) % len(CFG["channels"])
        select_line(CFG["channels"][index])
        return
    if "mute" in args:
        STATE["volume"] = 0
        STATE["last"] = "Speaker muted"
        return
    if "unmute" in args:
        STATE["volume"] = float(CFG.get("volume", .8))
        STATE["last"] = "Speaker unmuted"
        return
    number_words = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}
    if "line" in args:
        idx = args.index("line") + 1
        if idx < len(args):
            n = number_words.get(args[idx])
            if n is None and args[idx].isdigit(): n = int(args[idx])
            if n and 1 <= n <= len(CFG["channels"]):
                set_scan(False)
                select_line(CFG["channels"][n-1])
                return
    if "volume" in args:
        idx = args.index("volume") + 1
        if idx < len(args):
            n = number_words.get(args[idx])
            if n is None and args[idx].isdigit(): n = int(args[idx])
            if n is not None:
                STATE["volume"] = max(0, min(100, n)) / 100
                STATE["last"] = "Volume set to " + str(n) + " percent"

def voice_worker():
    from vosk import Model, KaldiRecognizer
    model_path = BASE / CFG.get("vosk_model_path", "models/vosk-model-small-en-us-0.15")
    if not model_path.exists():
        STATE["error"] = "Vosk model missing: " + str(model_path)
        return
    model = Model(str(model_path))
    phrases = ["alpha romeo line " + w for w in ["one","two","three","four","five","six","seven","eight","nine","ten"]]
    phrases += ["alpha romeo scan all lines","alpha romeo start scanning","alpha romeo stop scanning","alpha romeo next line","alpha romeo previous line","alpha romeo mute","alpha romeo unmute","alpha romeo volume fifty","alpha romeo volume twenty five","alpha romeo volume one hundred"]
    recognizer = KaldiRecognizer(model, 16000, json.dumps(phrases))
    def mic_callback(indata, frames, timing, status):
        try: MIC.put_nowait(bytes(indata))
        except queue.Full: pass
    try:
        with sd.RawInputStream(samplerate=16000, blocksize=8000, channels=1, dtype="int16", callback=mic_callback, device=CFG.get("audio_input_device")):
            while not STOP.is_set():
                try: data = MIC.get(timeout=.5)
                except queue.Empty: continue
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result()).get("text", "")
                    if result: command(result)
    except Exception as exc:
        STATE["error"] = "Voice listener: " + str(exc)

def scanner_worker():
    dwell = time.monotonic()
    while not STOP.is_set():
        time.sleep(.1)
        if not STATE["scan"] or STATE["emergency"]:
            dwell = time.monotonic()
            continue
        current = FLOOR.get(STATE["selected"])
        if current and time.monotonic() - current["seen"] < 2.8:
            dwell = time.monotonic()
            continue
        if time.monotonic() - dwell >= float(CFG.get("scan_interval_seconds", 5)):
            index = (CFG["channels"].index(STATE["selected"]) + 1) % len(CFG["channels"])
            select_line(CFG["channels"][index])
            dwell = time.monotonic()

class Console:
    def __init__(self, root):
        self.root = root
        root.title("Sanket Voice Command Centre")
        root.geometry("760x650")
        root.configure(bg="#0b1724")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#0b1724", foreground="#eaf2f8", font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=8)
        ttk.Label(root, text="SANKET VOICE COMMAND CENTRE", font=("Segoe UI", 20, "bold")).pack(pady=16)
        self.status = ttk.Label(root, text="Connecting to Sanket relay…")
        self.status.pack(pady=6)
        self.active = ttk.Label(root, text="—", font=("Segoe UI", 32, "bold"), foreground="#70efb0")
        self.active.pack(pady=8)
        frame = ttk.Frame(root)
        frame.pack(pady=12)
        for i, ch in enumerate(CFG["channels"]):
            ttk.Button(frame, text=str(i+1)+". "+ch, command=lambda c=ch: select_line(c)).grid(row=i//2, column=i%2, padx=6, pady=6, sticky="ew")
        controls = ttk.Frame(root)
        controls.pack(pady=14)
        ttk.Button(controls, text="START SCAN", command=lambda: set_scan(True)).grid(row=0,column=0,padx=6)
        ttk.Button(controls, text="STOP SCAN", command=lambda: set_scan(False)).grid(row=0,column=1,padx=6)
        ttk.Label(root, text="Speaker volume").pack()
        self.vol = tk.Scale(root, from_=0, to=100, orient="horizontal", command=self.set_volume, length=340, bg="#0b1724", fg="white", highlightthickness=0)
        self.vol.set(int(STATE["volume"]*100))
        self.vol.pack()
        self.last = ttk.Label(root, text="Voice: say 'Alpha Romeo, line two' or 'Alpha Romeo, scan all lines'")
        self.last.pack(pady=12)
        self.error = ttk.Label(root, text="", foreground="#ffb2a8")
        self.error.pack(pady=4)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()
    def set_volume(self, value):
        STATE["volume"] = int(float(value))/100
    def refresh(self):
        self.status.config(text=("● RELAY CONNECTED" if STATE["connected"] else "○ RELAY DISCONNECTED") + ("  |  SCANNING" if STATE["scan"] else "  |  MANUAL"))
        self.active.config(text=STATE["selected"].upper())
        self.last.config(text="Last command: "+STATE["last"]+" | Speaker: "+(STATE["speaker"] or "idle"))
        self.error.config(text=STATE["error"])
        self.root.after(500, self.refresh)
    def close(self):
        STOP.set()
        self.root.destroy()

def main():
    output = sd.OutputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=1200, callback=output_callback, device=CFG.get("audio_output_device"))
    output.start()
    u = urlparse(CFG["broker_url"])
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sanket-command-centre", transport="websockets" if u.scheme in ("ws","wss") else "tcp")
    if u.scheme in ("ws","wss"): client.ws_set_options(path=u.path or "/")
    if u.scheme in ("wss","mqtts"): client.tls_set()
    if u.username: client.username_pw_set(unquote(u.username), unquote(u.password or ""))
    client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message
    client.reconnect_delay_set(1,30)
    client.connect_async(u.hostname, u.port or {"wss":443,"ws":80,"mqtts":8883}.get(u.scheme,1883), keepalive=30)
    client.loop_start()
    threading.Thread(target=voice_worker, daemon=True).start()
    threading.Thread(target=scanner_worker, daemon=True).start()
    root = tk.Tk()
    Console(root)
    root.mainloop()
    client.loop_stop()
    client.disconnect()
    output.stop()
    output.close()

if __name__ == "__main__":
    main()
