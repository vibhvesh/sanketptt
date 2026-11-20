"""Alert email over SMTP (keyword alerts or every message)."""
import os, smtplib
from email.message import EmailMessage
from .util import log


def send(cfg, meta, base, device_name):
    try:
        m = EmailMessage()
        m["From"] = cfg["smtp_user"] or "sanket-pi@localhost"; m["To"] = cfg["email_to"]
        kw = f" [ALERT: {', '.join(meta.get('keywords', []))}]" if meta.get("keywords") else ""
        m["Subject"] = f"Sanket PTT{kw}: {meta['channel']} - {meta['speaker']}"
        m.set_content(f"Channel: {meta['channel']}\nFrom: {meta['speaker']}\nTime: {meta['time']}\n"
                      f"Duration: {meta.get('duration_s', 0)} s\n\nTranscript:\n{meta.get('text') or '(none)'}\n\n-- {device_name}")
        if base and os.path.exists(base + ".wav"):
            m.add_attachment(open(base + ".wav", "rb").read(), maintype="audio", subtype="wav", filename=os.path.basename(base) + ".wav")
        with smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"]), timeout=20) as s:
            if cfg["smtp_tls"]:
                s.starttls()
            if cfg["smtp_user"]:
                s.login(cfg["smtp_user"], cfg["smtp_password"])
            s.send_message(m)
        log.info("email sent to %s", cfg["email_to"]); return "sent"
    except Exception as e:
        log.error("email failed: %s", e); return f"failed: {e}"


def wanted(cfg, meta):
    return cfg["email_enabled"] and cfg["email_to"] and (cfg["email_mode"] == "all" or meta.get("keywords"))
