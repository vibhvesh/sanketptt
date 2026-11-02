# Sanket Transcribe

Live transcription and translation of Sanket PTT radio channels, in the browser.

* Live: https://vibhvesh.github.io/sanketptt/transcribe/
* Android: [Sanket_Transcribe.apk](https://github.com/vibhvesh/sanketptt/releases/download/v1.0-android/Sanket_Transcribe.apk)
* Guide: [Sanket Transcribe User Guide (PDF)](../docs/Sanket_Transcribe_User_Guide.pdf) · https://vibhvesh.github.io/sanketptt/docs/

## What it does

* Joins one or more Sanket PTT channels over the same MQTT relay as the radio app (listen only).
* Plays each transmission and turns it into text with a speech-to-text API (ElevenLabs), with automatic language detection.
* Translates transcripts to and from English and Indian languages.
* Keyword alerts, searchable history and optional email of transcripts (Gmail, signed in with Google).

## Use

1. Open the link and enter the channel(s) to monitor (the same names used in Sanket PTT, e.g. `?ch=name`).
2. Add your speech-to-text API key in settings when asked (stored only in the browser).
3. Leave the page open; new messages appear with transcript and translation.

## Files

`index.html` – the whole app (static HTML/JS, no build step). Deployed by GitHub Pages with the rest of the repo.
