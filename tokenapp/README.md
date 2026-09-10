# Token Automation Service

A FastAPI web app that automatically fetches and refreshes OAuth2
`client_credentials` access tokens from a third-party API, caches them in
PostgreSQL, and keeps them fresh via a background scheduler — so any
endpoint that needs to call the external API always has a valid token on
hand, with no manual token management.

## How it works

- **`app/token_manager.py`** — talks to your OAuth2 provider's token
  endpoint, stores the resulting token + expiry in Postgres, and knows how
  to decide "is this token still good, or do I need a new one?"
- **`app/scheduler.py`** — an APScheduler background job (runs inside the
  same process) that checks every `POLL_INTERVAL_SECONDS` and refreshes the
  token if it's within `TOKEN_REFRESH_MARGIN_SECONDS` of expiring. This
  means the token is proactively refreshed *before* it expires, rather than
  reactively refreshed after a call fails.
- **`app/routers/token.py`** — `GET /token/status` (masked token info) and
  `POST /token/refresh` (force an immediate refresh).
- **`app/routers/proxy.py`** — an example `GET /proxy/call?path=...`
  endpoint showing how any route can pull `token_manager.get_valid_token()`
  and use it to call the external API, with automatic refresh baked in.

## Quick start

1. Copy the environment template and fill in your real OAuth2 provider
   details:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env`:
   - `OAUTH_TOKEN_URL` — your provider's token endpoint
   - `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET` — your app's credentials
   - `EXTERNAL_API_BASE_URL` — the API you want to call with the token

3. Build and run:

   ```bash
   docker compose up --build
   ```

4. The app is now live:
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health
   - Token status: http://localhost:8000/token/status
   - Force refresh: `curl -X POST http://localhost:8000/token/refresh`
   - Example proxied call: http://localhost:8000/proxy/call?path=some/endpoint
   - Postgres admin UI (Adminer): http://localhost:8080
     (system: PostgreSQL, server: `db`, user/pass/db: `tokenapp`)

## Running locally without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Point DATABASE_URL at a local Postgres instance, then:
uvicorn app.main:app --reload
```

## Notes on security

- Access tokens are never returned in full over the API — `/token/status`
  only shows a masked preview (`abcd...wxyz`) plus the expiry time.
- Store `.env` outside of version control (it's already in `.dockerignore`;
  add it to `.gitignore` too).
- For production, consider adding: encryption-at-rest for the
  `token_records` table, a secrets manager (Vault/AWS Secrets Manager) for
  `OAUTH_CLIENT_SECRET` instead of a plain `.env` file, and restricting
  `/token/refresh` behind auth if it's reachable from outside your network.

## Project layout

```
app/
  main.py          # FastAPI app, lifespan startup/shutdown
  config.py        # Settings (env vars)
  database.py      # Async SQLAlchemy engine/session
  models.py        # TokenRecord table
  schemas.py       # Pydantic response models
  token_manager.py # Fetch/cache/refresh logic
  scheduler.py      # Background refresh job (APScheduler)
  routers/
    health.py
    token.py
    proxy.py
Dockerfile
docker-compose.yml
requirements.txt
.env.example
```
