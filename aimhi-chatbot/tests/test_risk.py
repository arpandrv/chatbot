"""
Risk detection tests for nlp/risk_detector.py

Comments only — implementation to be added later.

Test setup:
- Patch requests.post/get to avoid network for OpenAI/Ollama checks.
- Patch environment variables for LLM_PROVIDER/API base/keys and SYSTEM_PROMPT.
- Patch primary_fallback.risk_fallback_sucidality.detect_risk_fallback to return deterministic fallback label/confidence.

Test cases:
- parse_json_response: valid JSON dict with {'label': 'risk'} returns dict; invalid/missing label -> returns {'label': 'no_risk', 'error': ...}.
- detect_risk_openai: builds payload with SYSTEM_PROMPT and user prompt, parses message JSON via parse_json_response; on HTTP error -> fallback used.
- detect_risk_ollama: builds prompt (SYSTEM_PROMPT + user message) and parses 'response' via parse_json_response; on HTTP error -> fallback.
- is_llm_available: returns True when API key present (openai) or Ollama tag list endpoint reachable (mocked 200); False otherwise.
- detect_risk (main):
  - When LLM available and returns non-fallback method -> returns that result.
  - When LLM unavailable or method == 'huggingface_fallback' -> uses fallback result.

Notes:
- Ensure SYSTEM_PROMPT is set during import to avoid RuntimeError.
- No external network calls; everything must be mocked.
"""
