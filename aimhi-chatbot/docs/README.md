# AIMhi-Y “Yarn” Chatbot

A Flask + Supabase, safety-aware chatbot that guides a young person through the AIMhi Stay Strong 4-step model using a deterministic flow (FSM) with optional LLM handoff. Risk detection surfaces crisis resources via a non-blocking popup; the conversation continues unless the user chooses otherwise.

## Features

- Supabase Auth (Google OAuth + Phone OTP) with JWT in `Authorization: Bearer <token>`
- Per-user sessions; chat history persisted in Supabase
- FSM-driven prompts from `config/responses.json` with sentiment-aware variation
- NLP pipeline:
  - Intent: HF zero-shot (facebook/bart-large-mnli) + LLM fallback
  - Sentiment: HF Twitter-RoBERTa + LLM fallback
  - Risk: LLM JSON classifier + HF suicidality fallback (non-blocking alert)
- CORS allowlist, security headers, and configurable rate limiting
- Health endpoint and lightweight web UI (Tailwind)

## Quick Start

1) Create a virtualenv and install deps
- Windows PowerShell
  - `python -m venv .venv`
  - `.\\.venv\\Scripts\\Activate`
- macOS/Linux
  - `python -m venv .venv`
  - `source .venv/bin/activate`

Then install dependencies:

- `pip install -r aimhi-chatbot/requirements.txt`
2) Configure environment
- Create `aimhi-chatbot/.env` and set at minimum:
  - Core: `FLASK_ENV`, `SECRET_KEY`, `CORS_ORIGINS`, optional `PORT`, `LOG_LEVEL`, `WEB_CONCURRENCY`, `GUNICORN_CMD_ARGS`
  - Supabase: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `SUPABASE_TIMEOUT`, `SUPABASE_RETRY_ATTEMPTS`
  - HF: `HF_TOKEN`
  - LLM Core: `LLM_PROVIDER` (`openai` or `ollama`), `LLM_API_KEY`, `LLM_MODEL`, `LLM_API_BASE` or `OLLAMA_API_BASE`, `LLM_MAX_TOKENS`
  - Risk Detection: `LLM_TIMEOUT_RISK`, `LLM_TEMPERATURE_RISK`, `LLM_SYSTEM_PROMPT_RISK`
  - Intent Classification: `LLM_TIMEOUT_INTENT`, `LLM_TEMPERATURE_INTENT`, `LLM_SYSTEM_PROMPT_INTENT`
  - Sentiment Analysis: `LLM_TIMEOUT_SENTIMENT`, `LLM_TEMPERATURE_SENTIMENT`, `LLM_SYSTEM_PROMPT_SENTIMENT`
  - LLM Handoff: `LLM_TIMEOUT_HANDOFF`, `LLM_TEMPERATURE_HANDOFF`, `LLM_HANDOFF_SYSTEM_PROMPT`
  - NLP Thresholds: `INTENT_CONFIDENCE_THRESHOLD`, `SENTIMENT_CONFIDENCE_THRESHOLD`, `RISK_CONFIDENCE_THRESHOLD`
  - HF API URLs: `HF_INTENT_API_URL`, `HF_SENTIMENT_API_URL`, `HF_RISK_API_URL`
  - Rate limit: `RATE_LIMIT_STORAGE` (e.g., `memory://` or `redis://...`), `RATE_LIMIT_DAY`, `RATE_LIMIT_HOUR`
3) Prepare database
- In Supabase SQL Editor, run `aimhi-chatbot/database/schema.sql`
- Use the Service Role key on server only. Clients should use the anon key.
4) Run
- Dev: `set FLASK_ENV=development` (Windows) or `export FLASK_ENV=development`
- Start: `python aimhi-chatbot/app.py`
- Open: `http://127.0.0.1:5000`

Production example:

- `gunicorn -w 2 -b 0.0.0.0:5000 aimhi-chatbot.app:app`

## API Overview

- `GET /health` – returns `{status, database, auth}`
- Auth
  - Auth handled client-side via Supabase JS (Google OAuth or Phone OTP)
  - `GET /auth/me` – returns `{user_id, authenticated}` if JWT valid
- Sessions
  - `POST /sessions` – create session; optional `fsm_state`
  - `GET /sessions` – list current user’s sessions
  - `GET /sessions/<id>/messages?limit=50` – history
  - `POST /sessions/<id>/messages` – `{message}` → routes via FSM/LLM, saves reply
  - `POST /sessions/<id>/accept` – `{step, message_id}` marks a response as final for a step

Notes

- All session endpoints require `Authorization: Bearer <jwt>` issued by Supabase Auth.
- Rate limits: global defaults per IP (`RATE_LIMIT_DAY`, `RATE_LIMIT_HOUR`) and endpoint-specific caps(Not currently robust due to use of in memory rate limit storage, future plans to move to redis)

## Architecture

- `app.py` – Flask app, CORS, rate limiting, routes, security headers
- `config/`
  - `auth_middleware.py` – decode Supabase JWT (HS256, `aud=authenticated`)
  - `supabase_client.py` – creates service/anon clients; `test_connection()`
  - `responses.json` – culturally safe response pools
- `core/`
  - `router.py` – FSM flow and message routing; `llm_conversation` state handling
  - `fsm.py` – FSM helpers
- `nlp/`
  - `intent_roberta_zeroshot.py` – HF zero-shot intent + LLM fallback
  - `sentiment.py` – HF sentiment + LLM fallback
  - `risk_detector.py` – LLM JSON risk + HF suicidality fallback
  - `response_selector.py` – varied responses by state/sentiment
- `llm/` – generic LLM client (OpenAI/Ollama) and `handoff_manager.py`
- `database/` – Supabase repository functions and `schema.sql`
- `templates/`, `static/` – demo frontend

## Environment Variables

Core

- `FLASK_ENV` (`development|production`), `SECRET_KEY`, `PORT`, `LOG_LEVEL`
- `CORS_ORIGINS` – comma-separated list of allowed origins (required in production)
- `WEB_CONCURRENCY`, `GUNICORN_CMD_ARGS` – production server configuration
- `RATE_LIMIT_STORAGE` (`memory://`, `redis://host:port/0`, `rediss://...`), `RATE_LIMIT_DAY`, `RATE_LIMIT_HOUR`

Supabase

- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
- Optional: `SUPABASE_TIMEOUT`, `SUPABASE_RETRY_ATTEMPTS`

Hugging Face

- `HF_TOKEN` – bearer token for Inference API
- Model API URLs: `HF_INTENT_API_URL`, `HF_SENTIMENT_API_URL`, `HF_RISK_API_URL`
- Confidence thresholds: `INTENT_CONFIDENCE_THRESHOLD`, `SENTIMENT_CONFIDENCE_THRESHOLD`, `RISK_CONFIDENCE_THRESHOLD`

LLM (OpenAI/Ollama)

- Core: `LLM_PROVIDER` (`openai` or `ollama`), `LLM_API_KEY`, `LLM_MODEL`, `LLM_MAX_TOKENS`
- OpenAI: `LLM_API_BASE` (default: `https://api.openai.com/v1`)
- Ollama: `OLLAMA_API_BASE` (default: `http://localhost:11434`)
- Risk Detection: `LLM_TIMEOUT_RISK`, `LLM_TEMPERATURE_RISK`, `LLM_SYSTEM_PROMPT_RISK`
- Intent Classification: `LLM_TIMEOUT_INTENT`, `LLM_TEMPERATURE_INTENT`, `LLM_SYSTEM_PROMPT_INTENT`
- Sentiment Analysis: `LLM_TIMEOUT_SENTIMENT`, `LLM_TEMPERATURE_SENTIMENT`, `LLM_SYSTEM_PROMPT_SENTIMENT`
- Handoff/Free-form: `LLM_TIMEOUT_HANDOFF`, `LLM_TEMPERATURE_HANDOFF`, `LLM_HANDOFF_SYSTEM_PROMPT`

## Security

- Auth: JWT in Authorization header; CSRF is not used (no cookies)
- CORS: allow only known origins in production (required)
- Headers: CSP, X-Frame-Options, X-Content-Type-Options, basic XSS protection
- Rate limiting: per-IP; configure Redis for multi-instance deployments
- Supabase keys: keep Service Role key on server only; never expose in the browser

## Testing

- Tests are not written yet. The app is tested manually

# 

## Deployment Notes

- Containers (e.g., Render/Railway/Fly) are recommended for Flask + Gunicorn
- If using Redis for rate limits, add a Redis add-on and set `RATE_LIMIT_STORAGE=redis://...`
- Set `CORS_ORIGINS` to your real domain(s) and enforce HTTPS

See `docs/LLM_GUIDELINES.md` and `docs/SAFETY.md` for model and safety specifics.
