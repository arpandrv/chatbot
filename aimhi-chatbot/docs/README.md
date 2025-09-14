# AIMhi‑Y “Yarn” Chatbot

A Flask + Supabase, safety‑aware chatbot that guides a young person through the AIMhi Stay Strong 4‑step model using a deterministic flow (FSM) with optional LLM handoff. It uses Hugging Face Inference APIs for intent/sentiment (with LLM fallbacks) and short‑circuits to crisis resources on risk.

## Features

- Supabase Auth (email/password) with JWT in `Authorization: Bearer <token>`
- Per‑user sessions; chat history persisted in Supabase
- FSM‑driven prompts from `config/responses.json` with sentiment‑aware variation
- NLP pipeline:
  - Intent: HF zero‑shot (facebook/bart‑large‑mnli) → LLM fallback
  - Sentiment: HF Twitter‑RoBERTa → LLM fallback
  - Risk: LLM JSON classifier → HF suicidality fallback
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
  - Core: `FLASK_ENV`, `SECRET_KEY`, `CORS_ORIGINS`, optional `PORT`, `LOG_LEVEL`
  - Supabase: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
  - HF: `HF_TOKEN`
  - LLM: `LLM_PROVIDER` (`openai` or `ollama`), `LLM_API_KEY` (for OpenAI), `LLM_MODEL`, `LLM_API_BASE` or `OLLAMA_API_BASE`
  - Risk prompt: `LLM_SYSTEM_PROMPT` (JSON‑only risk classifier)
  - Optional: `LLM_HANDOFF_SYSTEM_PROMPT` (for free‑form “yarn” handoff)
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

- `GET /health` — returns `{status, database, auth}`
- Auth
  - `POST /auth/register` — `{email, password}` → 201
  - `POST /auth/login` — `{email, password}` → tokens
  - `POST /auth/logout` — requires Bearer token
  - `GET /auth/me` — returns `{user_id, authenticated}`
- Sessions
  - `POST /sessions` — create session; optional `fsm_state`
  - `GET /sessions` — list current user’s sessions
  - `GET /sessions/<id>/messages?limit=50` — history
  - `POST /sessions/<id>/messages` — `{message}` → saves user message, routes via FSM/LLM, saves reply
  - `POST /sessions/<id>/accept` — `{step, message_id}` marks a response as final for a step

Notes
- All session endpoints require `Authorization: Bearer <jwt>` issued by Supabase Auth.
- Rate limits: global defaults per IP (`RATE_LIMIT_DAY`, `RATE_LIMIT_HOUR`) and endpoint‑specific caps.

## Architecture

- `app.py` — Flask app, CORS, rate limiting, routes, security headers
- `config/`
  - `auth_middleware.py` — decode Supabase JWT (HS256, `aud=authenticated`)
  - `supabase_client.py` — creates service/anon clients; `test_connection()`
  - `responses.json` — culturally safe response pools
- `core/`
  - `router.py` — FSM flow and message routing; optional `llm_conversation` state
  - `fsm.py` — FSM helpers
- `nlp/`
  - `intent_roberta_zeroshot.py` — HF zero‑shot intent → LLM fallback
  - `sentiment.py` — HF sentiment → LLM fallback
  - `risk_detector.py` — LLM JSON risk → HF suicidality fallback
  - `response_selector.py` — varied responses by state/sentiment
- `llm/` — generic LLM client (OpenAI/Ollama) and `handoff_manager.py`
- `database/` — Supabase repository functions and `schema.sql`
- `templates/`, `static/` — demo frontend

## Environment Variables

Core
- `FLASK_ENV` (`development|production`), `SECRET_KEY`, `PORT`, `LOG_LEVEL`
- `CORS_ORIGINS` — comma‑separated list of allowed origins (required in production)
- `RATE_LIMIT_STORAGE` (`memory://`, `redis://host:port/0`, `rediss://...`), `RATE_LIMIT_DAY`, `RATE_LIMIT_HOUR`

Supabase
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`

Hugging Face
- `HF_TOKEN` — bearer token for Inference API
- Optional overrides: `HF_ZS_API_URL`, `HF_SENTIMENT_API_URL`, `HF_RISK_API_URL`

LLM (OpenAI/Ollama)
- `LLM_PROVIDER` (`openai` or `ollama`)
- `LLM_API_KEY`, `LLM_MODEL`, `LLM_API_BASE` (OpenAI)
- `OLLAMA_API_BASE` (Ollama)
- `LLM_TIMEOUT`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`
- Risk classifier prompt: `LLM_SYSTEM_PROMPT`
- Optional handoff: `LLM_HANDOFF_SYSTEM_PROMPT`
- Optional router toggle: `LLM_ENABLED=true` enables `llm_conversation` branch messaging

## Security

- Auth: JWT in Authorization header; CSRF is not used (no cookies)
- CORS: allow only known origins in production (required)
- Headers: CSP, X‑Frame‑Options, X‑Content‑Type‑Options, basic XSS protection
- Rate limiting: per‑IP; configure Redis for multi‑instance deployments
- Supabase keys: keep Service Role key on server only; never expose in the browser

## Testing

- Run: `python -m unittest discover -s aimhi-chatbot/tests -p "test_*.py"`
- Tests are scaffolds with detailed comments (no live network)
- Mock Supabase and HTTP clients for predictability

## Known Gaps / TODO

- `core/router.py` imports `contains_risk` and `get_crisis_resources`, but `nlp/risk_detector.py` exports `detect_risk(...)` only. This causes the router’s NLP import block to fall back to stubbed no‑risk behavior. Fix by wiring `route_message` to call `nlp.risk_detector.detect_risk` (thin wrapper to boolean + resources).
- `transitions` is in requirements but not used; safe to remove once confirmed.
- `LLM_HANDOFF_SYSTEM_PROMPT` exists but `llm_conversation` handler is a stub; wire to `llm/handoff_manager.py` if enabling free‑form chat.
- The bundled `.env` includes variables not used by code (e.g., provider names other than `openai|ollama`, and per‑feature timeouts). Prefer the variables listed above.

## Deployment Notes

- Containers (e.g., Render/Fly/Heroku) are recommended for Flask + Gunicorn
- If using Redis for rate limits, add a Redis add‑on and set `RATE_LIMIT_STORAGE=redis://...`
- Set `CORS_ORIGINS` to your real domain(s) and enforce HTTPS

See `docs/LLM_GUIDELINES.md` and `docs/SAFETY.md` for model and safety specifics.
