# LLM Guidelines

This document explains how the Yarn chatbot uses Large Language Models (LLMs), the prompts and outputs expected, and how to configure providers and fallbacks safely.

## Where LLMs Are Used

Primary generation

- `llm/client.py` — provider‑agnostic client for OpenAI or Ollama (non‑streaming). Used by `llm/handoff_manager.py` to generate free‑form replies when the conversation transitions to an LLM conversation mode.
- `llm/handoff_manager.py` — formats full conversation context → calls `call_llm(...)` with `LLM_HANDOFF_SYSTEM_PROMPT`.

Classification / safety checks

- `nlp/risk_detector.py` — JSON‑only LLM classifier for suicide/self‑harm risk; falls back to HF `sentinet/suicidality` when the LLM is unavailable or fails.
- `nlp/intent_roberta_zeroshot.py` — HF zero‑shot intent first; falls back to `primary_fallback/intent_fallback_llm.py` (LLM JSON output) when zero‑shot is low confidence or fails.
- `nlp/sentiment.py` — HF sentiment first; falls back to `primary_fallback/sentiment_fallback_llm.py` (LLM JSON output) on error.

Routing

- `core/router.py` guards the conversation with a risk check and runs the FSM. The `llm_conversation` state is gated by `LLM_ENABLED=true`. Risk detection import is currently mis‑wired (see “Known Issues”).

## Providers and Configuration

Supported providers

- `LLM_PROVIDER=openai` — calls OpenAI Chat Completions via `LLM_API_BASE` (default `https://api.openai.com/v1`).
- `LLM_PROVIDER=ollama` — calls a local Ollama instance via `OLLAMA_API_BASE` (default `http://localhost:11434`).

Common variables

- Core: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_MAX_TOKENS`
- OpenAI: `LLM_API_KEY`, `LLM_API_BASE`
- Ollama: `OLLAMA_API_BASE`
- Task-specific timeouts: `LLM_TIMEOUT_RISK`, `LLM_TIMEOUT_INTENT`, `LLM_TIMEOUT_SENTIMENT`, `LLM_TIMEOUT_HANDOFF`
- Task-specific temperatures: `LLM_TEMPERATURE_RISK`, `LLM_TEMPERATURE_INTENT`, `LLM_TEMPERATURE_SENTIMENT`, `LLM_TEMPERATURE_HANDOFF`

Task‑specific prompts

- Risk Detection: `LLM_SYSTEM_PROMPT_RISK` (required). Strict JSON output.
- Intent Classification: `LLM_SYSTEM_PROMPT_INTENT` (LLM fallback)
- Sentiment Analysis: `LLM_SYSTEM_PROMPT_SENTIMENT` (LLM fallback)
- Handoff/free‑form: `LLM_HANDOFF_SYSTEM_PROMPT` (optional, required if enabling LLM yarn mode)

Hugging Face (fallbacks and primaries)

- `HF_TOKEN` is required for HF Inference API calls.
- Model API URLs: `HF_INTENT_API_URL`, `HF_SENTIMENT_API_URL`, `HF_RISK_API_URL`
- Confidence thresholds: `INTENT_CONFIDENCE_THRESHOLD`, `SENTIMENT_CONFIDENCE_THRESHOLD`, `RISK_CONFIDENCE_THRESHOLD`

## Prompt Contracts (Strict)

Risk (required: `LLM_SYSTEM_PROMPT_RISK`)

- Instruction goals: single‑message suicide/self‑harm risk classifier for a youth wellbeing chatbot.
- Output: JSON only, one of:
  - `{'label': 'risk'}`
  - `{'label': 'no_risk'}`
- Guidance: prefer "risk" on ambiguous first‑person despair; handle slang/misspellings; no extra text.
- Parser: `nlp/risk_detector.parse_json_response()` handles both single and double quote formats and expects a JSON object with a `label` field.

Intent (fallback LLM)

- Task: map a message to exactly one of the categories used by the FSM (greeting, question, affirmative, negative, support_people, strengths, worries, goals, no_support, no_strengths, no_worries, no_goals, unclear).
- Output: JSON only — `{ "intent": "<category>" }`.
- Parser in `primary_fallback/intent_fallback_llm.py` extracts `intent` and validates it against known categories.

Sentiment (fallback LLM)

- Task: single‑message sentiment analysis.
- Output: JSON only — `{ "sentiment": "positive|neutral|negative" }`.

Handoff/free‑form (optional)

- Instruction goals: short, strengths‑based, culturally safe, non‑clinical chat replies.
- Style/constraints:
  - 1–2 sentences, plain Australian English, no markdown
  - No medical advice or diagnosis; no PII collection
  - If any risk language appears, prioritize safety and suggest contacting 13YARN (13 92 76) or Lifeline (13 11 14)
- Input format: `handoff_manager` concatenates the conversation into a simple transcript string.

## Timeouts and Budgets

- `llm/client.py`: `LLM_TIMEOUT_HANDOFF` for chat generation.
- `nlp/risk_detector.py`: uses `LLM_TIMEOUT_RISK` for classification; falls back to HF on failure.
- Intent/Sentiment fallbacks: use `LLM_TIMEOUT_INTENT` and `LLM_TIMEOUT_SENTIMENT` respectively.
- HF requests: rely on `requests` defaults; use lightweight inputs to avoid latency.

## Logging and Telemetry

- Classifiers record results into Supabase via `database/repository.py` (`record_risk_detection`, `record_intent_classification`).
- Handle exceptions defensively; classification fallbacks should never crash the request.

## Known Issues

- Performance: Multiple sequential API calls create latency bottlenecks. Consider parallel processing for non-blocking operations.

## Safety Principles

- Always surround LLM usage with guardrails: strict prompts, timeouts, and safe fallbacks.
- 
