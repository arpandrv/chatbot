# Tests for llm/client.py
#
# Strategy:
# - Patch requests.post to simulate OpenAI and Ollama endpoints.
# - Patch os.environ to toggle LLM_PROVIDER and set API base URLs and keys.
#
# Test cases:
# - call_llm_openai happy path: builds correct payload (model, messages, temperature, max_tokens) and parses content.
# - call_llm_openai error path: HTTP error -> raises RuntimeError with message.
# - call_llm_ollama happy path: builds correct prompt and parses 'response' field.
# - call_llm_ollama error path: HTTP error -> raises RuntimeError.
# - call_llm dispatch: when LLM_PROVIDER='ollama' uses ollama version, otherwise openai version.
#
# Notes:
# - Validate headers include Authorization for OpenAI.
# - Do not hit network.

