# Tests for nlp/response_selector.VariedResponseSelector
#
# Strategy:
# - Monkeypatch file loading to provide a tiny in-memory responses.json structure (avoid real file I/O).
# - Alternatively, patch VariedResponseSelector._load_response_pools to return a deterministic dict.
#
# Test cases:
# - get_response returns a random element from list for valid category/subcategory; seed random for determinism.
# - get_prompt uses 'prompt' subcategory by default and returns a value.
# - Sentiment weighting: for 'positive' sentiment, responses containing enthusiastic words are favored; for 'negative',
#   empathetic words are favored; verify distribution by seeding RNG and checking chosen element (single-run determinism via seed).
# - Fallback: missing category or subcategory returns _get_fallback_response value.
# - String pool handling: if subcategory value is a string, returns it directly.
# - Missing/invalid JSON load path: when loader returns {}, calls to get_response fall back.
#
# Notes:
# - Patch random.choice to deterministic behavior if needed.
# - Do not read actual aimhi-chatbot/config/responses.json to keep tests hermetic.

