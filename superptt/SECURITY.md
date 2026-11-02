# SuperPTT security notes

This file describes what SuperPTT protects, what it does not, and the gaps that remain before any Indian
government certification. **SuperPTT is not certified by TEC, STQC or any other body, and this document does not claim it is.**

## Threat model
| Adversary | Protected? |
|---|---|
| Public MQTT broker operator (shiftr.io, EMQX, HiveMQ, Mosquitto test) reading or recording traffic | Yes, on **encrypted channels**: audio, floor, presence and SSTV payloads are AES-256-GCM ciphertext. |
| Anyone on the internet who guesses or sees the topic prefix | Yes on encrypted channels: they can't decrypt, and injected, tampered or replayed packets are dropped. |
| Network observer (Wi-Fi, ISP) | TLS (WSS) to the broker, plus E2E on encrypted channels. |
| Someone who holds the invite link / QR, or an unlocked phone | **No.** Whoever has the key is a member. Rotate the key if a phone is lost. |
| Compromised control-room Pi | **No.** The Pi holds all channel secrets and stores decrypted recordings and transcripts. |
| Cloud STT provider (if enabled) | **No.** Audio sent for cloud transcription leaves the Pi decrypted. Keep cloud STT off for sensitive channels. |
| Denial of service (broker down, flooding, jamming the floor) | **No.** |

## Encryption (opt-in per channel)
- A channel without a key works exactly like before and shows **⚠ not encrypted**. Legacy Sanket PTT channels stay plaintext and interoperate.
- Channel secret: 32 random bytes, created by the control room (`data/keys.json`, mode 600). Per-channel keys come from HKDF-SHA256
  (salt `superptt-e2e-v1`, info `aes|<channel>`; the topic key uses `topic|<channel>`).
- Packet: `E5 01 kid n id seq(u32) ts(u64 ms) nonce(12) ciphertext+tag(16)`. The nonce is random for each packet. The AAD is the header (sender id, seq, ts, key id)
  plus `superptt|<channel>|<kind>`, so a packet can't be moved to another channel or message type.
- Replay: packets older or newer than ±30 s are dropped (so phone clocks must be right), and so are repeats of a sequence number (64-packet window per sender).
- Plaintext packets on an encrypted channel are dropped. The sender id inside the payload must match the authenticated header.
- Optional hidden topic: `h` + HMAC-SHA256(topic key, channel)[:12 bytes], so the broker never sees the channel name.
- Implementations: browser WebCrypto (`app/superptt.js`), Python `cryptography`/OpenSSL (`control-room/superptt/e2e.py`). There is a cross-implementation test.

## Key distribution
Keys are never sent through the broker, and `/api/directory` never returns keys. The admin creates or rotates a key in Console → Channel encryption,
then clicks **Invite / QR**. The secret sits only in the URL **fragment** (`…/superptt/#k=<ch>.<kid>.<secret>[.h]`), which browsers never send
to a server. The app stores the key in `localStorage` and removes the fragment from the address bar. Treat the link like a password and share it in person or over a private channel.
**Rotation** issues a new key id. Phones still on the old key show "key mismatch" until they scan the new invite.
Every key add, rotation, removal and invite is written to the **Security log** (without the secret), along with logins, failed logins,
PIN and token changes, broker changes, cut-ins, retention and cloud-STT changes.

## What is NOT protected / known gaps
- Metadata: the broker still sees the sender's random per-session id (in the presence topic), packet timing and size. It sees channel names unless the topic is hidden.
  A plaintext empty "leave" message is still sent.
- No forward secrecy and no per-user keys: everyone on a channel shares one key, and a leaked key decrypts recorded traffic from that key's lifetime.
- There is no sender signature beyond channel-key membership: any member can impersonate another member's name.
- Keys and the private-broker password are stored in the phone's browser storage, with no hardware keystore.
- Recordings and transcripts on the Pi are stored unencrypted on the SD card. Use full-disk encryption and physical security.
- The public brokers are third-party services outside India.

## Private broker (`install.sh --private-broker`)
This installs Mosquitto on the Pi with anonymous access turned off, a separate generated password for each user (`/etc/mosquitto/superptt-credentials.txt`, root only),
and an ACL limited to the SuperPTT topic tree. Mosquitto listens on 127.0.0.1:9001 (WebSockets). TLS comes from Cloudflare (wss://), and Cloudflare
can see the traffic at its edge. That is why E2E is still recommended. An optional LAN `wss://:8884` listener is available with your own certificate. Today all users share the topic tree, so the ACL does not stop one unit from reaching another unit's channels.

## Gaps before Indian government certification (not exhaustive, no claim made)
- **No TEC / STQC evaluation** has been done (for example TEC MTCTE, STQC application security / CC testing, CERT-In empanelled audit).
- **Crypto modules are not FIPS 140-validated** (browser WebCrypto and stock OpenSSL builds), and they are not evaluated against Indian (SETS / NCIIPC) guidance.
- **Hosting:** public brokers and Cloudflare are outside India. Use the private broker on a Pi on Indian soil, with a tunnel or hosting in an Indian region
  (data-localisation and MeitY empanelled-cloud requirements still need review).
- There is no formal key-management lifecycle (HSM, escrow, audit of key custody), no independent penetration test, no SBOM or vulnerability-management process,
  and the audit log is local only and not tamper-evident.
