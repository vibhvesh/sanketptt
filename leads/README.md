# Sanket lead finder

Internal sales search for Sanket PTT. The page is `https://sanketptt.com/leads/` (direct URL only). It is not in the site menu and it sends `noindex`.

The marketing site is static. This folder is the API that the page calls. Searches use only public sources:

- OpenStreetMap Nominatim for geocoding (one request at a time, identified User-Agent)
- OpenStreetMap Overpass and Photon for tagged places
- DuckDuckGo's HTML search, with Bing HTML as a fallback
- The company's own pages, when `robots.txt` allows the fetch

A phone, email, address or person's name is stored only when it was found. Empty means "not found".

## How the live site is hosted

`https://sanketptt.com` is static HTML. Two workflows publish it:

| Workflow | What it publishes | When |
|---|---|---|
| `.github/workflows/deploy-hostinger.yml` | `website/` (and `aakashvani/`) to the Hostinger VPS over SSH | Push to `main` that changes those paths, or a manual run |
| `.github/workflows/deploy.yml` | The repository to GitHub Pages | Push to `main` |

The Hostinger job is what serves the custom domain. It needs the existing repository secrets `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `DEPLOY_PATH`, and optional `SSH_PORT`. This lead finder does not change that job.

What is **not** deployed by either workflow:

- This Python API. Hostinger only receives files. GitHub Pages only receives files. Nothing there runs the search.

The API is already running on Render at https://sanket-leads.onrender.com. `website/leads/config.js` points the page at that origin. Merging this branch to `main` publishes the page to `https://sanketptt.com/leads/` on the next Hostinger deploy.

## Run it locally

```bash
cd leads
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export LEADS_TOKEN=local-dev-token
export LEADS_DB_PATH=./data/leads.sqlite
uvicorn sanket_leads.api:app --host 0.0.0.0 --port 8765
```

Open http://127.0.0.1:8765/leads/ and use the token above. The page is prefilled with the Render API. Clear **Lead service address** before opening the desk if you want it to call this local server instead.

Tests (no network):

```bash
cd leads && python -m pytest
```

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `LEADS_TOKEN` | Yes | Shared password. If it is empty the API refuses every search. |
| `LEADS_DB_PATH` | No | SQLite file. Default `./data/leads.sqlite`. |
| `LEADS_CORS_ORIGINS` | No | Browser origins allowed to call the API. Include `https://sanketptt.com`. |
| `NOMINATIM_USER_AGENT` | No | Identifies this app to OpenStreetMap. Keep a contact URL in it. |
| `NOMINATIM_MIN_INTERVAL` | No | Seconds between Nominatim calls. Default `1.1`. |
| `OVERPASS_TIMEOUT` | No | Seconds before a hung Overpass mirror is skipped. Default `8`. |

Generate a password with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

Do not commit the real token.

## Deploy the API on Render

The service is deployed as **sanket-leads** at https://sanket-leads.onrender.com. Its root is the repository root (Render root directory is empty). `render.yaml` matches that service:

| Setting | Value |
|---|---|
| Build | `pip install -r leads/requirements.txt` |
| Start | `cd leads && uvicorn sanket_leads.api:app --host 0.0.0.0 --port $PORT` |
| Health check | `/api/health` |

`LEADS_TOKEN` is set in the Render environment and is not in the repo. `LEADS_CORS_ORIGINS` should include `https://sanketptt.com` and `https://www.sanketptt.com` so the Hostinger page can call the API.

The free plan's disk is wiped on restart and after the service spins down (about 15 minutes idle). Searches then start again from an empty database. To keep SQLite, move the service to a plan with a persistent disk and set `LEADS_DB_PATH` to that mount, for example `/var/data/leads.sqlite`.

The page at `website/leads/config.js` already uses `https://sanket-leads.onrender.com`. After the Hostinger deploy, open `https://sanketptt.com/leads/` and enter `LEADS_TOKEN`.

Nominatim's usage policy allows this low-volume, identified use. The service also caps how many searches one password can start.

## What a search does

Same industry, query type and country within 24 hours:

- If an earlier circle fully covers the new one (or a country sweep covers a later state sweep), the saved rows are filtered and returned. No new external calls.
- If the areas only overlap, those saved rows are kept and only new places are added.

Query types:

| Type | What it keeps |
|---|---|
| Meet in person | Address and phone, inside the radius, nearest first |
| Email / phone contacts | Address plus a phone or email. Email is verified only when it appears on the company's site and the domain has MX. Phone is verified only when it appears on that site. The website flag is a reachability check. |
| Industry sweep | The selected state, or the whole country |
| Contact person | A separate pass. A name is kept only when a public page prints it next to a title such as Plant Head or Head of Security. |
