# Tests for llm/handoff_manager.handle_llm_response
#
# Strategy:
# - Patch llm.client.call_llm to capture system prompt and user message (context) and return a stub response.
# - Patch env LLM_HANDOFF_SYSTEM_PROMPT to a known string; ensure module import does not raise.
#
# Test cases:
# - Builds context from full_conversation list: 'User:' for user role, 'Yarn:' for bot role; lines joined with newlines.
# - Returns call_llm string result on success; logs info.
# - When call_llm raises, function logs error and raises RuntimeError with message.
#
# Notes:
# - No external network; isolate by patching call_llm only.

