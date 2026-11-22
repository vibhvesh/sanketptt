# Prisha Shopper — Market Rush

Prisha Shopper is a voice-shopping game in the Sanket website. Audio is captured with one hold-to-talk button, converted to mono 16 kHz WAV and submitted sequentially to the existing Sanket Transcribe endpoint at https://stlu-001.sanketptt.com/api/transcribe. Provider selection stays on the transcription server; no provider keys are exposed in the browser.

## Database/API still required
The Sanket website is static and cannot persist game history on its own. Set the optional `?api=https://YOUR-GAME-API` parameter after deploying a backend. Required endpoints: GET `/api/health`, POST `/api/games` to store a completed session and order transcripts, and GET `/api/games?player_name=...` to retrieve history.

Suggested PostgreSQL migration:

    CREATE TABLE sanket_game_sessions (id UUID PRIMARY KEY, player_name VARCHAR(32) NOT NULL, budget_paise BIGINT NOT NULL, total_paise BIGINT NOT NULL DEFAULT 0, won BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
    CREATE TABLE sanket_game_orders (id BIGSERIAL PRIMARY KEY, game_id UUID NOT NULL REFERENCES sanket_game_sessions(id) ON DELETE CASCADE, clip_id UUID NOT NULL, transcript TEXT NOT NULL DEFAULT '', product_id VARCHAR(32), quantity INTEGER, accepted BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
    CREATE INDEX sanket_game_player_history ON sanket_game_sessions (LOWER(player_name), created_at DESC);

The current transcribe endpoint accepts one WAV per request, so the client performs a sequential batch at checkout. Local Whisper fallback and any configured LLM provider must be selected server-side. The client does not run a local model. This MVP uses basic product/quantity parsing and needs server-side structured validation before competitive scoring.