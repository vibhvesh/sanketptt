# Sanket Voice Command Centre — GitHub Pages Demo

Static browser-based receive-only console for the existing Sanket PTT MQTT-over-WebSocket relay.

## URL after deployment

- GitHub Pages project path: `/sanketptt/voice-centre/`
- If the repository's custom domain is active: `https://sanketptt.com/voice-centre/`

The page is included in the repository under `voice-centre/index.html`. It will be served automatically by the existing GitHub Pages site once the change is merged and the Pages deployment completes.

## Use

1. Open the page in desktop Google Chrome over HTTPS.
2. Enter the MQTT WebSocket endpoint (ws:// or preferably wss://), broker username/password if required, and the same Sanket topic prefix used by the existing PTT clients.
3. Check/edit the channel names and priority channels so they match the deployed relay.
4. Click **Enable speaker audio** once to satisfy the browser's audio autoplay policy.
5. Click **Connect**.
6. Select a channel, or start scanning.
7. Click **Enable voice commands** and grant microphone permission.

## Voice commands

- `Alpha Romeo, line two` — select channel 2.
- `Alpha Romeo, scan all lines` — start sequential scan.
- `Alpha Romeo, stop scanning` — stop scan.
- `Alpha Romeo, next line` / `previous line`.
- `Alpha Romeo, volume fifty`.
- `Alpha Romeo, mute` / `unmute`.

The current demo uses Chrome's Web Speech API (`SpeechRecognition`) with `en-IN`. Speech recognition availability and processing depend on Chrome and its configured speech service; this is not an offline recognizer. The wake phrase is filtered in the page after speech recognition returns a transcript, so the browser microphone remains active while voice commands are enabled.

## Relay protocol compatibility

The page subscribes to:
- `<prefix>/<channel>/floor` — JSON floor claim / heartbeat / release.
- `<prefix>/<channel>/audio` — one-byte sender-ID length, sender-ID bytes, then mono 12 kHz signed Int16 little-endian PCM.

This matches the packet structure in `pi/sanket/mqtt_relay.py`. The browser page does not publish floor claims or audio and cannot transmit.

## Emergency behaviour

A message on a configured priority channel pre-empts the selected channel and is played through the same speaker. On floor release, normal scanning can resume. Configure priority channel names to match actual deployed channels. This is a basic test policy, not a certified dispatch safety system.

## Important deployment requirements

- The broker must expose MQTT over WebSockets and permit connections from the GitHub Pages site origin. Use WSS for the HTTPS page.
- Configure authentication and broker ACLs so this console can subscribe only to the intended topics.
- Do not put broker passwords or private credentials in committed JavaScript/config files. Credentials are entered into the page at runtime and are not intentionally persisted.
- Avoid shared public demo broker credentials for operational traffic.
- Chrome must be allowed to use the microphone. Browser audio output must be unlocked by a user gesture.
- Test with a non-operational test channel and known audio samples before relying on the console.

## Current scope / limitations

- Desktop Chrome is the target; browser speech recognition support varies by browser and platform.
- One selected channel is played at a time through one browser audio output.
- Scan interval is configurable; scanner holds the selected line while its floor is active.
- This page has not been hardware-tested against a live Sanket broker, PC sound card, or microphone in this development session.
