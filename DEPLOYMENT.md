# Oracle deployment

The app runs on Oracle ARM64 with Gunicorn, an isolated Redis rate-limit store,
and the existing Coolify Traefik Docker provider. Nothing binds new host ports.
The existing proxy is neither edited nor restarted. App containers join its
existing `coolify` network using app-specific router and middleware names.

## Layout and startup

Everything for this installation lives in `/home/ubuntu/chatbot`:

```
chatbot/
  .env          # chmod 600; credentials, never in Git
  source/       # repository contents
    .env -> ../.env
  build.log
```

Copy `.env.example` to the private environment file and fill the required values.
Generate `SECRET_KEY` with `python3 -c 'import secrets; print(secrets.token_hex(32))'`.
Create the symlink only if no `source/.env` already exists. From `source/`:

```sh
sudo docker compose config --quiet
sudo docker compose build
sudo docker compose run --rm --no-deps app python check_env.py
sudo docker compose up -d --wait
curl --fail https://chatbot.arpanlabs.com/health
```

Do not print `docker compose config` without `--quiet`: it includes credentials.
Compose fixes production mode, internal port 5000, Redis URL, one Gunicorn worker,
four threads, and a 120-second worker timeout. The single worker keeps the existing
in-memory FSM attempt counters consistent; session state remains in Supabase.
Redis only holds rate-limit counters and intentionally has no persistent volume.
Docker images/build cache also live in Docker's shared storage.
The image installs `requirements.lock`, captured from the verified ARM64 build.
After dependency changes, regenerate that lockfile in the target Python 3.11
environment and rerun the deployment tests.

## DNS, TLS, and authentication

Cloudflare A record: `chatbot.arpanlabs.com` → `192.9.191.72`, initially DNS-only.
Traefik uses its existing `http`/`https` entrypoints and `letsencrypt` resolver.
HTTP redirects to HTTPS. DNS-only permits a direct origin certificate check.
If later enabling Cloudflare proxying, use Full (strict) TLS; do not change the
zone's SSL mode casually because it also affects other sites.

Supabase project: `yqqzyrvleuvykizwtnww` (aimhi supabase db).
Set its Auth Site URL to `https://chatbot.arpanlabs.com` and allow
`https://chatbot.arpanlabs.com/chat` as a redirect URL. Preserve existing URLs
if other apps use the project. Google login needs an enabled Google provider and
Google OAuth credentials; phone OTP needs an enabled SMS provider. These are
Supabase dashboard settings, not app environment variables.

The backend verifies bearer tokens through Supabase Auth, supporting current
asymmetric signing keys and legacy tokens. `SUPABASE_JWT_SECRET` is unnecessary.
The public key goes into page metadata; the backend service key stays server-side.

Inspect existing tables before applying `aimhi-chatbot/database/schema.sql`.
It is a first-install schema, not a safe repeatable migration. Never run it over
an existing database blindly. Required tables are `sessions`, `chat_history`,
`risk_detections`, and `intent_classifications`, all with RLS enabled. The backend
uses its privileged key and enforces ownership in repository methods.

## Required environment variables

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Random Flask secret; generated per installation |
| `CORS_ORIGINS` | `https://chatbot.arpanlabs.com` (comma-separated if needed) |
| `SUPABASE_URL` | `https://yqqzyrvleuvykizwtnww.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase publishable or legacy anon key, safe for browser use |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend Supabase secret or legacy service-role key |
| `LLM_PROVIDER` | `openai` for an OpenAI-compatible endpoint, or `ollama` |
| `LLM_MODEL` | Model supported by the configured provider |
| `LLM_API_KEY` | Required with `LLM_PROVIDER=openai` |
| `OLLAMA_API_BASE` | Required with `LLM_PROVIDER=ollama`; reachable from the container |
| `LLM_SYSTEM_PROMPT_RISK` | Reviewed risk-classifier prompt; require JSON with `label` equal to `risk` or `no_risk` |
| `LLM_HANDOFF_SYSTEM_PROMPT` | Reviewed supportive conversation prompt |

## Optional environment variables

| Variable(s) | Default / purpose |
| --- | --- |
| `CHATBOT_HOST` | `chatbot.arpanlabs.com`; Traefik hostname |
| `TRAEFIK_NETWORK` | `coolify`; existing external Docker network |
| `LOG_LEVEL` | `INFO` |
| `RATE_LIMIT_DAY`, `RATE_LIMIT_HOUR` | `200`, `50` per client IP |
| `HEALTH_TTL_SECONDS` | `60`; database health cache |
| `LLM_API_BASE` | `https://api.openai.com/v1`; OpenAI-compatible base URL |
| `LLM_TIMEOUT`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS` | `45.0`, `0.8`, `500` for main conversation; classification modules default to 100 tokens |
| `LLM_TIMEOUT_RISK`, `LLM_TEMPERATURE_RISK` | `2.0`, `0.1` |
| `LLM_TIMEOUT_INTENT`, `LLM_TEMPERATURE_INTENT` | `5.0`, `0.3` |
| `LLM_TIMEOUT_SENTIMENT`, `LLM_TEMPERATURE_SENTIMENT` | `10.0`, `0.7` |
| `LLM_SYSTEM_PROMPT_INTENT`, `LLM_SYSTEM_PROMPT_SENTIMENT` | Built-in classifier prompts |
| `HF_TOKEN` | Hugging Face token; intent/sentiment fall back to LLM if absent; required for HF risk fallback |
| `HF_INTENT_API_URL`, `HF_SENTIMENT_API_URL`, `HF_RISK_API_URL` | Override the built-in Hugging Face inference endpoints |
| `HF_RISK_TIMEOUT` | `5.0` |
| `INTENT_CONFIDENCE_THRESHOLD`, `SENTIMENT_CONFIDENCE_THRESHOLD`, `RISK_CONFIDENCE_THRESHOLD` | `0.5` |

`FLASK_ENV`, `PORT`, `WEB_CONCURRENCY`, `GUNICORN_CMD_ARGS`, and
`RATE_LIMIT_STORAGE` are set by this Compose deployment. `REDIS_URL` is supported
by the app as a fallback outside Compose. `SUPABASE_TIMEOUT`,
`SUPABASE_RETRY_ATTEMPTS`, `LLM_TIMEOUT_HANDOFF`, `LLM_TEMPERATURE_HANDOFF`, and
`LLM_ENABLED` are not read by the current implementation and are not required.

## Verification and limits

```sh
sudo docker compose run --rm --no-deps app python -m unittest discover -s tests -p test_deployment.py -v
sudo docker compose ps
curl --fail https://chatbot.arpanlabs.com/healthz
curl --fail https://chatbot.arpanlabs.com/health
```

Also verify a real login, user-owned session creation, message persistence,
classification, and LLM replies with configured credentials before declaring
the service ready. Existing tests other than `test_deployment.py` are placeholders.
The existing risk pipeline can return `no_risk` when inference fails; deployment
checks do not establish clinical safety. Review prompts and test provider failures
before using this application with real users.

## Later removal (requires approval)

Stop only this Compose project from its `source/` folder. Do not prune Docker,
remove the shared `coolify` network, or stop Coolify/Traefik/n8n. The app stores
conversation data in the restored Supabase project, outside the Oracle folder.
DNS and Supabase data must be handled separately. No teardown is performed by
this deployment procedure.

References: [Traefik Docker routing](https://doc.traefik.io/traefik/reference/routing-configuration/other-providers/docker/),
[Supabase token verification](https://supabase.com/docs/reference/python/auth-getuser),
[Flask changes](https://flask.palletsprojects.com/en/stable/changes/).
