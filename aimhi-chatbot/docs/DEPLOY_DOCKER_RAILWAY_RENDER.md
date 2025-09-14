# Deploy with Docker on Railway or Render

This guide shows how to containerize and deploy the Yarn chatbot using Docker to Railway or Render.

## Prerequisites

- A Supabase project with the database schema applied (see `aimhi-chatbot/database/schema.sql`).
- Supabase Auth configured with the Google provider enabled. Copy the project URL, anon key, and JWT secret.
- Crisis/risk LLM env either configured or leave defaults. In dev, risk detection gracefully degrades.
- Docker installed locally (optional if using Git-based deploy).

## Repo Layout

- App: `aimhi-chatbot/app.py` (Flask)
- Dockerfile: `aimhi-chatbot/Dockerfile`
- Requirements: `aimhi-chatbot/requirements.txt`

If your platform expects a root-level Dockerfile, either set the context to `aimhi-chatbot/` or move the Dockerfile to repo root and adjust paths accordingly.

## Environment Variables

Set these in the deployment dashboard (never commit secrets):

- `SECRET_KEY` — Flask secret. Example: `dev` (non-empty)
- `FLASK_ENV` — `production`
- `PORT` — `5000`
- `SUPABASE_URL` — e.g. `https://<project>.supabase.co`
- `SUPABASE_ANON_KEY` — project anon key
- `SUPABASE_SERVICE_ROLE_KEY` — service role key (server-side)
- `SUPABASE_JWT_SECRET` — your Supabase JWT secret (used to verify tokens)
- `CORS_ORIGINS` — comma-separated allowed origins (your frontend origin)

Optional (risk/LLM):

- `LLM_PROVIDER` — `openai` or `ollama`
- `LLM_API_KEY`, `LLM_MODEL`, `LLM_SYSTEM_PROMPT`, `LLM_API_BASE`, etc.

## Docker Build (local)

From repo root:

```bash
docker build -t yarn-chatbot -f aimhi-chatbot/Dockerfile aimhi-chatbot
docker run -p 5000:5000 --env-file ./aimhi-chatbot/.env yarn-chatbot
```

The server listens on `0.0.0.0:5000` and serves the UI at `/`.

## Deploy to Railway

1. Create a new service in Railway and select “Deploy from GitHub”.
2. Choose this repo. In service settings:
   - Build command: leave empty (Dockerfile used automatically)
   - Root directory (optional): `aimhi-chatbot`
   - Health check path: `/health`
3. Add environment variables listed above.
4. Deploy. Confirm logs show `Flask app initialized` and `/health` returns `200`.

Notes:
- If Railway uses Nixpacks instead of Dockerfile, force Docker by enabling “Dockerfile Deployments”.
- Ensure `PORT=5000` is set; Railway injects a `PORT`, but our image defaults to 5000.

## Deploy to Render

Option A: “Web Service” from repo (Docker)

1. Create a new “Web Service”.
2. Select this repo; Render detects the Dockerfile.
3. Set the root directory to `aimhi-chatbot` or point to the Dockerfile path.
4. Set “Environment” to “Docker”.
5. Add environment variables (see list above).
6. Set the port to `5000` if asked (Render usually sets `PORT` env automatically).
7. Deploy and visit the service URL.

Option B: Prebuilt image

1. Build and push your image to a registry.
2. Create a Render service from image and set env vars.

## Verifying Auth (Google)

- The UI loads Supabase JS from CDN. On the sign-in modal, click “Continue with Google”.
- After redirect back, the session is read and the access token is used for API calls.
- The backend verifies JWTs using `SUPABASE_JWT_SECRET` via `config/auth_middleware.py`.

## Troubleshooting

- 503 from `/health`: verify `SUPABASE_*` env vars and that the schema exists.
- 401 from API: ensure the JWT secret matches the project’s JWT secret, and tokens are present after OAuth.
- CORS errors: set `CORS_ORIGINS` to your frontend origin(s). Example: `https://your-app.onrender.com`
- Risk prompt error: if `LLM_SYSTEM_PROMPT` is not set, router falls back and won’t block chat.

## Production Command

The container uses:

```bash
gunicorn -w 2 -b 0.0.0.0:5000 aimhi-chatbot.app:app
```

You can scale workers depending on instance size.
