"""Cloud STT providers (fallback only). openai-compatible | elevenlabs | google."""
import base64, io, json, urllib.request, uuid, wave
ISO3 = {"eng": "en", "hin": "hi", "guj": "gu", "mar": "mr", "ben": "bn", "tam": "ta", "tel": "te", "urd": "ur",
        "pan": "pa", "kan": "kn", "mal": "ml", "ori": "or", "asm": "as", "nep": "ne", "ara": "ar", "fra": "fr",
        "spa": "es", "deu": "de", "rus": "ru", "zho": "zh", "cmn": "zh", "jpn": "ja", "por": "pt", "ron": "ro", "pol": "pl", "kan": "kn", "nld": "nl", "ita": "it", "tur": "tr"}
GOOGLE_LOC = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN", "mr": "mr-IN", "bn": "bn-IN", "ta": "ta-IN", "te": "te-IN",
              "kn": "kn-IN", "ml": "ml-IN", "pa": "pa-Guru-IN", "ur": "ur-IN", "or": "or-IN"}

import os
ENV_KEYS = {"elevenlabs": "ELEVENLABS_API_KEY", "openai": "OPENAI_API_KEY", "google": "GOOGLE_API_KEY"}
def api_key(c):
    """config key wins; otherwise env var for the provider (systemd EnvironmentFile on the Pi)."""
    return c.get("api_key") or os.environ.get(ENV_KEYS.get(c.get("provider"), ""), "")

def wav_bytes(pcm, rate):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm.tobytes())
    return b.getvalue()

def _multipart(fields, wav):
    bd = uuid.uuid4().hex; out = b""
    for k, v in fields.items():
        if v is None: continue
        out += f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    out += (f'--{bd}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\n'
            f'Content-Type: audio/wav\r\n\r\n').encode() + wav + f"\r\n--{bd}--\r\n".encode()
    return out, "multipart/form-data; boundary=" + bd

def _post(url, body, headers, timeout):
    r = urllib.request.Request(url, body, headers)
    return json.loads(urllib.request.urlopen(r, timeout=timeout).read())

def transcribe(c, pcm, rate, lang=None, hints=None):
    """Returns (text, lang). Raises on failure. c = cfg['cloud']."""
    p, key, t = c["provider"], api_key(c), int(c.get("timeout", 45))
    if not key: raise RuntimeError("no cloud API key")
    wav = wav_bytes(pcm, rate)
    if p == "openai":
        model = c.get("model") or "whisper-1"
        f = {"model": model, "language": lang,
             "response_format": "verbose_json" if model == "whisper-1" else "json"}
        body, ct = _multipart(f, wav)
        j = _post(c.get("url") or "https://api.openai.com/v1/audio/transcriptions", body,
                  {"Authorization": "Bearer " + key, "Content-Type": ct}, t)
        l = j.get("language"); l = {"gujarati": "gu", "hindi": "hi", "english": "en"}.get(str(l).lower(), l)
        return j.get("text", "").strip(), l or lang
    if p == "elevenlabs":
        body, ct = _multipart({"model_id": c.get("model") or "scribe_v1", "language_code": lang}, wav)
        j = _post(c.get("url") or "https://api.elevenlabs.io/v1/speech-to-text", body,
                  {"xi-api-key": key, "Content-Type": ct}, t)
        l = j.get("language_code"); return j.get("text", "").strip(), ISO3.get(l, l) or lang
    if p == "google":
        langs = [x for x in ([lang] if lang else []) + list(hints or []) if x]
        locs = [GOOGLE_LOC.get(x, x) for x in dict.fromkeys(langs)] or ["en-IN"]
        cfg = {"encoding": "LINEAR16", "sampleRateHertz": rate, "languageCode": locs[0],
               "enableAutomaticPunctuation": True}
        if len(locs) > 1: cfg["alternativeLanguageCodes"] = locs[1:4]
        body = json.dumps({"config": cfg, "audio": {"content": base64.b64encode(pcm.tobytes()).decode()}}).encode()
        j = _post((c.get("url") or "https://speech.googleapis.com/v1p1beta1/speech:recognize") + "?key=" + key, body,
                  {"Content-Type": "application/json"}, t)
        res = j.get("results") or []
        text = " ".join(r["alternatives"][0].get("transcript", "") for r in res if r.get("alternatives")).strip()
        l = (res[0].get("languageCode") if res else None) or locs[0]
        return text, l.split("-")[0].lower()
    raise RuntimeError("unknown provider " + p)
