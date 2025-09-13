# Tests for nlp/intent_roberta_zeroshot.classify_intent and helpers
#
# Strategy:
# - Patch requests.post to return a fake HF zero-shot response.
# - Patch environment vars: HF_TOKEN, HF_ZS_API_URL, ROBERTA_INTENT_THRESHOLD.
# - Patch classify_intent_llm in primary_fallback.intent_fallback_llm for fallback path assertions.
#
# Test cases:
# - Happy path: HF returns labels/scores; top label maps via PHRASE_TO_KEY to internal key; confidence >= threshold -> method "hf_zero_shot_bart_mnli".
# - Threshold fallback: same HF response but with confidence < threshold triggers classify_intent_with_fallback and uses LLM fallback.
# - Response shape variants: dict with labels/scores vs. list of {label, score}; both parse correctly.
# - Preprocess_text normalization: contractions/cultural terms replaced ("i'm" -> "i am", "yarning" -> "talking").
# - HF_TOKEN missing: _headers raises -> fallback path used with method "llm_fallback".
# - Empty/whitespace input: returns label "unclear", method "empty_input".
#
# Notes:
# - Ensure no network access: requests.post must be fully mocked.
# - Verify candidate labels passed contain KEY_TO_PHRASE values.

