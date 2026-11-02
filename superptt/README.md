# SuperPTT web app (static, GitHub-Pages-ready)

Multi-channel push-to-talk in the browser / as an installable PWA / inside the existing Android WebView wrapper.
It uses the **same public brokers and topics as Sanket PTT** (`ptt-radio-66ab9178/<channel>/…`), so SuperPTT and existing Sanket PTT users talk to each other.

## Features
- **Connect to a control room**: ⚙ → admin URL + directory token loads all channels and their priorities (`GET /api/directory?t=`).
  Fallback: a manual channel list and/or "discover active channels" (broker presence).
  Deep link: `…/index.html?admin=https://ptt.example.com&t=<token>&name=Unit7`.
- **Listen to many channels at once**, each with mute and volume. The mixer gives every (channel, sender) its own jitter buffer, so two people talking at once are **mixed, never interleaved or garbled**. Lower-priority channels are **ducked −12 dB** while a higher-priority (or your current TX) channel is active.
- **One-tap TX switch**: tap a channel row (or keys 1–9). **ALL-CALL**: check channels, tick ALL-CALL, hold PTT. It claims the floor on each one; busy channels are skipped and reported.
- **Floor control** uses the Sanket protocol (claim/hb/release, earliest timestamp wins). The claim window adapts to broker latency (it waits for its own claim to echo back), so simultaneous presses resolve to exactly one talker. **Priority cut-in** (`prio` field) from the control room preempts compliant SuperPTT clients. Legacy clients also switch to the control room, because cut-in uses the earliest possible timestamp.
- **Who's talking**: live talker names per channel, with an overlap marker and a CUT-IN badge.
- **PWA**: `manifest.json`, `sw.js` (offline shell, network-first), icons. On Android Chrome: menu → Install app. iOS: Share → Add to Home Screen.
- **Android wrapper**: load the hosted URL in the existing WebView app (same as `sanketptt/android`); grant mic permission. Hardware PTT keys can call `window.SuperPTTHardware.down()` / `.up()` via `evaluateJavascript`.

## Try it locally
    cd app && python3 -m http.server 8080    # open http://localhost:8080 (mic works on localhost/https only)
Open two browser windows with different names and the same manual channels (e.g. `test1, test2`) to talk to each other.
Use a private test channel name, not a real channel. To use the control room: open its console → Access → Show tokens → copy the directory token.

## Tests (live public broker, isolated random topic prefix)
    npm i && node test/e2e.js superptt-selftest-<rand>/ http://127.0.0.1:8099 <cookie-file>
Runs 3 SuperPTT clients plus 1 legacy Sanket PTT client plus the control room (multi-listen, switch, all-call, overlap, race, cut-in, talk-back).

## Files
`superptt.js` protocol core + mixer (browser & Node) · `app.js` UI/audio · `index.html` · `sw.js` · `manifest.json` · icons.

## Encryption (opt-in per channel)
Channels without a key behave exactly as before (marked ⚠ not encrypted). The control-room admin adds a key under Console → Channel encryption.
**Invite / QR** shows a QR code and a link `https://vibhvesh.github.io/sanketptt/superptt/#k=…`. Scan it or open it on the phone, then Connect. The channel shows 🔒 E2E.
Custom/private broker: Setup → Broker (URL, username, password). Details: `../SECURITY.md`. Offline crypto test: `node test/crypto.js`.
