# Prisha Shopper — Market Rush

Prisha Shopper is a voice-shopping game in the Sanket website. Audio is captured with one hold-to-talk button, converted to mono 16 kHz WAV and submitted sequentially to the existing Sanket Transcribe endpoint at https://stlu-001.sanketptt.com/api/transcribe. Provider selection stays on the transcription server; no provider keys are exposed in the browser.

## Session-only game history

Completed games are stored in the browser's `sessionStorage`, scoped to the current tab session. The My History screen shows games played by the current player during that session. History is not sent to a game database or history API, and is cleared when the tab's session ends. No database, migration, or game-history backend is required.

The current transcription endpoint accepts one WAV per request, so the client performs a sequential batch at checkout. Local Whisper fallback and any configured LLM provider must be selected server-side. The client does not run a local model. This MVP uses basic product/quantity parsing and needs server-side structured validation before competitive scoring.
