# Tests for nlp/sentiment.analyze_sentiment
#
# Strategy:
# - Patch requests.post to emulate HF API response and error cases.
# - Patch analyze_sentiment_llm in primary_fallback.sentiment_fallback_llm for fallback behavior.
# - Patch env HF_TOKEN and HF_SENTIMENT_API_URL where needed.
#
# Test cases:
# - Happy path: returns top label normalized to 'negative'/'neutral'/'positive' with confidence and method 'hf_text_classification'.
# - HF API returns unexpected/empty payload -> triggers fallback; verify method 'llm_fallback_on_error' and fallback_reason present.
# - HF_TOKEN missing -> raises internally and triggers fallback.
# - Empty input => returns neutral label with method 'empty_input'.
# - Label normalization mapping: 'LABEL_0', 'LABEL_1', 'LABEL_2' map to negative/neutral/positive respectively.
#
# Notes:
# - Ensure requests.post is never actually called against network.

