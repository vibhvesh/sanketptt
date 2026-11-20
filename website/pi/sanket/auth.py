"""Settings PIN + login sessions. Reads stay open (dashboard/kiosk); writes need the PIN when one is set.
Clients can send the PIN (X-Pin header, v2 compatible) or log in once and use the session token."""
import hmac, secrets, time

SESSION_S = 12 * 3600


class Auth:
    def __init__(self, cfg):
        self.cfg, self.sessions = cfg, {}

    def required(self):
        return bool(self.cfg["web_pin"])

    def check_pin(self, pin):
        p = self.cfg["web_pin"]
        return not p or hmac.compare_digest(str(pin or ""), str(p))

    def login(self, pin):
        if not self.check_pin(pin):
            time.sleep(0.5); return None
        tok = secrets.token_urlsafe(24); self.sessions[tok] = time.time() + SESSION_S
        return tok

    def logout(self, tok):
        self.sessions.pop(tok, None)

    def ok(self, headers):
        if not self.required():
            return True
        if self.check_pin(headers.get("X-Pin", "")) and headers.get("X-Pin"):
            return True
        tok = headers.get("X-Token", "")
        if not tok:
            for part in (headers.get("Cookie") or "").split(";"):
                k, _, v = part.strip().partition("=")
                if k == "sanket_token":
                    tok = v
        exp = self.sessions.get(tok)
        return bool(exp and exp > time.time())
