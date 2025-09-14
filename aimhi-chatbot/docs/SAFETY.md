# Safety

This document outlines how the Yarn chatbot mitigates risk, enforces boundaries, and protects data.

## Objectives

- Prioritize user safety; detect and respond to suicide/self‑harm risk
- Keep conversation supportive, strengths‑based, and non‑clinical
- Avoid collecting or emitting personally identifiable information (PII)
- Protect services from abuse (rate limits, auth, CORS, headers)

## Risk Detection and Response

Detection pipeline
- Router calls a risk gate before normal flow. Intended behavior: call `nlp.risk_detector.detect_risk(text)` and read `{"label": "risk|no_risk"}`.
- Primary: LLM JSON classifier (OpenAI or Ollama) with strict `LLM_SYSTEM_PROMPT`
- Fallback: HF Inference `sentinet/suicidality` with a confidence threshold

Response on risk
- Conversation is short‑circuited and a crisis help message is returned, e.g., 13YARN (13 92 76) and Lifeline (13 11 14)
- The detection event is logged via `database/repository.record_risk_detection(...)`

Important wiring note
- Current code in `core/router.py` imports `contains_risk` from `nlp/risk_detector`, which is not exported. This forces a stubbed “no risk” fallback. To re‑enable the safety gate, switch the router to use `detect_risk(...)` (see LLM_GUIDELINES — Known Issues).

## Content Boundaries

- Not a crisis or clinical service: do not provide diagnosis, treatment, or medical advice
- Keep replies short (1–2 sentences) and strengths‑based
- No PII collection: do not ask for names, addresses, phone numbers, or other identifiers
- Use culturally safe, plain Australian English (no medical jargon)

## Privacy and Data Handling

- Auth: Supabase JWT in Authorization header; no auth cookies → CSRF not applicable
- Storage: chat sessions and messages are stored in Supabase and scoped per user; repository functions always check `user_id` ownership
- Keys: Service Role key is server‑only; the browser uses the anon key for sign‑in/sign‑up via API, never stored client‑side in code
- Logging: risk/intent events are stored for audit; avoid storing PII in free‑text where possible

## Platform Protections

- CORS: in production, `CORS_ORIGINS` must list only trusted origins; app refuses to start otherwise
- Security headers: CSP (restricts scripts/styles/connect), X‑Frame‑Options=DENY, X‑Content‑Type‑Options=nosniff, basic XSS protection
- Rate limiting: per‑IP global defaults (`RATE_LIMIT_DAY`, `RATE_LIMIT_HOUR`) and route‑specific caps; use Redis storage in production multi‑instance setups
- Authentication: all session endpoints require a valid JWT; middleware verifies `aud=authenticated` and extracts `sub` as `user_id`

## Known Gaps / Recommendations

- Router risk import bug disables the risk short‑circuit — fix to use `detect_risk(...)`
- Consider Supabase Row‑Level Security (RLS) policies mirroring repository ownership checks
- Add abuse monitoring (e.g., repeated risk flags, excessive usage beyond limits)
- Keep `responses.json` focused on safe phrasing; review and curate culturally safe prompts regularly

## Operational Checklist

- Set `CORS_ORIGINS` to real domains; enforce HTTPS
- Provide `LLM_SYSTEM_PROMPT` for risk and test with red‑team phrases
- Configure `RATE_LIMIT_STORAGE` (`redis://...`) for production
- Verify Supabase schema via `database/schema.sql`; ensure Service Role key is not exposed client‑side

## Testing Safety

- Unit tests must mock network calls (OpenAI/Ollama/HF) and assert:
  - Risk classifier returns JSON; router short‑circuits on risk and logs an event
  - No PII in generated replies when LLM handoff is enabled
  - CORS and security headers appear on responses

