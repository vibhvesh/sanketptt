# Sanket AI Database Copilot

FastAPI backend for natural-language PostgreSQL exploration. It introspects PostgreSQL tables, columns and foreign keys; asks an OpenAI model to generate SQL; validates and executes only read-only statements; and returns tabular results plus chart suggestions.

## Temporary database (no account)
On the Ubuntu VPS (Node.js 20.12+ and npm required):

```bash
npx create-db@latest --json
```

Copy the printed `connectionString` into `DATABASE_URL` in this service's private `.env`. The database expires after 24 hours unless claimed with the supplied `claimUrl`. Do not commit either URL or credentials. Choose region ap-southeast-1 if creating interactively and nearest region is desired.

## Configure and start
1. Copy `.env.example` to `.env`.
2. Set `DATABASE_URL` to the temporary database connection string.
3. Set `OPENAI_API_KEY` to a server-side API key. Never put it in GitHub Pages/browser JavaScript.
4. Set `ALLOWED_ORIGINS` to the exact public frontend origins.
5. Run:

```bash
docker compose up -d --build
curl http://127.0.0.1:8091/health
```

Expose it through the existing HTTPS reverse proxy at `https://<your-api-host>/` and preserve the /api paths. Do not expose port 8091 publicly; use HTTPS and proxy to 127.0.0.1:8091.

## API
- GET /health
- GET /api/schema
- GET /api/suggestions
- POST /api/chat { "message": "...", "history": [] }
- POST /api/query { "sql": "SELECT ..." }

Every SQL execution uses a PostgreSQL read-only transaction, 8-second statement timeout, one statement only, and a 500-row response cap. The SQL validator blocks common write/DDL commands and dangerous server functions. Use a dedicated database role with SELECT-only privileges for production-grade isolation; this temporary scratch database is disposable.

## Security notes
The temporary Prisma database is public internet reachable by connection credentials. Keep the connection string only in the VPS environment. Rotate/delete the temporary database if the credentials are exposed. The free unclaimed database expires after 24 hours. OpenAI API usage is billed separately according to the account's API plan.
