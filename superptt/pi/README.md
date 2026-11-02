# SuperPTT Control Room (Raspberry Pi)

Receives **every** Sanket PTT channel (same MQTT topics `ptt-radio-66ab9178/<ch>/…`), records each
transmission per channel *and per speaker*, transcribes locally with faster-whisper (int8), and plays
one / selected / all channels mixed out of the Pi speaker with priority ducking. See `../DESIGN.md`.

## Install (Pi 4/5, Raspberry Pi OS 64-bit)
    git clone … && cd superptt/control-room && ./install.sh
Open `http://<pi>.local:8090`; on first open you must set an admin PIN (6+ digits). You get a LAN worker token once; keep it.

## Run without install (dev)
    python3 -m venv v && v/bin/pip install -r requirements.txt && v/bin/python -m superptt -c config.json

## Key settings (`config.json`)
- `listen_all` (auto-join every channel seen), `channels`, `priority` `{"control":5}`
- Multilingual only: `quality_model` small (when idle) → `whisper_model` base → `fallback_model` tiny (queue > `overload_queue`)
- `language` null = auto per utterance; `language_hints` `{"channel":["gu","hi","en"]}`
- `local_stt`, `remote_workers`; LAN worker: `python worker.py --url http://<pi>:8090 --token <token> --model small` (GPU: `large-v3` for Gujarati)
- `cloud`: local first, cloud as fallback. Set `provider` (elevenlabs | openai | google) and the `api_key` in the console (Cloud box → Save; the key stays hidden).
  It is sent to the cloud when the language is in `cloud.langs` (Gujarati etc.), the channel's expected language is, the script is wrong, confidence is low (`min_avg_logprob`, `min_lang_prob`, `max_no_speech`), or queue > `when_queue_over`.
  With no key or a cloud error the local text is kept and retried every `retry_s`. The console shows ⌂ LOCAL / ☁ CLOUD per message.
- `out_rate` 48000 (12 kHz audio resampled for the sound card)
- `stt_engine`: `faster-whisper` | `vosk` (set `vosk_model_path`, `pip install vosk`) | `none`
- `language`: null (auto) / `hi` / `en`
- `output`: `mode` all|select|single, `channels`, `volume`, `duck_db`, `device`

## API
`GET /api/directory` (for SuperPTT clients) · `GET /api/status` · `GET /api/timeline?since=&channels=a,b` ·
`GET /rec/<path>.wav` · `POST /api/login {pin}` · `POST /api/output` · `POST /api/cloud {provider,api_key,model,url,langs}` · `POST /api/config` (X-Token header).

Data: `data/rec/YYYY-MM-DD/<channel>/*.wav`, `data/superptt.db`. Failed/backlogged transcriptions stay `pending` and are retried on restart.
Gujarati: small Pi models are not usable, so it is routed to cloud automatically once a key is set. Not yet: control-room TX, own broker/ACL, server floor arbiter, SuperPTT multi-group client (phases P1–P2).

## Cloud API key via environment (recommended on the Pi)
If `cloud.api_key` in config is empty, the key is read from the environment by provider:
`ELEVENLABS_API_KEY`, `OPENAI_API_KEY` or `GOOGLE_API_KEY`. The installer creates `/etc/superptt.env` (mode 600) loaded by systemd:

    sudo nano /etc/superptt.env        # ELEVENLABS_API_KEY=sk_...
    sudo systemctl restart superptt

The console shows "key set ✓ (env)". The key is never shown or logged.

## Outside access (Cloudflare Tunnel)
The broker stays public (shiftr). The console is reached from outside through Cloudflare Tunnel, with no port forwarding.
- **Quick tunnel (default):** `./install.sh` installs `cloudflared` (arm64 .deb) and the `superptt-tunnel` service. The random `https://<words>.trycloudflare.com` URL is shown in the console header and logged (`journalctl -u superptt | grep "public console"`). It **changes on every restart** and Cloudflare offers no uptime guarantee, so use it for testing.
- **Named tunnel (your domain, stable):** in Cloudflare Zero Trust → Networks → Tunnels → Create tunnel (cloudflared), copy the token, add a Public Hostname `ptt.example.com` → `http://localhost:8090`. Then:
  `SUPERPTT_TUNNEL=named CF_TUNNEL_TOKEN=<token> PUBLIC_URL=https://ptt.example.com ./install.sh`
  (token stored in `/etc/superptt-tunnel.env`, mode 600). Optional: add Cloudflare Access (email OTP) in front for a second factor.
- `SUPERPTT_TUNNEL=none` for LAN only.

## Security model (internet-exposed)
- Unauthenticated: only `/` (console shell), `GET /api/session`, `POST /api/login`, and `POST /api/setup`, which only works on first run **from the LAN** (refused via the tunnel).
- PIN stored as a PBKDF2 hash. Login lockout: 5 failures in 15 min per IP → 15 min lock, doubling on repeats; 30 failures globally → 5 min lock for everyone. Real client IP comes from `Cf-Connecting-Ip` only when the request arrives from local cloudflared.
- Session cookie `HttpOnly; SameSite=Strict`, plus `Secure` via the tunnel, 12 h; POSTs also need `X-Requested-With: superptt` (CSRF). Logout and PIN change (`/api/pin`) invalidate sessions.
- Via tunnel: HTTP→HTTPS redirect and HSTS; CSP, X-Frame-Options DENY, no-store.
- LAN workers (`/api/jobs/*`) work **LAN-only** with the worker token, refused via the tunnel even with a valid token.
- `/api/directory` (for SuperPTT clients) needs a login session **or** the read-only `directory_token` (`?t=` or `X-Directory-Token`), shown at setup and under Access → Show tokens. It exposes only broker URL, prefix and channel list.

## Retention
Default: audio **30 days**, transcripts **30 days** (editable in console → Storage & retention, or `retention` in config). Cleanup runs daily. A disk guard runs every 5 min: if free space < `min_free_pct` (10%) it deletes the **oldest recordings first** and keeps their transcripts. The console shows disk free/total, recordings size, message count and last cleanup.

## Talk-back (control room → radios)
Console → Talk-back: choose "Checked channels" or "ALL channels", optionally **Priority cut-in**, then hold the button (or Space).
The browser mic needs a secure origin: use the tunnel HTTPS URL or `http://localhost:8090` on the Pi. Plain `http://<pi>.local` blocks the mic.
API: `POST /api/tx/start {channels:[..]|"all", cutin}` → `{ok,busy}`, `POST /api/tx/audio` (raw Int16LE 12 kHz), `POST /api/tx/stop`. It auto-stops after 3 s without audio.
Cut-in uses `prio 9` + earliest timestamp: SuperPTT clients stop transmitting and show "cut in"; legacy Sanket clients switch their floor to the control room.
`/api/directory` sends CORS `*` (token-only, no cookies), so the GitHub-Pages app can load channels.

## Encryption, private broker, security log
- Console → **Channel encryption**: add / rotate / remove AES-256-GCM keys per channel, then **Invite / QR** for phones. Keys live in `data/keys.json` (600) and are never sent via the broker.
- `install.sh --private-broker` (or `curl … | bash -s -- --private-broker`, `BROKER_USERS="unit1 unit2"`) installs Mosquitto with logins + ACL behind Cloudflare. Console → **Broker** to change it.
- Console → **Security log**: admin actions and key changes. See `../SECURITY.md`.
