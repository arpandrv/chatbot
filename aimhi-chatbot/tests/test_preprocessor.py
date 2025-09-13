# Tests for nlp/preprocessor.normalize_text
#
# Simple, no mocks needed.
#
# Test cases:
# - Lowercases input: 'Hello WORLD' -> 'hello world'.
# - Trims whitespace: '  hi  ' -> 'hi'.
# - Preserves inner spaces (no collapsing beyond strip): 'hello   there' remains 'hello   there' lowercased.

