# SuperPTT Transcribe (web / PWA)

Listen-only web version of Sanket edge transcribe: https://vibhvesh.github.io/sanketptt/superptt/transcribe/

- Joins the same MQTT brokers / prefix / channels as the SuperPTT app (`../superptt.js` is reused, including AES-256-GCM/HKDF E2E).
- Keys: open the control-room invite link with `/transcribe/` in the path, or paste it in ⚙. Keys already imported in the SuperPTT app on the same origin are reused.
- Transcripts: if a control-room URL + PIN is set, transcripts and audio come from the Pi (`/api/timeline`, `/rec/`) with a Bearer token
  (Pi must allow the origin in `cors_origins`, default `https://vibhvesh.github.io`). Otherwise the browser transcribes with local Whisper
  (transformers.js, whisper-tiny ~40 MB / base ~80 MB, cached after the first load) or ElevenLabs Scribe with a key kept only in localStorage.
- Search, language label, export CSV/TXT.
