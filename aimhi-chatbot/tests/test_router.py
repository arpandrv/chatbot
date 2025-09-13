# Tests for core/router.py
#
# Use unittest.TestCase with setUp/tearDown to patch dependencies:
# - Patch database.repository functions: get_session, update_session_state, record_risk_detection,
#   record_intent_classification to avoid DB calls and to assert they’re called with expected args.
# - Patch NLP functions used by router: contains_risk, get_crisis_resources, classify_intent,
#   analyze_sentiment, and VariedResponseSelector.get_response/get_prompt to return deterministic strings.
# - Control environment var LLM_ENABLED via os.environ for LLM branch tests.
#
# Test cases:
# - route_message risk short-circuit: when contains_risk returns True, returns get_crisis_resources value
#   and records risk via record_risk_detection, without calling other handlers.
# - FSM initial state restore: when get_session provides an fsm_state, router uses it; otherwise defaults to 'welcome'.
# - Welcome -> next state: any non-trivial message advances to 'support_people' and update_session_state is called.
# - Clarify/attempts: for 'support_people' with classify_intent returning 'unclear', first attempt yields 'clarify' response;
#   after max attempts, should force advance and return a transition response + next prompt.
# - Strengths/Worries/Goals happy paths: intent != 'unclear' advances state and returns acknowledgment + prompt/transition text.
# - LLM conversation branch: when state is 'llm_conversation' and LLM_ENABLED=False, returns static unavailable message.
# - set/get attempts behavior: ensure increment/reset are used across clarify and advance paths (observable via mocked responses).
# - State update only when changed: verify update_session_state is called IFF the state transitions.
#
# Notes:
# - Avoid importing real NLP classes; patch symbols in core.router module namespace (e.g., core.router.contains_risk).
# - Use patch.dict(os.environ, {"LLM_ENABLED": "true/false"}, clear=False) to toggle behavior.
# - Ensure no network calls; all requests from NLP modules must be mocked if they accidentally import.

